"""Unit tests for the ``intents[]`` backlog schema (T-25-01, SPEC §3.1).

Pure typed ``Subject``/``Intent`` dataclasses with per-kind ref validation. ``code`` refs
are module-relative ``path#symbol`` — absolute / operator-local paths and private repo names
are rejected (SPEC §3.8 finding #7). No resolution/binding lives here (that is T-25-02).

Operator-local-path rejection = privacy law — rows survive below in the reject table, plus
the absolute-path case kept standalone.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.backlog import (
    BacklogHistoRecord,
    Intent,
    Subject,
    SubjectKind,
    parse_intents,
    serialize_intents,
)

pytestmark = pytest.mark.unit


def test_subject_kind_members_valid_construction_and_intent_is_frozen() -> None:
    assert {k.value for k in SubjectKind} == {
        "code",
        "api",
        "cli",
        "panel",
        "doc",
        "invariant",
        "catalog",
    }
    valid = [
        (SubjectKind.CODE, "dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind"),
        (SubjectKind.CLI, "backlog doctor"),
        (SubjectKind.CATALOG, "panel"),
        (SubjectKind.DOC, "SPEC-DOC-031"),
        (SubjectKind.INVARIANT, "INV-no-claude-at-L2"),
        (SubjectKind.PANEL, "panel:/api/workflow-catalog"),
        (SubjectKind.API, "api:/api/kanban"),
    ]
    for kind, ref in valid:
        subject = Subject(kind=kind, ref=ref)
        assert subject.kind is kind
        assert subject.ref == ref

    intent = Intent(subject=Subject(SubjectKind.INVARIANT, "INV-1"), change="x")
    with pytest.raises(AttributeError):
        intent.change = "y"  # type: ignore[misc]


# ── code ref validation privacy law — the absolute-path rejection is the CRIT row ──


@pytest.mark.parametrize(
    ("name", "kind", "ref", "match"),
    [
        (
            # PRIVACY: an absolute operator-local path must never bind as a code ref.
            "rejects_absolute_path",
            SubjectKind.CODE,
            "/home/marco/workspace/foo.py#Bar",
            "module-relative|absolute",
        ),
        (
            "requires_hash_symbol",
            SubjectKind.CODE,
            "dadaia_workspace/core/models/lifecycle.py",
            "path#symbol",
        ),
        (
            # PRIVACY: `~` home-relative refs must never bind.
            "rejects_home_traversal",
            SubjectKind.CODE,
            "~/secret/foo.py#Bar",
            "module-relative|operator-local",
        ),
        (
            # PRIVACY: `../` parent traversal must never escape the source root.
            "rejects_parent_traversal",
            SubjectKind.CODE,
            "../other-repo/foo.py#Bar",
            "module-relative|traversal",
        ),
        (
            "rejects_empty_symbol",
            SubjectKind.CODE,
            "dadaia_workspace/core/foo.py#",
            None,
        ),
    ],
)
def test_code_ref_reject_table(name: str, kind: SubjectKind, ref: str, match: str | None) -> None:
    if match is not None:
        with pytest.raises(ValueError, match=match):
            Subject(kind, ref)
    else:
        with pytest.raises(ValueError):
            Subject(kind, ref)


def test_empty_ref_rejected_for_all_kinds_and_blank_change_rejected() -> None:
    for kind in SubjectKind:
        with pytest.raises(ValueError):
            Subject(kind, "")
    with pytest.raises(ValueError, match="change"):
        Intent(subject=Subject(SubjectKind.INVARIANT, "INV-1"), change="   ")


# ── (de)serialization round-trip + rejection table ──────────────────────────────


def test_parse_intents_round_trip_and_none_is_empty() -> None:
    raw = [
        {
            "subject": {
                "kind": "code",
                "ref": "dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind",
            },
            "change": "remove OPENCODE_RUN",
        },
        {
            "subject": {"kind": "doc", "ref": "SPEC-DOC-031"},
            "change": "supersede prose heuristic",
        },
    ]
    intents = parse_intents(raw)
    assert len(intents) == 2
    assert intents[0].subject.kind is SubjectKind.CODE
    assert intents[0].change == "remove OPENCODE_RUN"
    assert serialize_intents(intents) == raw

    assert parse_intents(None) == []


def test_subject_surface_new_round_trip_and_default() -> None:
    """Bugs backlog-independent-cli-items-false-conflict-044 +
    backlog-cli-intent-hallucinated-anchor-045: an item introducing a genuinely NEW
    surface (e.g. a new CLI command) has NO existing registry anchor to bind — the
    author was forced to mis-bind an existing anchor (false conflict) or invent a ref
    (unrecoverable unresolved block). ``surface: new`` declares the new surface as a
    first-class subject; the default stays ``existing`` and serialization stays
    byte-stable for every existing item."""
    raw = [
        {
            "subject": {"kind": "cli", "ref": "hello", "surface": "new"},
            "change": "add a hello command printing a greeting",
        },
        {
            "subject": {"kind": "doc", "ref": "SPEC-DOC-031"},
            "change": "document it",
        },
    ]
    intents = parse_intents(raw)
    assert intents[0].subject.surface == "new"
    assert intents[1].subject.surface == "existing"
    # Round trip: `surface` is emitted only when new — existing items stay byte-stable.
    assert serialize_intents(intents) == raw

    with pytest.raises(ValueError, match="surface"):
        parse_intents([{"subject": {"kind": "cli", "ref": "x", "surface": "bogus"}, "change": "c"}])


@pytest.mark.parametrize(
    ("name", "payload", "match"),
    [
        ("non_list", {"subject": {}}, "list"),
        ("unknown_kind", [{"subject": {"kind": "bogus", "ref": "x"}, "change": "c"}], "kind"),
        (
            "missing_change",
            [{"subject": {"kind": "invariant", "ref": "INV-1"}}],
            "change",
        ),
        ("missing_subject", [{"change": "c"}], "subject"),
    ],
)
def test_parse_intents_reject_table(name: str, payload: object, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        parse_intents(payload)  # type: ignore[arg-type]


# ═════════════════════════════════════════════════════════════════════════════════
# BacklogHistoRecord.redact() — write-time denylist redaction (bug
# backlog-histo-writer-skips-write-time-denylist-redaction). The SAME defect class
# BugRecord already had fixed twice (T-043-23 -> T-044-62 -> T-045-19, SPEC v0.4.5
# FR6): a committed histo snapshot's free-text fields (``entry_md`` above all) must be
# masked through the SAME ``redact_text`` seam BEFORE the record is appended, never
# written raw and caught later only at the push gate.
# ═════════════════════════════════════════════════════════════════════════════════


def _histo_record(**overrides: object) -> BacklogHistoRecord:
    fields: dict[str, object] = {
        "id": "some-slug",
        "ts": "2026-08-27",
        "disposition": "CONSUMED",
        "reason": "a reason",
        "release": "v0.5.0",
        "by": "project-manager",
        "entry_md": "### some-slug\nsome body",
        "entry_md_source": "live exit",
    }
    fields.update(overrides)
    return BacklogHistoRecord(**fields)  # type: ignore[arg-type]


def test_backlog_histo_record_redact_masks_denylisted_term_in_entry_md() -> None:
    """A5.1/A2.6-class fix: a denylisted term embedded in ``entry_md`` (the free-text
    exit snapshot) is masked by :meth:`BacklogHistoRecord.redact`, mirroring
    ``BugRecord.redact`` exactly — same ``(term, reason)`` shape, same
    ``[REDACTED-TERM]`` placeholder."""
    record = _histo_record(
        entry_md="See .dadaia/reports/acme-corp-games/qa-engineer/report.html for detail."
    )

    redacted = record.redact(denylist_terms=(("acme-corp", "private project/person identifier"),))

    assert redacted.entry_md is not None
    assert "acme-corp" not in redacted.entry_md.lower()
    assert "[REDACTED-TERM]" in redacted.entry_md


def test_backlog_histo_record_redact_with_no_terms_is_byte_identical() -> None:
    """No-op default: a record redacted with no denylist terms is unchanged (mirrors
    ``BugRecord.redact()``'s own no-op default)."""
    record = _histo_record(entry_md="nothing sensitive here")

    assert record.redact() == record


def test_backlog_histo_record_redact_scrubs_every_non_identity_field() -> None:
    """A2.10-class regression guard: the redactable field set is DERIVED from
    ``BacklogHistoRecord``'s own dataclass metadata, never a hand-kept list — every
    free-text field carries the term through unless explicitly marked identity."""
    term = "acme-corp"
    record = _histo_record(
        disposition=f"CONSUMED — {term}",
        reason=f"leaked {term} here",
        release=f"leaked {term} here",
        entry_md=f"leaked {term} here",
        entry_md_source=f"leaked {term} here",
    )

    redacted = record.redact(denylist_terms=((term, "private client name"),))

    for name in ("disposition", "reason", "release", "entry_md", "entry_md_source"):
        value = getattr(redacted, name)
        assert value is not None
        assert term not in value, f"field {name!r} was not scrubbed"
    # Identity fields (id/ts/by) are never touched by denylist masking.
    assert redacted.id == "some-slug"
    assert redacted.ts == "2026-08-27"
    assert redacted.by == "project-manager"


def test_backlog_histo_record_redact_leaves_none_fields_none() -> None:
    """``reason``/``release``/``entry_md``/``entry_md_source`` are all optional — a
    ``None`` free-text field stays ``None`` through redaction, never coerced to a
    string."""
    record = _histo_record(reason=None, release=None, entry_md=None, entry_md_source=None)

    redacted = record.redact(denylist_terms=(("acme-corp", "private client name"),))

    assert redacted.reason is None
    assert redacted.release is None
    assert redacted.entry_md is None
    assert redacted.entry_md_source is None
