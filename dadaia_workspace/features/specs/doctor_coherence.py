"""Constitution and pattern-version coherence checks for SpecsDoctor."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.features.specs.doctor_types import Severity, specs_finding


class CoherenceValidator:
    """Constitution and pattern-version coherence."""

    def __init__(
        self,
        specs_dir: Path,
        public_dir: Path | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        self.public_dir = public_dir

    def check_constitution(self) -> list[SectionFinding]:
        path = self.specs_dir / "constitution.md"
        if not path.exists():
            return [
                specs_finding(
                    code="SPEC-DOC-001",
                    severity=Severity.ERROR,
                    description="specs/constitution.md is missing",
                    path=str(path),
                )
            ]
        return []

    def check_gitflow(self) -> list[SectionFinding]:
        """GITFLOW-1, WARN-only (ADR 0037): the constitution's ``gitflow:`` block is absent
        or malformed, so the pre-push gate falls back to the default."""
        from dadaia_workspace.core.gitflow import read_gitflow

        constitution = self.specs_dir / "constitution.md"
        _, warning = read_gitflow(self.specs_dir)
        if warning is None or not constitution.is_file():
            return []
        return [
            specs_finding(
                code="GITFLOW-1",
                severity=Severity.WARNING,
                description=warning,
                path=str(constitution),
            )
        ]
