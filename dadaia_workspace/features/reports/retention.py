"""Workspace report retention service.

The service treats reports and handoffs as workspace runtime state. It never
writes into repo working trees and every filesystem mutation is constrained to
``.dadaia/reports/``, ``.dadaia/handoff/``, or ``.dadaia/states/``.

One index (:meth:`ReportRetentionService._nodes`): every ``*.html`` under
``.dadaia/reports/`` and every ``*.handoff.json`` under either root is a retention
node. A handoff pairs with the report its ``artifact.path`` names under
``.dadaia/reports/`` (or, for a legacy sidecar inside ``.dadaia/reports/``, the
same-stem report); every other handoff — the handoff-first emission (DADAIA §5.4),
a ``repos/…``/``specs/…`` artifact, an unreadable document — is a node of its own,
keyed by its own workspace ref. There is no second class of handoff.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath

from dadaia_workspace.core.handoff_index import Handoff, path_timestamp, scan_handoffs

_DEFAULT_TTL = dt.timedelta(hours=48)


@dataclass(frozen=True)
class ReportRecord:
    """One retention node: a report with its paired handoffs, or an unpaired handoff group."""

    artifact_path: str
    report_path: Path | None
    handoff_paths: tuple[Path, ...]
    effective_timestamp: dt.datetime
    important: bool = False


@dataclass(frozen=True)
class CleanupCandidate:
    """A logical retention deletion candidate."""

    artifact_path: str
    reason: str
    paths: tuple[Path, ...]
    effective_timestamp: dt.datetime
    important: bool = False


@dataclass(frozen=True)
class CleanupResult:
    """Cleanup outcome for CLI, panel, and tests."""

    dry_run: bool
    candidates: tuple[CleanupCandidate, ...]
    deleted_paths: tuple[Path, ...] = field(default_factory=tuple)
    skipped_paths: tuple[Path, ...] = field(default_factory=tuple)


class ReportRetentionService:
    """Discover, protect, and clean workspace report artifacts."""

    def __init__(self, workspace_root: Path, *, now: dt.datetime | None = None) -> None:
        self._workspace_root = workspace_root.resolve()
        self._reports_root = (self._workspace_root / ".dadaia" / "reports").resolve()
        self._handoff_root = (self._workspace_root / ".dadaia" / "handoff").resolve()
        self._states_root = (self._workspace_root / ".dadaia" / "states").resolve()
        self._state_path = self._states_root / "report_retention.json"
        self._now = now

    @property
    def state_path(self) -> Path:
        return self._state_path

    def list_reports(self) -> list[ReportRecord]:
        """Return report-backed records sorted newest first."""
        return [node for node in self._nodes() if node.report_path is not None]

    def cleanup_candidates(
        self,
        *,
        older_than: dt.timedelta = _DEFAULT_TTL,
    ) -> list[CleanupCandidate]:
        """Return every non-important node older than ``older_than``."""
        reason = f"older than {int(older_than.total_seconds() // 3600)}h"
        return [
            CleanupCandidate(
                artifact_path=node.artifact_path,
                reason=reason,
                paths=tuple(p for p in (node.report_path, *node.handoff_paths) if p is not None),
                effective_timestamp=node.effective_timestamp,
            )
            for node in self._expired(self._nodes(), older_than)
        ]

    def cleanup(
        self,
        *,
        older_than: dt.timedelta = _DEFAULT_TTL,
        dry_run: bool = False,
    ) -> CleanupResult:
        """Delete eligible candidates unless ``dry_run`` is true."""
        candidates = tuple(self.cleanup_candidates(older_than=older_than))
        if dry_run:
            return CleanupResult(dry_run=True, candidates=candidates)

        deleted: list[Path] = []
        skipped: list[Path] = []
        for candidate in candidates:
            for path in candidate.paths:
                if not self._is_mutable_runtime_path(path):
                    skipped.append(path)
                    continue
                if path.exists() and path.is_file():
                    path.unlink()
                    deleted.append(path)
        return CleanupResult(
            dry_run=False,
            candidates=candidates,
            deleted_paths=tuple(deleted),
            skipped_paths=tuple(skipped),
        )

    def mark_important(self, path: str | Path, *, reason: str | None = None) -> str:
        """Protect a report from retention cleanup and return its artifact ref."""
        artifact = self._normalize_to_artifact_ref(path)
        state = self._load_state()
        important = state.setdefault("important", {})
        if not isinstance(important, dict):
            important = {}
            state["important"] = important
        important[artifact] = {
            "marked_at": self._clock().isoformat().replace("+00:00", "Z"),
            "reason": reason or "",
        }
        self._save_state(state)
        return artifact

    def unmark_important(self, path: str | Path) -> str:
        """Remove explicit important protection and return its artifact ref."""
        artifact = self._normalize_to_artifact_ref(path)
        state = self._load_state()
        important = state.get("important", {})
        if isinstance(important, dict):
            important.pop(artifact, None)
        self._save_state(state)
        return artifact

    def important_reports(self) -> dict[str, dict[str, str]]:
        """Return important state keyed by workspace-relative artifact path."""
        state = self._load_state()
        important = state.get("important", {})
        if not isinstance(important, dict):
            return {}
        result: dict[str, dict[str, str]] = {}
        for path, value in important.items():
            if isinstance(path, str) and isinstance(value, dict):
                result[path] = {str(k): str(v) for k, v in value.items()}
        return result

    def status(self, *, older_than: dt.timedelta = _DEFAULT_TTL) -> dict[str, int | bool]:
        """Return retention counters for doctor/status surfaces.

        ``orphan_handoff_count`` counts every handoff not paired with a report.
        """
        nodes = self._nodes()
        expired = self._expired(nodes, older_than)
        return {
            "report_count": sum(1 for node in nodes if node.report_path is not None),
            "stale_report_count": sum(1 for node in expired if node.report_path is not None),
            "stale_handoff_count": sum(len(node.handoff_paths) for node in expired),
            "orphan_handoff_count": sum(
                len(node.handoff_paths) for node in nodes if node.report_path is None
            ),
            "important_report_count": len(self.important_reports()),
            "malformed_state": self._state_malformed(),
        }

    def _nodes(self) -> list[ReportRecord]:
        """The one index: every report under ``reports/``, every handoff under either root."""
        important = self._important_paths()
        groups = self._handoffs_by_ref()
        nodes: list[ReportRecord] = []
        if self._reports_root.exists():
            for report in sorted(self._reports_root.rglob("*.html")):
                if report.is_file() and self._is_under(report, self._reports_root):
                    ref = self._workspace_ref(report)
                    nodes.append(self._node(ref, report, groups.pop(ref, []), important))
        nodes.extend(self._node(ref, None, group, important) for ref, group in groups.items())
        return sorted(nodes, key=lambda node: node.effective_timestamp, reverse=True)

    def _node(
        self, ref: str, report: Path | None, handoffs: list[Handoff], important: set[str]
    ) -> ReportRecord:
        paths = tuple(handoff.path for handoff in handoffs)
        members = [p for p in (report, *paths) if p is not None]
        return ReportRecord(
            artifact_path=ref,
            report_path=report,
            handoff_paths=paths,
            effective_timestamp=self._effective_timestamp(report, handoffs),
            important=ref in important or any(self._workspace_ref(p) in important for p in members),
        )

    def _expired(self, nodes: list[ReportRecord], older_than: dt.timedelta) -> list[ReportRecord]:
        cutoff = self._clock() - older_than
        return [n for n in nodes if not n.important and n.effective_timestamp <= cutoff]

    def _handoffs_by_ref(self) -> dict[str, list[Handoff]]:
        """Every handoff under either root, grouped by the ref it pairs with (or its own)."""
        groups: dict[str, list[Handoff]] = {}
        for root in (self._handoff_root, self._reports_root):
            for handoff in scan_handoffs(root):
                if self._is_under(handoff.path, root):
                    groups.setdefault(self._pairing_ref(handoff), []).append(handoff)
        return groups

    def _pairing_ref(self, handoff: Handoff) -> str:
        declared = handoff.artifact_path_raw
        report = self._artifact_to_report_path(declared) if declared is not None else None
        if report is None:
            report = self._legacy_same_stem_report(handoff.path)
        return self._workspace_ref(handoff.path if report is None else report)

    def _effective_timestamp(self, report: Path | None, handoffs: list[Handoff]) -> dt.datetime:
        """A node ages by its newest canonical handoff; a report with none ages by itself."""
        if report is None:
            return max(handoff.effective_timestamp() for handoff in handoffs)
        canonical = [h for h in handoffs if self._is_under(h.path, self._handoff_root)]
        if canonical:
            return max(handoff.effective_timestamp() for handoff in canonical)
        return path_timestamp(report)

    def _normalize_to_artifact_ref(self, path: str | Path) -> str:
        raw = Path(path)
        # Reject absolute inputs regardless of host OS. Path.is_absolute() is
        # host-dependent ("/tmp/x" is NOT absolute on Windows; "C:\x" is NOT
        # absolute on POSIX), so a foreign-style absolute path could slip past a
        # single-flavour check and trip a weaker downstream guard. Test both
        # flavours. See FR-RC2-3.
        text = str(path)
        if PurePosixPath(text).is_absolute() or PureWindowsPath(text).is_absolute():
            raise ValueError("absolute paths are not accepted")
        if any(part == ".." for part in raw.parts):
            raise ValueError("parent traversal is not accepted")
        ref = raw.as_posix()
        if ref.startswith(".dadaia/handoff/") or ref.endswith(".handoff.json"):
            handoff = (self._workspace_root / raw).resolve()
            if not self._is_under(handoff, self._handoff_root) and not self._is_under(
                handoff, self._reports_root
            ):
                raise ValueError("handoff path must be under .dadaia/handoff or .dadaia/reports")
            return self._pairing_ref(Handoff.load(handoff))
        if not ref.startswith(".dadaia/reports/"):
            ref = f".dadaia/reports/{ref}"
        report = self._artifact_to_report_path(ref)
        if report is None:
            raise ValueError("report path must stay under .dadaia/reports")
        return self._workspace_ref(report)

    def _artifact_to_report_path(self, artifact: str) -> Path | None:
        if not artifact.startswith(".dadaia/reports/"):
            return None
        rel = artifact.removeprefix(".dadaia/reports/")
        if any(part == ".." for part in Path(rel).parts):
            return None
        candidate = (self._reports_root / rel).resolve()
        if not self._is_under(candidate, self._reports_root):
            return None
        return candidate

    def _workspace_ref(self, path: Path) -> str:
        return path.resolve().relative_to(self._workspace_root).as_posix()

    def _legacy_same_stem_report(self, handoff: Path) -> Path | None:
        if not self._is_under(handoff, self._reports_root) or not handoff.name.endswith(
            ".handoff.json"
        ):
            return None
        report = handoff.with_name(handoff.name.removesuffix(".handoff.json") + ".html")
        if report.is_file() and self._is_under(report, self._reports_root):
            return report
        return None

    def _is_mutable_runtime_path(self, path: Path) -> bool:
        resolved = path.resolve()
        return self._is_under(resolved, self._reports_root) or self._is_under(
            resolved, self._handoff_root
        )

    def _is_under(self, path: Path, root: Path) -> bool:
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            return False
        return True

    def _important_paths(self) -> set[str]:
        return set(self.important_reports())

    def _load_state(self) -> dict[str, object]:
        if not self._state_path.exists():
            return {"version": 1, "important": {}}
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"version": 1, "important": {}}
        if not isinstance(data, dict):
            return {"version": 1, "important": {}}
        data.setdefault("version", 1)
        data.setdefault("important", {})
        return data

    def _save_state(self, state: dict[str, object]) -> None:
        state.setdefault("version", 1)
        if not isinstance(state.get("important"), dict):
            state["important"] = {}
        self._states_root.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _state_malformed(self) -> bool:
        if not self._state_path.exists():
            return False
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return True
        return not isinstance(data, dict) or not isinstance(data.get("important", {}), dict)

    def _clock(self) -> dt.datetime:
        return (self._now or dt.datetime.now(tz=dt.UTC)).astimezone(dt.UTC)
