"""Write-time bug-append redaction sees what the push gate refuses (SPEC v0.4.5 FR6,
T-045-19).

Intent: CONTRACT — SPEC v0.4.5 FR6/A6.1-A6.3/A6.5. Third recurrence of the class (SPEC
entry ``bug-append-write-time-denylist-redaction``): the operator denylist
(``infrastructure.privacy_check.load_privacy_terms``) was consulted only at push time
(``features.chokepoints.denylist_scan``) — a bug event whose free-text field carries a
denylisted term was written RAW by ``dadaia bugs append``, caught only later at the
push gate (twice, inside v0.4.4 alone, one forcing an ``rc-1`` history rewrite). This
pins the fix at the write-time seam: ``BugService.append_event`` (the SAME method
already enforcing stream coherence) now also enforces denylist-term masking, reusing
the SAME field-scrub call ``BugEvent.redact()`` already runs for IP/home-path leaks.
Architect ruling SOUND-WITH-AMENDMENT (``specs/releases/v0.4.5/reviews/FR23-firings.md``
"Firing 2") on commit eb03d01b: AM-1 deleted the CLI's superseded second ``.redact()``
call, AM-2 made the scrubbed field set schema-DERIVED (``_OPTIONAL_STR_FIELDS``, no
hand-kept list — A6.5).

Size: SMALL (directory-tiered ``unit`` — real ``tmp_path`` file I/O only, no
subprocess/network; matches the sibling redaction-matrix coverage already in
``test_jsonl_bug_store.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.models.bugs import BugEvent, redact_text
from dadaia_workspace.features.bugs.service import BugService
from dadaia_workspace.infrastructure.jsonl_bug_store import JsonlBugStore

_TS = "2026-08-26T10:00:00Z"


def _reported(bug_id: str, *, notes: str, title: str = "t") -> BugEvent:
    return BugEvent(
        bug_id=bug_id,
        event="reported",
        ts=_TS,
        reported_by="software-engineer",
        title=title,
        severity="HIGH",
        surface="s",
        component="c",
        context="dadaia-workspace",
        tags=(),
        symptom="sy",
        repro="re",
        expected="ex",
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Core seam — redact_text/BugEvent.redact accept the SAME (term, reason) pairs
# infrastructure.privacy_check.load_privacy_terms returns.
# ---------------------------------------------------------------------------


def test_redact_text_masks_a_denylisted_term_case_insensitively() -> None:
    """A6.1/A6.2: :func:`redact_text` masks a case-insensitive substring occurrence of
    an operator denylist term, leaving unrelated text untouched (A6.3 parity with the
    push-time scan's own case-insensitive substring semantics)."""
    out = redact_text(
        "deployment landed at ACME-Corp's staging box",
        denylist_terms=(("acme-corp", "private client name"),),
    )
    assert "acme-corp" not in out.lower()
    assert "[REDACTED-TERM]" in out
    assert "deployment landed at" in out
    assert "staging box" in out


def test_redact_text_with_no_terms_is_byte_identical_to_pre_fr6() -> None:
    """Every pre-FR6 caller of :func:`redact_text` (single positional arg) must stay
    byte-identical — the new parameter defaults to a no-op."""
    raw = "deployment landed at ACME-Corp's staging box"
    assert redact_text(raw) == raw


def test_bug_event_redact_masks_denylisted_term_across_free_text_fields() -> None:
    """A6.5: the denylist masking rides through the SAME field set + the SAME
    :func:`redact_text` call ``BugEvent.redact`` already uses for IP/home-path
    scrubbing — not a second, independently hand-kept field list."""
    event = BugEvent(
        bug_id="b1",
        event="reported",
        ts=_TS,
        reported_by="software-engineer",
        title="incident at consumer-vps-7",
        severity="HIGH",
        surface="s",
        component="c",
        context="dadaia-workspace",
        tags=(),
        symptom="sy",
        repro="re",
        expected="ex",
        notes="root cause traced to consumer-vps-7's disk",
    )

    redacted = event.redact(denylist_terms=(("consumer-vps-7", "private host name"),))

    assert "consumer-vps-7" not in (redacted.title or "")
    assert "consumer-vps-7" not in (redacted.notes or "")
    assert "[REDACTED-TERM]" in (redacted.title or "")
    assert "[REDACTED-TERM]" in (redacted.notes or "")
    # Structured fields are never touched by denylist masking either.
    assert redacted.bug_id == "b1"
    assert redacted.context == "dadaia-workspace"


# ---------------------------------------------------------------------------
# THE RED test (A6.1) — BugService.append_event is the enforced write-time seam.
# ---------------------------------------------------------------------------


def test_bug_service_append_event_masks_denylisted_term_before_it_reaches_disk(
    tmp_path: Path,
) -> None:
    """Before the fix: a bug event whose ``notes`` field carries an operator
    denylisted term is written RAW to ``bugs.jsonl`` — ``BugService.append_event``
    only ever threaded IP/home-path masking through ``BugEvent.redact()``, never the
    operator denylist. Constructing ``BugService`` with the SAME ``(term, reason)``
    shape ``load_privacy_terms`` returns (the CLI wires the real loader through
    ``container.load_denylist_terms``; this unit test injects the pair directly,
    mirroring the sibling redaction-matrix tests' own convention) proves the term
    never reaches the committed record."""
    store = JsonlBugStore(tmp_path / "bugs")
    service = BugService(store, denylist_terms=(("acme-corp", "private client name"),))

    service.append_event(
        _reported("leaky-denylist", notes="deployment landed at acme-corp's staging box")
    )

    persisted = list(store.iter_events())[-1]
    assert persisted.notes is not None
    assert "acme-corp" not in persisted.notes.lower()
    assert "[REDACTED-TERM]" in persisted.notes


def test_bug_service_with_no_denylist_terms_stays_byte_identical_to_pre_fr6(
    tmp_path: Path,
) -> None:
    """A6.3 sibling guarantee for the write-time seam: a ``BugService`` constructed
    with no denylist terms (the pre-FR6 default) behaves exactly as before — only
    IP/home-path masking runs; an arbitrary term is left alone."""
    store = JsonlBugStore(tmp_path / "bugs")
    service = BugService(store)  # no denylist_terms -> defaults to ()

    service.append_event(
        _reported("not-leaky", notes="deployment landed at acme-corp's staging box")
    )

    persisted = list(store.iter_events())[-1]
    assert persisted.notes == "deployment landed at acme-corp's staging box"


# ---------------------------------------------------------------------------
# AM-2 (architect ruling, FR23-firings.md "Firing 2") — A6.5: the scrubbed field set
# must be DERIVED from the schema file, never a hand-kept list either in production
# (BugEvent.redact now iterates _OPTIONAL_STR_FIELDS) or in this test.
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[4]
    / "dadaia_workspace"
    / "public"
    / "schemas"
    / "bugs"
    / "bug-event-v1.schema.json"
)


def _schema_optional_string_fields() -> set[str]:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    identity_fields = set(schema["required"])  # bug_id, event, ts, reported_by
    return {
        name
        for name, prop in schema["properties"].items()
        if prop.get("type") == "string" and name not in identity_fields
    }


def test_bug_event_redact_scrubs_every_schema_string_field_derived_from_schema() -> None:
    """A6.5: regression guard for the T-043-23 -> T-044-62 chain (a hand-kept field
    list twice missed a newly added free-text field). Reads the REAL schema file at
    test time and proves ``BugEvent.redact()`` scrubs every optional string property
    it names — title/severity/surface/component/context/superseded_by included, not
    just the narrower pre-AM-2 set."""
    schema_fields = _schema_optional_string_fields()
    term = "acme-corp"
    leaky = {name: f"leaked {term} here" for name in schema_fields}
    event = BugEvent(bug_id="b1", event="reported", ts=_TS, reported_by="se", **leaky)

    redacted = event.redact(denylist_terms=((term, "private client name"),))

    for name in schema_fields:
        value = getattr(redacted, name)
        assert value is not None
        assert term not in value, f"schema field {name!r} was not scrubbed"
