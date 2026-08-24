"""Spec Context Project domain models."""

from dataclasses import dataclass
from enum import StrEnum


class ContextState(StrEnum):
    ALIVE = "alive"
    DEAD = "dead"


@dataclass(frozen=True)
class AssociatedRepo:
    """One repo associated with a context, ordered alongside the unique main repo.

    The main repo (``SpecContextProject.repo_slug``/``repo_url``) stays the sole
    specs/bind/memory/release/backlog target (FR19, G13, I4) — an ``AssociatedRepo``
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
        """The one accessor for "this context's repos" (A15.3).

        Main repo first (folded into the same slug/url shape as an associated repo),
        then every associated repo in registration order. Every consumer that needs
        "the context's repos" as a set — the ALIVE/DEAD lifecycle (FR16), show/list/
        export/panel (FR18) — resolves through this method; no second
        repo-resolution path is created for it. Specs/bind/memory/releases/backlog
        keep resolving the main repo directly via ``repo_slug``/``repo_url`` (FR19) —
        this accessor is additive to that single control point, never a replacement
        for it.
        """
        return (AssociatedRepo(slug=self.repo_slug, url=self.repo_url), *self.associated_repos)
