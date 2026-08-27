"""Typed ``intents[]`` backlog item schema (SPEC §3.1, ADR-A), plus
:class:`BacklogHistoRecord` (v0.5.0 FR5, A5.1) — the one-record-per-exit shape appended to
``specs/backlog/_archive/backlog_histo.jsonl`` when a ``### <slug>`` ``## ACTIVE``
subsection leaves ``BACKLOG.md``.

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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "INTENTS_EXEMPT_STATUS",
    "TERMINAL_DISPOSITION_TOKENS",
    "BacklogHistoRecord",
    "ConsumedBacklogHistoRecord",
    "Intent",
    "Subject",
    "SubjectKind",
    "is_intents_exempt",
    "is_terminal_disposition",
    "parse_intents",
    "serialize_intents",
]

#: The one backlog stage exempt from the resolvable-typed-intents requirement.
INTENTS_EXEMPT_STATUS = "idea"

#: The six canonical LEDGER disposition tokens (SPEC v0.12.0 FR1/FR2,
#: ``dd-backlog-definition`` §2 — the single canonical home for this vocabulary;
#: defined once here so the document parser (LEDGER-line grammar, A1.5) and the doctor
#: (BL-STALE's "own Status is terminal" condition, ADR D8) share one source of truth.
TERMINAL_DISPOSITION_TOKENS: tuple[str, ...] = (
    "DELIVERED",
    "SUPERSEDED",
    "RESOLVED",
    "CONSUMED",
    "DEFERRED",
    "REJECTED",
)
_TERMINAL_DISPOSITION_TOKEN_SET = frozenset(TERMINAL_DISPOSITION_TOKENS)


def is_terminal_disposition(token: str | None) -> bool:
    """True iff *token* is (case-insensitively) one of the six canonical terminal
    LEDGER disposition tokens: ``DELIVERED``, ``SUPERSEDED``, ``RESOLVED``, ``CONSUMED``,
    ``DEFERRED``, ``REJECTED`` (``dd-backlog-definition`` §2).
    """
    return token is not None and token.strip().upper() in _TERMINAL_DISPOSITION_TOKEN_SET


def is_intents_exempt(status: str | None) -> bool:
    """True iff ``status`` is the intents-exempt ``idea`` stage (v0.1.55 FR5).

    An ``idea`` is an unbound brainstorm — exempt from the resolvable-typed-intents
    requirement. Every other status (candidate and beyond, or a missing status) must
    carry bound, resolvable intents.

    Lives in ``core`` so every backlog validator shares ONE predicate — validators
    previously diverged on whether a pre-existing ``candidate`` with no intents was
    acceptable (bug ``r5c-backlog-gate-accepts-preexisting-candidate-without-intents``).
    """
    return status is not None and status.strip().lower() == INTENTS_EXEMPT_STATUS


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


def _require_histo_str(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"backlog-histo record missing required string field {key!r}: {raw!r}")
    return value


def _optional_histo_str(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"backlog-histo record field {key!r} must be a string or null: {raw!r}")
    return value


@dataclass(frozen=True)
class BacklogHistoRecord:
    """One record per backlog-item exit (v0.5.0 FR5, A5.1) — appended once to
    ``specs/backlog/_archive/backlog_histo.jsonl`` through the generic
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` seam
    (``infrastructure.jsonl_record_store.JsonlRecordStore``, composed at
    ``container.build_backlog_histo_store``) when a ``### <slug>`` ``## ACTIVE``
    subsection leaves ``BACKLOG.md`` (any disposition).

    ``id`` IS the backlog slug — the record's identity and the
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` key. With one
    line per slug, ever, a duplicate exit is structurally impossible (A5.2): the
    ``disposition``/``reason``/``release`` fields are rewritten IN PLACE through
    :meth:`~dadaia_workspace.core.protocols.record_store.RecordStore.update` when a
    provisional ``CONSUMED`` matures to its terminal token at closure (DADAIA.md §6) —
    never a second record for the same slug.
    """

    id: str
    ts: str
    disposition: str
    reason: str | None
    release: str | None
    by: str
    entry_md: str | None
    entry_md_source: str | None

    def to_dict(self) -> dict[str, object]:
        """Serialize to the JSONL object shape (``"id"`` present so the generic
        ``JsonlRecordStore.update`` seam can locate this record by slug)."""
        return {
            "id": self.id,
            "ts": self.ts,
            "disposition": self.disposition,
            "reason": self.reason,
            "release": self.release,
            "by": self.by,
            "entry_md": self.entry_md,
            "entry_md_source": self.entry_md_source,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> BacklogHistoRecord:
        """Parse a JSONL object into a :class:`BacklogHistoRecord`. Raises
        ``ValueError`` on a malformed record so tolerant readers can skip it (mirrors
        ``BugRecord.from_dict``)."""
        return cls(
            id=_require_histo_str(raw, "id"),
            ts=_require_histo_str(raw, "ts"),
            disposition=_require_histo_str(raw, "disposition"),
            reason=_optional_histo_str(raw, "reason"),
            release=_optional_histo_str(raw, "release"),
            by=_require_histo_str(raw, "by"),
            entry_md=_optional_histo_str(raw, "entry_md"),
            entry_md_source=_optional_histo_str(raw, "entry_md_source"),
        )


def _require_histo_consumed_list(raw: Mapping[str, object], key: str) -> list[dict[str, object]]:
    """Validate :class:`ConsumedBacklogHistoRecord`'s ``consumed`` field: a list of
    mapping entries, each carrying at least a non-empty ``slug`` string. Every other
    key (``shipped_anchors``, ``note``, ...) passes through opaque and untouched — the
    relocation this record backs is byte-lossless, not a narrower reshape."""
    value = raw.get(key)
    if not isinstance(value, list):
        raise ValueError(f"consumed-backlog histo record field {key!r} must be a list: {raw!r}")
    entries: list[dict[str, object]] = []
    for entry in value:
        if not isinstance(entry, dict):
            raise ValueError(f"consumed-backlog histo record entry must be a mapping: {entry!r}")
        slug = entry.get("slug")
        if not isinstance(slug, str) or not slug:
            raise ValueError(
                f"consumed-backlog histo record entry missing a non-empty 'slug': {entry!r}"
            )
        entries.append(dict(entry))
    return entries


@dataclass(frozen=True)
class ConsumedBacklogHistoRecord:
    """One record per archived release's ``consumed_backlog.json`` sidecar (v0.5.0
    T-050-13A, SPEC A5.5) — the relocation target for the 18 per-release
    ``specs/_archive/<release-id>/consumed_backlog.json`` files FR6 (T-050-14) would
    otherwise delete out from under BL-STALE's condition (a) with no failure signal
    (FR13's "documented convention with no data behind it" shape).

    Appended once per release to ``specs/backlog/_archive/consumed_backlog_histo.jsonl``
    through the SAME generic
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` seam
    :class:`BacklogHistoRecord` uses (``infrastructure.jsonl_record_store.
    JsonlRecordStore``, composed at ``container.build_consumed_backlog_histo_store``).
    ``id`` is the release id the original sidecar's directory named (e.g.
    ``"v0.1.47"``) — the record's identity and the
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` key. ``consumed``
    is that sidecar's original ``consumed`` entry list (``{slug, shipped_anchors[],
    ...}``), preserved verbatim — a byte-lossless relocation, not a reshape.
    """

    id: str
    consumed: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        """Serialize to the JSONL object shape (``"id"`` present so the generic
        ``JsonlRecordStore`` seam can locate this record by release id)."""
        return {"id": self.id, "consumed": self.consumed}

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> ConsumedBacklogHistoRecord:
        """Parse a JSONL object into a :class:`ConsumedBacklogHistoRecord`. Raises
        ``ValueError`` on a malformed record so the generic ``JsonlRecordStore`` skips
        it (WARN-logged) rather than crashing the whole read."""
        return cls(
            id=_require_histo_str(raw, "id"),
            consumed=_require_histo_consumed_list(raw, "consumed"),
        )
