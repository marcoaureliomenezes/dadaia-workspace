"""Spec Context Project domain models."""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ContextState(StrEnum):
    INATIVO = "inativo"
    STANDBY = "standby"
    ATIVO = "ativo"


class RepoRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


class RepoSourceKind(StrEnum):
    REMOTE_URL = "remote_url"
    LOCAL_PATH = "local_path"


@dataclass(frozen=True)
class ContextRepositoryRef:
    repo_ref: str            # original ref (URL or local path)
    role: RepoRole
    source_kind: RepoSourceKind
    repo_slug: str           # derived from repo_ref basename (without .git)
    materialized_path: Path | None = None
    has_specs_dir: bool = False


@dataclass(frozen=True)
class SpecContextProject:
    name: str
    state: ContextState
    primary_repo: ContextRepositoryRef
    secondary_repos: tuple[ContextRepositoryRef, ...] = field(default_factory=tuple)
    context_dir: Path | None = None
    specs_dir: Path | None = None


def derive_repo_slug(repo_ref: str) -> str:
    """Derive a filesystem-safe slug from a repo ref (URL or local path)."""
    from pathlib import PurePosixPath
    name = PurePosixPath(repo_ref).name
    if name.endswith(".git"):
        name = name[:-4]
    return name or "repo"


def detect_source_kind(repo_ref: str) -> RepoSourceKind:
    """Detect whether a repo_ref is a remote URL or a local path."""
    if repo_ref.startswith(("http://", "https://", "git@", "ssh://", "git://")):
        return RepoSourceKind.REMOTE_URL
    return RepoSourceKind.LOCAL_PATH
