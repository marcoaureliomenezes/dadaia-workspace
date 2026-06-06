"""Reports doctor — structural invariant checks for .dadaia/reports/ and .dadaia/handoff/.

RPT-1: Dangling artifact.path invariant.

A handoff sidecar (``.handoff.json``) is "dangling" when its ``artifact.path`` field
either:

  - does not start with ``.dadaia/reports/`` (non-canonical location), or
  - resolves to a file that does not exist on disk, or
  - resolves to a file that is not an ``.html`` file.

The invariant does NOT flag HTML reports that have no corresponding sidecar
(sidecar-less reports are valid — the sidecar is optional).

Infra-free per the constitution (L67): standard library only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ReportsDoctorIssue:
    """One RPT-1 finding."""

    code: str
    message: str
    sidecar_path: Path
    artifact_path: str | None = None


@dataclass
class ReportsDoctorResult:
    """Result of a full reports doctor run."""

    issues: list[ReportsDoctorIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0


class ReportsDoctor:
    """Run structural invariant checks on ``.dadaia/reports/`` and ``.dadaia/handoff/``.

    Args:
        workspace_root: Absolute path to the workspace root.  Must contain
            ``.dadaia/handoff/`` and (optionally) ``.dadaia/reports/``.
    """

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve()
        self._handoff_root = self._workspace_root / ".dadaia" / "handoff"
        self._reports_root = self._workspace_root / ".dadaia" / "reports"

    def check(self) -> ReportsDoctorResult:
        """Run all invariant checks and return a consolidated result."""
        result = ReportsDoctorResult()
        result.issues.extend(self._check_rpt1())
        return result

    # ------------------------------------------------------------------
    # RPT-1 — Dangling artifact.path
    # ------------------------------------------------------------------

    def _check_rpt1(self) -> list[ReportsDoctorIssue]:
        """RPT-1: flag handoffs whose artifact.path does not resolve to an existing .html.

        Scan all ``.handoff.json`` files under ``.dadaia/handoff/`` (canonical location).
        For each file that declares an ``artifact.path``:

        - If the path does not start with ``.dadaia/reports/`` → dangling (non-canonical).
        - If the resolved file does not exist → dangling (missing HTML).
        - If the resolved file exists but is not ``.html`` → dangling (wrong type).

        Handoffs without an ``artifact.path`` are silently skipped (the field is
        optional in handoff-v1.1 for handoff-first emission).
        """
        issues: list[ReportsDoctorIssue] = []
        if not self._handoff_root.exists():
            return issues

        for sidecar in sorted(self._handoff_root.rglob("*.handoff.json")):
            if not sidecar.is_file():
                continue
            try:
                doc = json.loads(sidecar.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                # Malformed JSON — not an RPT-1 concern (covered by validate/lint).
                continue

            artifact = doc.get("artifact", {})
            if not isinstance(artifact, dict):
                continue
            artifact_path_str = artifact.get("path")
            if not isinstance(artifact_path_str, str) or not artifact_path_str:
                # No artifact.path declared — sidecar is valid (handoff-first emission).
                continue

            issue = self._check_rpt1_path(sidecar, artifact_path_str)
            if issue is not None:
                issues.append(issue)

        return issues

    def _check_rpt1_path(self, sidecar: Path, artifact_path_str: str) -> ReportsDoctorIssue | None:
        """Return an RPT-1 issue if ``artifact_path_str`` is dangling, else None."""
        # Must start with the canonical reports prefix.
        _REPORTS_PREFIX = ".dadaia/reports/"
        if not artifact_path_str.startswith(_REPORTS_PREFIX):
            return ReportsDoctorIssue(
                code="RPT-1",
                message=(
                    f"[dangling-artifact-path] {sidecar} → {artifact_path_str!r} "
                    f"(artifact.path must start with '{_REPORTS_PREFIX}')"
                ),
                sidecar_path=sidecar,
                artifact_path=artifact_path_str,
            )

        # Resolve against workspace root; guard against path traversal.
        rel = artifact_path_str.removeprefix(_REPORTS_PREFIX)
        if any(part == ".." for part in Path(rel).parts):
            return ReportsDoctorIssue(
                code="RPT-1",
                message=(
                    f"[dangling-artifact-path] {sidecar} → {artifact_path_str!r} "
                    "(path traversal detected)"
                ),
                sidecar_path=sidecar,
                artifact_path=artifact_path_str,
            )

        resolved = (self._reports_root / rel).resolve()
        try:
            resolved.relative_to(self._reports_root)
        except ValueError:
            return ReportsDoctorIssue(
                code="RPT-1",
                message=(
                    f"[dangling-artifact-path] {sidecar} → {artifact_path_str!r} "
                    "(escapes .dadaia/reports/ boundary)"
                ),
                sidecar_path=sidecar,
                artifact_path=artifact_path_str,
            )

        if not resolved.exists():
            return ReportsDoctorIssue(
                code="RPT-1",
                message=(
                    f"[dangling-artifact-path] {sidecar} → {artifact_path_str!r} "
                    "(file does not exist)"
                ),
                sidecar_path=sidecar,
                artifact_path=artifact_path_str,
            )

        if resolved.suffix.lower() != ".html":
            return ReportsDoctorIssue(
                code="RPT-1",
                message=(
                    f"[dangling-artifact-path] {sidecar} → {artifact_path_str!r} "
                    f"(not an .html file — got {resolved.suffix!r})"
                ),
                sidecar_path=sidecar,
                artifact_path=artifact_path_str,
            )

        return None
