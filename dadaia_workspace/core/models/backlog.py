"""Typed ``intents[]`` backlog item schema (SPEC §3.1, ADR-A).

The ``(subject{kind,ref} -> change)`` frontmatter shape every backlog item carries. This is
a **pure** domain model: it validates that a ref is *well-formed for its kind*, but it does
NOT resolve a subject to a registry anchor — binding is the registry's job (T-25-02,
``features/backlog/subject_registry.py``).

Privacy invariant (SPEC §3.8 finding #7): a ``code`` ref stored in a committed intent is
**always** module-relative ``path#symbol`` (e.g.
``dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind``). Absolute / operator-local
paths (``/home/...``, ``~/...``), parent-directory traversal (``../``), and Windows drive
prefixes are rejected at construction so no operator-local path can ever land in a committed
backlog file.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "Intent",
    "Subject",
    "SubjectKind",
    "parse_intents",
    "serialize_intents",
]


class SubjectKind(StrEnum):
    """The registry source classes a subject ref may belong to (SPEC §3.1/§3.2).

    ``code``/``cli``/``catalog``/``doc``/``invariant`` are auto-derived by the registry in
    R1; ``panel``/``api`` bind via the operator alias map only (no auto-derivation in R1 —
    ADR-A). The schema accepts all seven so the shape is forward-compatible with R2.
    """

    CODE = "code"
    API = "api"
    CLI = "cli"
    PANEL = "panel"
    DOC = "doc"
    INVARIANT = "invariant"
    CATALOG = "catalog"


#: A module-relative ``path#symbol`` code ref: a relative POSIX path, ``#``, then a symbol.
#: The path segment must not be absolute, a home-expansion, a parent traversal, or carry a
#: Windows drive prefix — those are operator-local and forbidden in a committed intent.
_CODE_REF_RE = re.compile(r"^(?P<path>[^#]+)#(?P<symbol>[^#]+)$")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


def _validate_code_ref(ref: str) -> None:
    """Validate a ``code`` subject ref is module-relative ``path#symbol`` (SPEC §3.8 #7)."""
    match = _CODE_REF_RE.match(ref)
    if match is None:
        raise ValueError(f"code subject ref must be module-relative 'path#symbol', got {ref!r}")
    path = match.group("path").strip()
    symbol = match.group("symbol").strip()
    if not path or not symbol:
        raise ValueError(f"code subject ref must carry a non-empty path and symbol, got {ref!r}")
    if path.startswith("/"):
        raise ValueError(f"code subject ref must be module-relative, not an absolute path: {ref!r}")
    if path.startswith("~"):
        raise ValueError(
            f"code subject ref must be module-relative, not an operator-local home path: {ref!r}"
        )
    if ".." in path.split("/"):
        raise ValueError(
            f"code subject ref must be module-relative, parent-directory traversal forbidden: {ref!r}"
        )
    if _WINDOWS_DRIVE_RE.match(path):
        raise ValueError(
            f"code subject ref must be module-relative, not an absolute drive path: {ref!r}"
        )


#: Valid ``Subject.surface`` values: ``existing`` (the ref must resolve to a registry
#: anchor — the default and the only pre-0.4.3 behavior) and ``new`` (the item
#: INTRODUCES this surface; there is deliberately no anchor to resolve). Bugs
#: backlog-independent-cli-items-false-conflict-044 /
#: backlog-cli-intent-hallucinated-anchor-045: without a first-class new-surface
#: declaration, an item about a new CLI command must either mis-bind an existing
#: anchor (false DIVERGENT_CONFLICT) or invent a ref (unrecoverable unresolved block).
_SUBJECT_SURFACES = ("existing", "new")


@dataclass(frozen=True)
class Subject:
    """A typed reference to one canonical subject of a change. Never free text.

    Validation here is *shape only* (well-formed for the kind). Resolution of the ref to a
    live registry anchor is the registry's job (T-25-02). ``surface: new`` marks a subject
    the item itself introduces — bound by declared identity, not registry resolution.
    """

    kind: SubjectKind
    ref: str
    surface: str = "existing"

    def __post_init__(self) -> None:
        if not isinstance(self.kind, SubjectKind):
            raise ValueError(f"subject kind must be a SubjectKind, got {self.kind!r}")
        ref = self.ref.strip() if isinstance(self.ref, str) else self.ref
        if not ref:
            raise ValueError(f"subject ref must be a non-empty string for kind {self.kind}")
        if self.surface not in _SUBJECT_SURFACES:
            raise ValueError(
                f"subject surface must be one of {_SUBJECT_SURFACES}, got {self.surface!r}"
            )
        if self.kind is SubjectKind.CODE:
            # Shape (and the §3.8 privacy invariant) applies to NEW code surfaces too —
            # a not-yet-existing module still must be declared module-relative.
            _validate_code_ref(ref)


@dataclass(frozen=True)
class Intent:
    """One ``(subject -> change)`` delta declared by a backlog item (SPEC §3.1)."""

    subject: Subject
    change: str

    def __post_init__(self) -> None:
        if not isinstance(self.subject, Subject):
            raise ValueError(f"intent subject must be a Subject, got {self.subject!r}")
        if not isinstance(self.change, str) or not self.change.strip():
            raise ValueError("intent change must be a non-empty human string")


def parse_intents(raw: object) -> list[Intent]:
    """Parse a frontmatter ``intents:`` value into validated :class:`Intent` objects.

    ``None`` (no ``intents`` key) → ``[]``. Raises ``ValueError`` on any structural problem
    (not a list, missing ``subject``/``change``, unknown ``kind``, malformed ``ref``) — the
    schema is fail-loud, never silently dropping a malformed intent.
    """
    if raw is None:
        return []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError(f"intents must be a list, got {type(raw).__name__}")
    intents: list[Intent] = []
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"intents[{idx}] must be a mapping, got {type(entry).__name__}")
        subject_raw = entry.get("subject")
        if not isinstance(subject_raw, dict):
            raise ValueError(f"intents[{idx}] missing a 'subject' mapping")
        kind_raw = subject_raw.get("kind")
        if not isinstance(kind_raw, str):
            raise ValueError(f"intents[{idx}] subject kind must be a string, got {kind_raw!r}")
        try:
            kind = SubjectKind(kind_raw)
        except ValueError as exc:
            raise ValueError(f"intents[{idx}] has unknown subject kind {kind_raw!r}") from exc
        ref_raw = subject_raw.get("ref")
        if not isinstance(ref_raw, str):
            raise ValueError(f"intents[{idx}] subject ref must be a string")
        surface_raw = subject_raw.get("surface", "existing")
        if not isinstance(surface_raw, str) or surface_raw not in _SUBJECT_SURFACES:
            raise ValueError(
                f"intents[{idx}] subject surface must be one of {_SUBJECT_SURFACES}, "
                f"got {surface_raw!r}"
            )
        change_raw = entry.get("change")
        if not isinstance(change_raw, str):
            raise ValueError(f"intents[{idx}] missing a 'change' string")
        intents.append(
            Intent(subject=Subject(kind=kind, ref=ref_raw, surface=surface_raw), change=change_raw)
        )
    return intents


def serialize_intents(intents: Sequence[Intent]) -> list[dict[str, object]]:
    """Serialize :class:`Intent` objects back to the frontmatter-mapping shape.

    ``surface`` is emitted only when ``new`` so every existing item round-trips
    byte-stable.
    """
    out: list[dict[str, object]] = []
    for intent in intents:
        subject: dict[str, object] = {
            "kind": intent.subject.kind.value,
            "ref": intent.subject.ref,
        }
        if intent.subject.surface != "existing":
            subject["surface"] = intent.subject.surface
        out.append({"subject": subject, "change": intent.change})
    return out
