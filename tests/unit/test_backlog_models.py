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
