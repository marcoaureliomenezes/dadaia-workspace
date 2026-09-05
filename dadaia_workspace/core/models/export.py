"""Domain model for `dadaia export` — the one JSON artifact in the `dist` zone (FR13)."""

from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = "spec-contexts-export-v1"


@dataclass(frozen=True)
class ExportResult:
    path: Path
    contexts: int
