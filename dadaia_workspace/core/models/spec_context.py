"""Spec Context Project domain models."""

from dataclasses import dataclass
from enum import StrEnum

from dadaia_workspace.core.skill_owner import load_owner

#: The kernel's context-name grammar, loaded from ``_grammar.py``.
CONTEXT_NAME_RE = load_owner("dd-bug-resolution", "_grammar").CONTEXT_NAME_RE

#: The `schema_version` `dadaia export` writes and `dadaia import` accepts.
EXPORT_SCHEMA_VERSION = "spec-contexts-export-v1"


class ContextState(StrEnum):
    ALIVE = "alive"
    DEAD = "dead"


@dataclass(frozen=True)
class AssociatedRepo:
    """One repo associated with a context, ordered alongside the unique main repo.

    The main repo (``SpecContextProject.repo_slug``/``repo_url``) stays the sole
    specs/bind/memory/release/backlog target — an ``AssociatedRepo``
    is never a second such target, only an extra checkout under ``repos/``.
    """

    slug: str
    url: str


@dataclass(frozen=True)
class SpecContextProject:
    name: str
    state: ContextState
    repo_slug: str
    repo_url: str
    created_at: str
    alive_since: str | None = None
    dead_since: str | None = None
    current_branch: str | None = None
    associated_repos: tuple[AssociatedRepo, ...] = ()

    def all_repos(self) -> tuple[AssociatedRepo, ...]:
        """Every repo of this context: the main repo first, then the associated repos.

        The main repo is folded into the slug/url shape of an associated repo. The
        specs, bind, memory, release and backlog paths resolve the main repo through
        ``repo_slug``/``repo_url`` directly, not through this method.
        """
        return (AssociatedRepo(slug=self.repo_slug, url=self.repo_url), *self.associated_repos)


@dataclass(frozen=True)
class RepoLiveStatus:
    """One repo's on-disk presence and live checked-out branch.

    Produced by ``SpecContextService.repo_live_status`` and ``repos_live_status``; the
    ``context show``, ``context list --json`` and export-branch refresh paths render it.
    """

    slug: str
    url: str
    on_disk: bool
    current_branch: str | None
