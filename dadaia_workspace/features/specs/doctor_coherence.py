"""Constitution and pattern-version coherence checks for SpecsDoctor."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.features.specs.doctor_types import Severity, specs_finding
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient, gitflow_fix


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
        """WARN, in a git repo, when the committed constitution's ``gitflow:`` block is absent or malformed:
        the gates read the same text and fall back to the default."""
        constitution = self.specs_dir / "constitution.md"
        repo = self.specs_dir.parent
        if not constitution.is_file() or not (repo / ".git").exists():
            return []
        _, warning = GitSubprocessClient().gitflow(repo)
        if warning is None:
            return []
        return [
            specs_finding(
                code="GITFLOW-1",
                severity=Severity.WARNING,
                description=warning,
                path=str(constitution),
                fix=gitflow_fix(self.specs_dir),
            )
        ]
