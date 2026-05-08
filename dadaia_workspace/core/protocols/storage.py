"""Storage protocols for public assets and catalog reading."""

from pathlib import Path
from typing import Protocol


class PublicAssetManager(Protocol):
    def install(self, target_claude_dir: Path, force: bool = False) -> list[str]:
        """Install public assets into target_claude_dir. Returns list of installed paths."""
        ...


class ExcelReader(Protocol):
    def read_rows(self, file_path: Path) -> list[dict[str, str]]:
        """Read rows from an xlsx file. Returns empty list if file does not exist."""
        ...
