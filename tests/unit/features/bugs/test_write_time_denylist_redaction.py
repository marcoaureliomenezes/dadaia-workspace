"""Write-time bug-record redaction sees what the push gate refuses (SPEC v0.4.5 FR6,
T-045-19). Rewritten at v0.5.0 T-050-08 against ``BugRecord``/``BugService`` (the event
fold and ``JsonlBugStore`` it exercised are deleted).

Intent: CONTRACT — SPEC v0.4.5 FR6/A6.1-A6.3/A6.5, carried forward by v0.5.0 A2.6 (the
SAME redaction seam now covers ``BugRecord``'s write paths too — registration AND the
governance-update seam, ``BugService.apply_update``).

Third recurrence of the class (SPEC entry ``bug-append-write-time-denylist-redaction``):
the operator denylist (``infrastructure.privacy_check.load_privacy_terms``) was
consulted only at push time (``features.chokepoints.denylist_scan``) — a bug record
whose free-text field carries a denylisted term was written RAW, caught only later at
the push gate. This pins the fix at the write-time seam: ``BugService.register``/
``apply_update`` (the SAME service already enforcing the record-store seam) enforces
denylist-term masking via ``BugRecord.redact()``.

Size: SMALL (directory-tiered ``unit`` — real ``tmp_path`` file I/O only, no
subprocess/network; matches the sibling redaction-matrix coverage in
``test_control_format_char_sanitation.py``).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.bugs import BugRecord, redact_text
from dadaia_workspace.features.bugs.service import BugService
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

from ._bug_record_helpers import bug_record_store

_TS = "2026-08-26T10:00:00Z"


def _register(
    store: JsonlRecordStore[BugRecord],
    bug_id: str,
    *,
    denylist_terms: tuple[tuple[str, str], ...] = (),
    notes: str,
    title: str = "t",
) -> None:
    service = BugService(store, denylist_terms=denylist_terms)
    service.register(
        bug_id=bug_id,
        ts=_TS,
        reported_by="software-engineer",
        title=title,
        severity="HIGH",
        surface="bugs",
        component="c",
        context="dadaia-workspace",
        symptom=notes,
        repro="re",
        expected="ex",
    )


# ---------------------------------------------------------------------------
# Core seam — redact_text/BugRecord.redact accept the SAME (term, reason) pairs
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


def test_bug_record_redact_masks_denylisted_term_across_free_text_fields() -> None:
    """A6.5: the denylist masking rides through the SAME field set + the SAME
    :func:`redact_text` call ``BugRecord.redact`` already uses for IP/home-path
    scrubbing — not a second, independently hand-kept field list."""
    record = BugRecord(
        id="b1",
        ts=_TS,
        reported_by="software-engineer",
        title="incident at consumer-vps-7",
        severity="HIGH",
        surface="bugs",
        component="c",
        context="dadaia-workspace",
        symptom="root cause traced to consumer-vps-7's disk",
        repro="re",
        expected="ex",
        status="open",
    )

    redacted = record.redact(denylist_terms=(("consumer-vps-7", "private host name"),))

    assert "consumer-vps-7" not in redacted.title
    assert "consumer-vps-7" not in redacted.symptom
    assert "[REDACTED-TERM]" in redacted.title
    assert "[REDACTED-TERM]" in redacted.symptom
    # Identity fields are never touched by denylist masking either.
    assert redacted.id == "b1"
    assert redacted.context == "dadaia-workspace"


# ---------------------------------------------------------------------------
# THE RED test (A6.1) — BugService.register is the enforced write-time seam.
# ---------------------------------------------------------------------------


def test_bug_service_register_masks_denylisted_term_before_it_reaches_disk(
    tmp_path: Path,
) -> None:
    """Before the fix: a bug record whose ``symptom`` field carries an operator
    denylisted term is written RAW to ``bugs.jsonl`` — ``BugService.register`` only
    ever threaded IP/home-path masking through ``BugRecord.redact()``, never the
    operator denylist. Constructing ``BugService`` with the SAME ``(term, reason)``
    shape ``load_privacy_terms`` returns (the CLI wires the real loader through
    ``container.load_denylist_terms``; this unit test injects the pair directly)
    proves the term never reaches the committed record."""
    store = bug_record_store(tmp_path)

    _register(
        store,
        "leaky-denylist",
        denylist_terms=(("acme-corp", "private client name"),),
        notes="deployment landed at acme-corp's staging box",
    )

    persisted = list(store.iter_records())[-1]
    assert "acme-corp" not in persisted.symptom.lower()
    assert "[REDACTED-TERM]" in persisted.symptom


def test_bug_service_with_no_denylist_terms_stays_byte_identical_to_pre_fr6(
    tmp_path: Path,
) -> None:
    """A6.3 sibling guarantee for the write-time seam: a ``BugService`` constructed
    with no denylist terms (the pre-FR6 default) behaves exactly as before — only
    IP/home-path masking runs; an arbitrary term is left alone."""
    store = bug_record_store(tmp_path)

    _register(store, "not-leaky", notes="deployment landed at acme-corp's staging box")

    persisted = list(store.iter_records())[-1]
    assert persisted.symptom == "deployment landed at acme-corp's staging box"


def test_bug_service_apply_update_also_masks_a_denylisted_term(tmp_path: Path) -> None:
    """A2.6: the SAME redaction seam covers the governance-UPDATE write path too, not
    just registration — a resolve carrying a denylisted term in ``solution`` is masked
    identically."""
    store = bug_record_store(tmp_path)
    _register(store, "resolved-leaky", notes="clean symptom")
    service = BugService(store, denylist_terms=(("acme-corp", "private client name"),))

    updated = service.apply_update(
        "resolved-leaky",
        {"solution": "root-caused at acme-corp's staging box; regression test added"},
    )

    assert "acme-corp" not in (updated.solution or "").lower()
    assert "[REDACTED-TERM]" in (updated.solution or "")


# ---------------------------------------------------------------------------
# AM-2 (architect ruling, FR23-firings.md "Firing 2") — A6.5/A2.10: the scrubbed field
# set must be DERIVED from BugRecord's OWN field metadata, never a hand-kept list.
# ---------------------------------------------------------------------------


def test_bug_record_redact_scrubs_every_non_identity_field() -> None:
    """A2.6/A2.10: regression guard for the T-043-23 -> T-044-62 chain (a hand-kept
    field list twice missed a newly added free-text field). Every free-text field
    ``BugRecord.redact()`` derives from its OWN dataclass metadata (never
    ``id``/``ts``/``reported_by``, the identity fields) is scrubbed."""
    term = "acme-corp"
    record = BugRecord(
        id="b1",
        ts=_TS,
        reported_by="software-engineer",
        title=f"leaked {term} here",
        severity="HIGH",
        surface="bugs",
        component=f"leaked {term} here",
        context=f"leaked {term} here",
        symptom=f"leaked {term} here",
        repro=f"leaked {term} here",
        expected=f"leaked {term} here",
        status="resolved",
        cause=f"leaked {term} here",
        caused_by=None,
        lineage_source=None,
        registration_commit=None,
        registration_granularity=None,
        resolved_commit=None,
        resolution_granularity=None,
        resolved_release=f"leaked {term} here",
        audited=None,
        root_cause=f"leaked {term} here",
        solution=f"leaked {term} here",
    )

    redacted = record.redact(denylist_terms=((term, "private client name"),))

    for name in (
        "title",
        "component",
        "context",
        "symptom",
        "repro",
        "expected",
        "cause",
        "resolved_release",
        "root_cause",
        "solution",
    ):
        value = getattr(redacted, name)
        assert value is not None
        assert term not in value, f"field {name!r} was not scrubbed"
    # Identity fields never touched.
    assert redacted.id == "b1"
    assert redacted.ts == _TS
    assert redacted.reported_by == "software-engineer"
