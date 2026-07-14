"""Workspace domain model."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    root: Path
    dadaia_dir: Path  # root/.dadaia/
    claude_dir: Path  # root/.claude/
    repos_dir: Path  # root/repos/

    # Durable subdirs
    @property
    def reports_dir(self) -> Path:
        return self.dadaia_dir / "reports"

    @property
    def scripts_dir(self) -> Path:
        return self.dadaia_dir / "scripts"

    @property
    def states_dir(self) -> Path:
        return self.dadaia_dir / "states"

    @property
    def academy_dir(self) -> Path:
        return self.dadaia_dir / "academy"

    # Ephemeral subdirs
    @property
    def tmp_python_dir(self) -> Path:
        return self.dadaia_dir / "tmp" / "python"

    @property
    def tmp_json_dir(self) -> Path:
        return self.dadaia_dir / "tmp" / "json"

    @classmethod
    def from_root(cls, root: Path) -> "Workspace":
        return cls(
            root=root,
            dadaia_dir=root / ".dadaia",
            claude_dir=root / ".claude",
            repos_dir=root / "repos",
        )
