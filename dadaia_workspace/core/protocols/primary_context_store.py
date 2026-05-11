"""PrimaryContextStore protocol — read/write/clear primary_context.json."""

from pathlib import Path
from typing import Protocol


class PrimaryContext(Protocol):
    name: str
    repo_slug: str
    specs_dir: str


class PrimaryContextStore(Protocol):
    def write(self, name: str, repo_slug: str, specs_dir: Path) -> None: ...
    def read(self) -> dict[str, str] | None: ...
    def clear(self) -> None: ...
