"""Unit tests for the ``intents[]`` backlog schema (T-25-01, SPEC §3.1).

Pure typed ``Subject``/``Intent`` dataclasses with per-kind ref validation. ``code`` refs
are module-relative ``path#symbol`` — absolute / operator-local paths and private repo names
are rejected (SPEC §3.8 finding #7). No resolution/binding lives here (that is T-25-02).
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


# ── SubjectKind ───────────────────────────────────────────────────────────────


def test_subject_kind_members() -> None:
    assert {k.value for k in SubjectKind} == {
        "code",
        "api",
        "cli",
        "panel",
        "doc",
        "invariant",
        "catalog",
    }


# ── valid subjects per kind ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("kind", "ref"),
    [
        (SubjectKind.CODE, "dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind"),
        (SubjectKind.CLI, "backlog doctor"),
        (SubjectKind.CATALOG, "panel"),
        (SubjectKind.DOC, "SPEC-DOC-031"),
        (SubjectKind.INVARIANT, "INV-no-claude-at-L2"),
        (SubjectKind.PANEL, "panel:/api/dadaia-workflows"),
        (SubjectKind.API, "api:/api/kanban"),
    ],
)
def test_valid_subject_constructs(kind: SubjectKind, ref: str) -> None:
    subject = Subject(kind=kind, ref=ref)
    assert subject.kind is kind
    assert subject.ref == ref


def test_intent_is_frozen() -> None:
    intent = Intent(subject=Subject(SubjectKind.INVARIANT, "INV-1"), change="x")
    with pytest.raises(AttributeError):
        intent.change = "y"  # type: ignore[misc]


# ── code ref validation (the privacy-critical one) ──────────────────────────────


def test_code_ref_requires_hash_symbol() -> None:
    with pytest.raises(ValueError, match="path#symbol"):
        Subject(SubjectKind.CODE, "dadaia_workspace/core/models/lifecycle.py")


def test_code_ref_rejects_absolute_path() -> None:
    with pytest.raises(ValueError, match="module-relative|absolute"):
        Subject(SubjectKind.CODE, "/home/marco/workspace/foo.py#Bar")


def test_code_ref_rejects_home_traversal() -> None:
    with pytest.raises(ValueError, match="module-relative|operator-local"):
        Subject(SubjectKind.CODE, "~/secret/foo.py#Bar")


def test_code_ref_rejects_parent_traversal() -> None:
    with pytest.raises(ValueError, match="module-relative|traversal"):
        Subject(SubjectKind.CODE, "../other-repo/foo.py#Bar")


def test_code_ref_rejects_empty_symbol() -> None:
    with pytest.raises(ValueError):
        Subject(SubjectKind.CODE, "dadaia_workspace/core/foo.py#")


def test_empty_ref_rejected_for_all_kinds() -> None:
    for kind in SubjectKind:
        with pytest.raises(ValueError):
            Subject(kind, "")


def test_blank_change_rejected() -> None:
    with pytest.raises(ValueError, match="change"):
        Intent(subject=Subject(SubjectKind.INVARIANT, "INV-1"), change="   ")


# ── (de)serialization round-trip ────────────────────────────────────────────────


def test_parse_intents_round_trip() -> None:
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


def test_parse_intents_none_is_empty() -> None:
    assert parse_intents(None) == []


def test_parse_intents_rejects_non_list() -> None:
    with pytest.raises(ValueError, match="list"):
        parse_intents({"subject": {}})  # type: ignore[arg-type]


def test_parse_intents_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="kind"):
        parse_intents([{"subject": {"kind": "bogus", "ref": "x"}, "change": "c"}])


def test_parse_intents_rejects_missing_change() -> None:
    with pytest.raises(ValueError, match="change"):
        parse_intents([{"subject": {"kind": "invariant", "ref": "INV-1"}}])


def test_parse_intents_rejects_missing_subject() -> None:
    with pytest.raises(ValueError, match="subject"):
        parse_intents([{"change": "c"}])
