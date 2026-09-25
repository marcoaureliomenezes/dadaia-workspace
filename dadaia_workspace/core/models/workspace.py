"""Workspace domain model."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    root: Path
    dadaia_dir: Path  # root/.dadaia/
    claude_dir: Path  # root/.claude/
    repos_dir: Path  # root/repos/

    @property
    def states_dir(self) -> Path:
        return self.dadaia_dir / "states"

    @classmethod
    def from_root(cls, root: Path) -> "Workspace":
        return cls(
            root=root,
            dadaia_dir=root / ".dadaia",
            claude_dir=root / ".claude",
            repos_dir=root / "repos",
        )
