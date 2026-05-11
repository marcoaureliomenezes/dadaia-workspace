"""Spec Context Project domain models."""

from dataclasses import dataclass
from enum import StrEnum


class ContextState(StrEnum):
    INATIVO = "inativo"
    ATIVO = "ativo"


@dataclass(frozen=True)
class SpecContextProject:
    name: str
    state: ContextState
    repo_slug: str
    repo_url: str
    is_primary: bool
    created_at: str
    activated_at: str | None = None
