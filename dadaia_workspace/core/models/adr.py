"""ADR domain model — :class:`AdrRecord`, the one-record-per-decision model (v0.5.0
specs-canon closure, operator ruling 2026-08-28).

Pure domain module — no I/O, no internal imports beyond ``dataclasses``/``collections.abc``
(stdlib only): mirrors ``core/models/findings.py``'s shape (the lighter of the two
existing JSONL record models) — an ADR carries no immutable-core/mutable-governance
split, since only the operator ever flips ``status`` (``specs/ADRs/AGENTS.md``'s
operator-only acceptance law), and superseding an ADR MOVES the whole record to
``specs/ADRs/_superseded/superseded.jsonl`` rather than rewriting a field in place (the
canon's own words: "a decision moves there when superseded").

Field set mirrors ``public/schemas/ADRs/decision-record-v1.schema.json`` exactly.

**No store instance is registered for this model in ``container.py`` at this fold**
(mirrors ``FindingRecord``'s own precedent). ``specs/ADRs/**`` has no CLI writer (this
task's own "NO new CLI verb") — an agent proposes/accepts/supersedes an ADR with plain
file tools, never through a code seam — so a ``build_adr_store`` composition-root
function would have zero call sites today: "a registration with no caller is dead code
behind a protocol." The generic ``infrastructure.jsonl_record_store.JsonlRecordStore``
already accepts this model's ``to_dict``/``from_dict`` pair unchanged the moment a real
consumer needs one — that registration lands in the task that adds the call site, not
here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

__all__ = ["AdrRecord"]


def _require_str(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"adr record missing required string field {key!r}")
    return value


def _optional_str(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"adr record field {key!r} must be a string")
    return value


@dataclass(frozen=True)
class AdrRecord:
    """One record per architecture decision (v0.5.0 specs-canon closure) — appended
    once to ``specs/ADRs/decisions.jsonl``. A superseded decision MOVES (never
    copies) to ``specs/ADRs/_superseded/superseded.jsonl`` in the same act that
    supersedes it — the id is never reused, never re-numbered.

    ``id`` is the zero-padded 4-digit sequence number as a string (``"0001"``),
    monotonic and gap-free across BOTH files together (the contract test's own
    invariant, ``tests/contract/test_adr_canon.py``).
    """

    id: str
    ts: str
    title: str
    status: str
    context: str
    decision: str
    consequences: str
    measured_by: str | None = None
    supersedes: str | None = None
    amends: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to the JSONL object shape. Every field is ALWAYS emitted (the
        optional cross-reference fields present as ``null`` when absent)."""
        return {
            "id": self.id,
            "ts": self.ts,
            "title": self.title,
            "status": self.status,
            "context": self.context,
            "decision": self.decision,
            "consequences": self.consequences,
            "measured_by": self.measured_by,
            "supersedes": self.supersedes,
            "amends": self.amends,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> AdrRecord:
        """Parse a JSONL object into an :class:`AdrRecord`. Raises ``ValueError`` on
        a malformed record (missing/typed-wrong required field) so tolerant readers
        can skip it."""
        return cls(
            id=_require_str(raw, "id"),
            ts=_require_str(raw, "ts"),
            title=_require_str(raw, "title"),
            status=_require_str(raw, "status"),
            context=_require_str(raw, "context"),
            decision=_require_str(raw, "decision"),
            consequences=_require_str(raw, "consequences"),
            measured_by=_optional_str(raw, "measured_by"),
            supersedes=_optional_str(raw, "supersedes"),
            amends=_optional_str(raw, "amends"),
        )
