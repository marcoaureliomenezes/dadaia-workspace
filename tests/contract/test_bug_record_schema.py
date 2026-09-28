"""``bug-record-v1`` schema shape (v0.5.0 FR2, D11, T-050-07).

Intent: CONTRACT — SPEC v0.5.0 A2.1 (additionalProperties: false, per-property
x-mutability documents the immutable-core/write-once/mutable-governance split) plus
Draft 2020-12 self-validity of the schema document itself. Moved out of
``tests/unit/core/models/test_bug_record.py`` — a pure ``core`` model unit test that
must stay stdlib-only so ``tests/scripts/run_mutation_baseline.sh``'s isolated venv
(mutmut + pytest only, no third-party install beyond the tool itself) can still collect
it; schema-vs-model agreement is a CONTRACT-tier concern, not a unit-test one
(resolves bug
``mutation-baseline-core-models-scope-now-imports-jsonschema-isolated-venv-cannot-collect``).

Size: SMALL — pure schema/document assertions, no I/O beyond reading the packaged
schema fixture.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = (
    _REPO_ROOT / "dadaia_workspace" / "public" / "schemas" / "bugs" / "bug-record-v1.schema.json"
)

_AS_APPENDED: dict[str, Any] = {
    "id": "sample-bug",
    "ts": "2026-08-27T12:00:00Z",
    "reported_by": "dd-software-engineer",
    "title": "sample bug",
    "severity": "MEDIUM",
    "surface": "tests",
    "component": "features/bugs/service.py#BugService",
    "context": "dadaia-workspace",
    "symptom": "something broke",
    "repro": "run the thing",
    "expected": "it should not break",
    "status": "open",
    "cause": None,
    "caused_by": None,
    "resolved_release": None,
    "audited": None,
    "closed_at": None,
}


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def test_bug_record_schema_is_valid_draft_2020_12_and_closes_the_envelope() -> None:
    """A2.1: Draft 2020-12, ``additionalProperties: false``, every property carries
    ``x-mutability`` in the closed set {immutable-core, write-once, mutable-governance},
    and ``required`` covers exactly the immutable-core + mutable-governance fields —
    the write-once fields (absent until a fix lands, A2.2b) are deliberately excluded
    from ``required``, never silently. sa-spec-doc-033-duplicates-bugs-check#B7: the law
    points to the schema's x-mutability and lists no fields itself."""
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False

    properties = schema["properties"]
    write_once = {name for name, spec in properties.items() if spec["x-mutability"] == "write-once"}
    assert set(schema["required"]) == set(properties) - write_once

    mutability = {name: spec["x-mutability"] for name, spec in properties.items()}
    assert set(mutability.values()) == {"immutable-core", "write-once", "mutable-governance"}
    law = (_SCHEMA_PATH.parents[2] / "scaffold" / "bugs" / "AGENTS.md").read_text()
    assert "x-mutability" in law
    assert not [ln for ln in law.splitlines() if len(set(properties) & set(ln.split("`"))) >= 3]


def test_bug_record_schema_example_validates_as_appended_and_after_resolution() -> None:
    """A freshly registered record (write-once fields absent entirely, not even
    ``null`` — ``solution``/the FR23 evidence triple/``diff_direction``
    are not ``required``) validates; the SAME record after a fix resolves it (the
    write-once fields filled exactly once, ``status``/``cause``/``resolved_release``
    rewritten in place) stays valid too — proving the schema tolerates both the
    write-once fill and the in-place governance rewrite ``BugRecord.
    apply_governance_update`` performs, with every immutable-core field unchanged."""
    schema = _schema()
    validator = Draft202012Validator(schema)

    assert list(validator.iter_errors(_AS_APPENDED)) == []

    after_resolution = {
        **_AS_APPENDED,
        "status": "resolved",
        "closed_at": "2026-09-01T00:00:00Z",
        "cause": "root cause narrative",
        "resolved_release": "0.5.0",
        "solution": "the fix narrative",
        "evidence_loop": "pytest --collect-only -q tests/unit/core/models",
        "evidence_seam": "tests/contract/test_bug_record_schema.py::"
        "test_bug_record_schema_example_validates_as_appended_and_after_resolution",
        "evidence_diff": "net-neutral: relocated schema-dependent assertions to the contract tier",
    }
    assert list(validator.iter_errors(after_resolution)) == []

    immutable_names = {
        name
        for name, spec in schema["properties"].items()
        if spec["x-mutability"] == "immutable-core"
    }
    for name in immutable_names:
        assert _AS_APPENDED[name] == after_resolution[name], name


def test_bug_record_schema_rejects_an_unknown_property_and_a_bad_status() -> None:
    """``additionalProperties: false`` refuses an unknown key; ``status`` is a closed
    enum, not free text, and carries no ``picked`` value (v0.5.0 FR2 — the pick is the
    bundled definition commit, not a status)."""
    schema = _schema()
    validator = Draft202012Validator(schema)

    assert list(validator.iter_errors(_AS_APPENDED)) == []

    with_extra_key = {**_AS_APPENDED, "unexpected": "nope"}
    assert list(validator.iter_errors(with_extra_key)) != []

    with_bad_status = {**_AS_APPENDED, "status": "picked"}
    assert list(validator.iter_errors(with_bad_status)) != []


# --- 0.4.7 FR1 — the surface enum's feature arm is DERIVED, never restated -----------


def test_the_surface_names_no_library_fact() -> None:
    """sa-consumer-law-carries-library-facts#FR8.1: the schema projected beside every
    consumer's bugs.py carries no library layer or package list — a surface is the
    unit of the context's own tree that broke (REWRITE of the "restates no feature
    package name" test; its "is the layers plus the feature packages" sibling pinned the
    library arm and is deleted as the losing side)."""
    surface = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))["properties"]["surface"]

    assert "enum" not in surface and "x-enum-append" not in surface
    assert surface["type"] == "string" and surface["minLength"] == 1
    assert "dadaia_workspace" not in surface["description"]
