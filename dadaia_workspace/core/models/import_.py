"""Domain models for the workspace import feature."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImportOptions:
    archive: Path
    workspace: Path
    skip_mnt: bool = False
    skip_activate: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class ImportManifest:
    version: str
    exported_at: str
    workspace_root: str
    dadaia_version: str
    contexts: tuple[dict[str, object], ...]
    includes: tuple[str, ...]
    mnt_included: bool
    reports_included: bool


@dataclass(frozen=True)
class ImportResult:
    workspace_root: Path
    contexts_restored: tuple[str, ...]
    errors: tuple[str, ...]
