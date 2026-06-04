"""Workspace report retention service.

The service treats reports and handoffs as workspace runtime state. It never
writes into repo working trees and every filesystem mutation is constrained to
``.dadaia/reports/``, ``.dadaia/handoff/``, or ``.dadaia/states/``.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_TTL = dt.timedelta(hours=48)
_TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{6}Z)")


@dataclass(frozen=True)
class ReportRecord:
    """One logical report artifact plus handoffs that reference it."""

    artifact_path: str
    report_path: Path | None
    handoff_paths: tuple[Path, ...]
    effective_timestamp: dt.datetime
    important: bool = False
    malformed_handoffs: tuple[Path, ...] = field(default_factory=tuple)


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
        """Return discovered report records sorted newest first."""
        important = self._important_paths()
        handoffs_by_artifact, malformed = self._handoffs_by_artifact()
        records: dict[str, ReportRecord] = {}

        if self._reports_root.exists():
            for report in sorted(self._reports_root.rglob("*.html")):
                if not report.is_file() or not self._is_under(report, self._reports_root):
                    continue
                artifact = self._workspace_ref(report)
                handoffs = handoffs_by_artifact.get(artifact, [])
                records[artifact] = ReportRecord(
                    artifact_path=artifact,
                    report_path=report,
                    handoff_paths=tuple(handoffs),
                    effective_timestamp=self._effective_timestamp(report, handoffs),
                    important=self._node_is_important(artifact, [report, *handoffs], important),
                    malformed_handoffs=tuple(malformed),
                )

        for artifact, handoffs in handoffs_by_artifact.items():
            if artifact in records:
                continue
            report = self._artifact_to_report_path(artifact)
            if report is None or not report.is_file() or report.suffix.lower() != ".html":
                continue
            records[artifact] = ReportRecord(
                artifact_path=artifact,
                report_path=report,
                handoff_paths=tuple(handoffs),
                effective_timestamp=self._effective_timestamp(report, handoffs),
                important=self._node_is_important(artifact, [report, *handoffs], important),
                malformed_handoffs=tuple(malformed),
            )

        return sorted(records.values(), key=lambda item: item.effective_timestamp, reverse=True)

    def cleanup_candidates(
        self,
        *,
        older_than: dt.timedelta = _DEFAULT_TTL,
    ) -> list[CleanupCandidate]:
        """Return non-important reports/handoffs older than ``older_than``."""
        cutoff = self._clock() - older_than
        candidates: list[CleanupCandidate] = []
        important = self._important_paths()
        seen_handoffs: set[Path] = set()

        for record in self.list_reports():
            seen_handoffs.update(record.handoff_paths)
            if record.important or record.effective_timestamp > cutoff:
                continue
            paths = tuple(
                p
                for p in ((record.report_path,) if record.report_path else ()) + record.handoff_paths
                if p is not None
            )
            candidates.append(
                CleanupCandidate(
                    artifact_path=record.artifact_path,
                    reason=f"older than {int(older_than.total_seconds() // 3600)}h",
                    paths=paths,
                    effective_timestamp=record.effective_timestamp,
                    important=False,
                )
            )

        handoffs_by_artifact, malformed = self._handoffs_by_artifact()
        for artifact, handoffs in handoffs_by_artifact.items():
            if artifact in important or any(self._workspace_ref(p) in important for p in handoffs):
                continue
            orphan_paths = tuple(p for p in handoffs if p not in seen_handoffs)
            if not orphan_paths:
                continue
            timestamp = self._effective_timestamp(None, list(orphan_paths))
            if timestamp <= cutoff:
                candidates.append(
                    CleanupCandidate(
                        artifact_path=artifact,
                        reason="orphan handoff older than retention window",
                        paths=orphan_paths,
                        effective_timestamp=timestamp,
                    )
                )

        for handoff in malformed:
            timestamp = self._timestamp_from_path(handoff)
            if timestamp <= cutoff:
                candidates.append(
                    CleanupCandidate(
                        artifact_path=self._workspace_ref(handoff),
                        reason="malformed handoff older than retention window",
                        paths=(handoff,),
                        effective_timestamp=timestamp,
                    )
                )

        return candidates

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
        """Return retention counters for doctor/status surfaces."""
        reports = self.list_reports()
        candidates = self.cleanup_candidates(older_than=older_than)
        stale_handoffs = sum(1 for c in candidates for p in c.paths if p.name.endswith(".handoff.json"))
        stale_reports = sum(1 for c in candidates for p in c.paths if p.suffix.lower() == ".html")
        orphan_handoffs = sum(1 for c in candidates if c.reason.startswith("orphan"))
        return {
            "report_count": len(reports),
            "stale_report_count": stale_reports,
            "stale_handoff_count": stale_handoffs,
            "orphan_handoff_count": orphan_handoffs,
            "important_report_count": len(self.important_reports()),
            "malformed_state": self._state_malformed(),
        }

    def _handoffs_by_artifact(self) -> tuple[dict[str, list[Path]], list[Path]]:
        result: dict[str, list[Path]] = {}
        malformed: list[Path] = []
        for root in (self._handoff_root, self._reports_root):
            if not root.exists():
                continue
            for handoff in sorted(root.rglob("*.handoff.json")):
                if not self._is_under(handoff, root):
                    continue
                try:
                    doc = json.loads(handoff.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    malformed.append(handoff)
                    continue
                artifact = doc.get("artifact", {}) if isinstance(doc, dict) else {}
                path = artifact.get("path") if isinstance(artifact, dict) else None
                if isinstance(path, str) and path.startswith(".dadaia/reports/"):
                    result.setdefault(path, []).append(handoff)
                    continue
                stem_artifact = self._legacy_same_stem_artifact(handoff)
                if stem_artifact is not None:
                    result.setdefault(stem_artifact, []).append(handoff)
        return result, malformed

    def _effective_timestamp(self, report: Path | None, handoffs: list[Path]) -> dt.datetime:
        timestamp_handoffs = (
            [handoff for handoff in handoffs if self._is_under(handoff, self._handoff_root)]
            if report is not None
            else handoffs
        )
        for handoff in timestamp_handoffs:
            try:
                doc = json.loads(handoff.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            produced_at = doc.get("produced_at") if isinstance(doc, dict) else None
            parsed = self._parse_datetime(produced_at) if isinstance(produced_at, str) else None
            if parsed is not None:
                return parsed
        if report is not None:
            parsed = self._parse_datetime_from_name(report.name)
            if parsed is not None:
                return parsed
            return dt.datetime.fromtimestamp(report.stat().st_mtime, tz=dt.UTC)
        if handoffs:
            return self._timestamp_from_path(handoffs[0])
        return self._clock()

    def _timestamp_from_path(self, path: Path) -> dt.datetime:
        parsed = self._parse_datetime_from_name(path.name)
        if parsed is not None:
            return parsed
        return dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.UTC)

    def _parse_datetime_from_name(self, name: str) -> dt.datetime | None:
        match = _TIMESTAMP_RE.match(name)
        if not match:
            return None
        raw = match.group(1)
        return self._parse_datetime(f"{raw[:13]}:{raw[13:15]}:{raw[15:]}")

    def _parse_datetime(self, value: str) -> dt.datetime | None:
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = dt.datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.UTC)
        return parsed.astimezone(dt.UTC)

    def _normalize_to_artifact_ref(self, path: str | Path) -> str:
        raw = Path(path)
        if raw.is_absolute():
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
            try:
                doc = json.loads(handoff.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise ValueError("handoff cannot be resolved to a report artifact") from exc
            artifact = doc.get("artifact", {}) if isinstance(doc, dict) else {}
            artifact_path = artifact.get("path") if isinstance(artifact, dict) else None
            if isinstance(artifact_path, str):
                ref = artifact_path
            else:
                return self._workspace_ref(handoff)
        elif not ref.startswith(".dadaia/reports/"):
            ref = f".dadaia/reports/{ref}"
        report = self._artifact_to_report_path(ref)
        if report is None:
            raise ValueError("report path must stay under .dadaia/reports")
        return ref

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

    def _legacy_same_stem_artifact(self, handoff: Path) -> str | None:
        if not self._is_under(handoff, self._reports_root) or not handoff.name.endswith(
            ".handoff.json"
        ):
            return None
        report = handoff.with_name(handoff.name.removesuffix(".handoff.json") + ".html")
        if report.is_file() and self._is_under(report, self._reports_root):
            return self._workspace_ref(report)
        return None

    def _node_is_important(self, artifact: str, paths: list[Path], important: set[str]) -> bool:
        if artifact in important:
            return True
        return any(self._workspace_ref(path) in important for path in paths)

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
