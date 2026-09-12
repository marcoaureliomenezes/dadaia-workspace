"""Unit tests for the ONE history-record shape, :class:`HistoRecord` (0.4.7 FR7).

Intent: CONTRACT — bug ``backlog-histo-writer-skips-write-time-denylist-redaction``.
The write-time denylist seam that lived on the deleted ``BacklogHistoRecord`` now
lives on ``HistoRecord``, the one shape every ``_histo.jsonl`` carries: a committed
exit snapshot's free text — including every string nested inside ``entry``, which IS
the removed live object — is masked through the SAME ``core.redaction.redact_text``
primitive ``BugRecord.redact`` calls, BEFORE the record is appended, never written raw
and caught later only at the push gate. Size: SMALL (pure dataclass, no I/O).
"""

from __future__ import annotations

from typing import Any

import pytest

from dadaia_workspace.core.models.histo import (
    TERMINAL_DISPOSITIONS,
    HistoRecord,
    is_terminal_disposition,
)

pytestmark = pytest.mark.unit


def _record(**overrides: object) -> HistoRecord:
    fields: dict[str, Any] = {
        "id": "some-slug",
        "ts": "2026-08-27",
        "disposition": "delivered",
        "release": "0.5.0",
        "reason": "a reason",
        "summary": "a summary",
        "entry": {"id": "some-slug", "description": "some body"},
    }
    fields.update(overrides)
    return HistoRecord(**fields)


def test_redact_masks_a_denylisted_term_nested_inside_entry() -> None:
    """``entry`` is the removed ``active[]`` object itself — an arbitrary JSON tree.
    A denylisted term buried in one of its values is masked, not merely the two
    top-level free-text strings."""
    record = _record(
        entry={
            "id": "some-slug",
            "description": "See .dadaia/reports/acme-corp-games/qa-engineer/report.html.",
            "intents": [{"change": "rename the acme-corp adapter"}],
        }
    )

    redacted = record.redact(denylist_terms=(("acme-corp", "private project/person identifier"),))

    assert redacted.entry is not None
    rendered = repr(redacted.entry)
    assert "acme-corp" not in rendered.lower()
    assert "[REDACTED-TERM]" in rendered


def test_redact_with_no_terms_is_byte_identical() -> None:
    """No-op default: a record redacted with no denylist terms is unchanged (mirrors
    ``BugRecord.redact()``'s own no-op default)."""
    record = _record(entry={"id": "some-slug", "description": "nothing sensitive here"})

    assert record.redact() == record


def test_redact_scrubs_every_non_identity_field() -> None:
    """A2.10-class regression guard: the redactable field set is DERIVED from
    ``HistoRecord``'s own dataclass metadata, never a hand-kept list — every free-text
    field carries the term through unless explicitly marked identity."""
    term = "acme-corp"
    record = _record(
        release=f"leaked {term} here",
        reason=f"leaked {term} here",
        summary=f"leaked {term} here",
        entry={"description": f"leaked {term} here"},
    )

    redacted = record.redact(denylist_terms=((term, "private client name"),))

    for name in ("release", "reason", "summary"):
        value = getattr(redacted, name)
        assert value is not None
        assert term not in value, f"field {name!r} was not scrubbed"
    assert term not in repr(redacted.entry)
    # Identity fields (id/ts/disposition) are never touched by denylist masking.
    assert redacted.id == "some-slug"
    assert redacted.ts == "2026-08-27"
    assert redacted.disposition == "delivered"


def test_redact_leaves_none_fields_none() -> None:
    """``release``/``reason``/``summary``/``entry`` are all optional — a ``None``
    field stays ``None`` through redaction, never coerced to a string."""
    record = _record(release=None, reason=None, summary=None, entry=None)

    redacted = record.redact(denylist_terms=(("acme-corp", "private client name"),))

    assert redacted.release is None
    assert redacted.reason is None
    assert redacted.summary is None
    assert redacted.entry is None


def test_redact_round_trips_through_to_dict() -> None:
    """The redacted record is what reaches the JSONL line: ``to_dict``/``from_dict``
    preserve the scrubbed ``entry`` tree exactly."""
    record = _record(entry={"description": "acme-corp is here"}).redact(
        denylist_terms=(("acme-corp", "private client name"),)
    )

    assert HistoRecord.from_dict(record.to_dict()) == record


@pytest.mark.parametrize("token", [*TERMINAL_DISPOSITIONS, "Delivered", " REJECTED "])
def test_is_terminal_disposition_accepts_the_one_vocabulary(token: str) -> None:
    assert is_terminal_disposition(token)


@pytest.mark.parametrize("token", [None, "", "picked", "candidate", "idea"])
def test_is_terminal_disposition_refuses_a_live_status(token: str | None) -> None:
    assert not is_terminal_disposition(token)
