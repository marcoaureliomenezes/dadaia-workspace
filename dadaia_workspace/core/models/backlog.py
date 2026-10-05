"""The typed ``intents[]`` of a backlog item: ``(subject{kind,ref,surface} -> change)``.

Plain constructors. The grammar (kinds, the repo-relative ``path[#word]`` code-ref rule,
no extra keys) is ``public/schemas/backlog/backlog-v1.schema.json`` alone; resolution is
``features/backlog/subject_registry.py``'s.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

__all__ = [
    "INTENTS_EXEMPT_STATUS",
    "Intent",
    "Subject",
    "SubjectKind",
]

#: The one backlog stage exempt from the resolvable-typed-intents requirement.
INTENTS_EXEMPT_STATUS = "idea"


class SubjectKind(StrEnum):
    """The registry source classes a subject ref may belong to, each derived from live
    truth (SPEC §3.1/§3.2)."""

    CODE = "code"
    DOC = "doc"
    INVARIANT = "invariant"
    CATALOG = "catalog"


@dataclass(frozen=True)
class Subject:
    """A typed reference to one canonical subject of a change; ``surface: new`` marks a
    subject the item itself introduces, bound by declared identity."""

    kind: SubjectKind
    ref: str
    surface: str = "existing"


@dataclass(frozen=True)
class Intent:
    """One ``(subject -> change)`` delta declared by a backlog item (SPEC §3.1)."""

    subject: Subject
    change: str

    @classmethod
    def of(cls, raw: dict[str, Any]) -> Intent:
        """One ``intents[]`` element the backlog-v1 schema already accepted."""
        s = raw["subject"]
        return cls(
            Subject(SubjectKind(s["kind"]), s["ref"], s.get("surface", "existing")), raw["change"]
        )
