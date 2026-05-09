"""Domain models for the workspace export feature."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExportOptions:
    output: Path | None = None
    include_reports: bool = False
    exclude_mnt: bool = False
    list_only: bool = False


@dataclass(frozen=True)
class ExportManifest:
    version: str
    exported_at: str
    workspace_root: str
    dadaia_version: str
    contexts: tuple  # tuple[dict] — frozen-compatible
    includes: tuple  # tuple[str] of archive-relative names
    mnt_included: bool
    reports_included: bool
    total_size_bytes: int


@dataclass(frozen=True)
class ExportResult:
    path: Path | None  # None when list_only=True
    size: int
    manifest: ExportManifest
