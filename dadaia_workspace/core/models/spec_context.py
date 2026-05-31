"""Spec Context Project domain models."""

from dataclasses import dataclass
from enum import StrEnum


class ContextState(StrEnum):
    ALIVE = "alive"
    DEAD = "dead"


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
