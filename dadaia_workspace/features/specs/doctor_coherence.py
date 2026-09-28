"""Constitution and pattern-version coherence checks for SpecsDoctor."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue


class CoherenceValidator:
    """Constitution and pattern-version coherence."""

    def __init__(
        self,
        specs_dir: Path,
        public_dir: Path | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        self.public_dir = public_dir

    def check_constitution(self) -> list[SpecsDoctorIssue]:
        path = self.specs_dir / "constitution.md"
        if not path.exists():
            return [
                SpecsDoctorIssue(
                    code="SPEC-DOC-001",
                    severity=Severity.ERROR,
                    description="specs/constitution.md is missing",
                    path=str(path),
                )
            ]
        return []

    def check_specs_pattern_version(self) -> list[SpecsDoctorIssue]:
        """WARN-only: the tree's ``specs_pattern_version`` is below the canonical
        version the library ships. Names the fix: migrate, then re-stamp (``specs upgrade`` refuses pre-v6 trees since K10)."""
        from dadaia_workspace.core import specs_version as _ver

        current = _ver.read_pattern_version(self.specs_dir)
        if current >= _ver.CANONICAL_SPECS_VERSION:
            return []
        return [
            SpecsDoctorIssue(
                code="SPECS-VERSION",
                severity=Severity.WARNING,
                description=(
                    f"specs_pattern_version is {current}, below the canonical "
                    f"{_ver.CANONICAL_SPECS_VERSION}. Migrate the tree to canon v{_ver.CANONICAL_SPECS_VERSION} "
                    "(dadaia-workspace 0.4.x, or by hand) and re-stamp constitution.md"
                ),
                path=str(self.specs_dir / "constitution.md"),
            )
        ]

    def check_gitflow(self) -> list[SpecsDoctorIssue]:
        """GITFLOW-1, WARN-only (ADR 0037): the constitution's ``gitflow:`` block is absent
        or malformed, so the pre-push gate falls back to the default."""
        from dadaia_workspace.core.gitflow import read_gitflow

        constitution = self.specs_dir / "constitution.md"
        _, warning = read_gitflow(self.specs_dir)
        if warning is None or not constitution.is_file():
            return []
        return [
            SpecsDoctorIssue(
                code="GITFLOW-1",
                severity=Severity.WARNING,
                description=warning,
                path=str(constitution),
            )
        ]
