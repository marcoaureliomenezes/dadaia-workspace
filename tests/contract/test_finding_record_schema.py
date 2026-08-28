"""``finding-record-v1`` schema shape (v0.5.0 FR13, D5/D11, T-050-23).

Intent: CONTRACT — SPEC v0.5.0 A13.1 (additionalProperties: false, per-property
x-mutability documents the immutable/mutable split) plus the valid-JSON example seeded
straight from SPEC.md FR13 (the "as appended" record).

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
    _REPO_ROOT
    / "dadaia_workspace"
    / "public"
    / "schemas"
    / "audits"
    / "finding-record-v1.schema.json"
)


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def test_finding_record_schema_closes_the_envelope_and_documents_mutability_per_property() -> None:
    """A13.1: Draft 2020-12, ``additionalProperties: false``, every property required
    (present as ``null`` until a governance field is set — mirrors ``bug-record-v1``),
    and every property carries ``x-mutability`` in the closed set {immutable-core,
    mutable-governance} — findings carry no write-once field (A13's own text: only the
    three governance fields, ``disposition``/``release``/``reason``, are ever rewritten
    in place)."""
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False

    properties = schema["properties"]
    assert set(schema["required"]) == set(properties)
    assert set(properties) == {
        "id",
        "pillar",
        "severity",
        "refs",
        "claim",
        "evidence",
        "disposition",
        "release",
        "reason",
    }

    mutability = {name: spec["x-mutability"] for name, spec in properties.items()}
    assert set(mutability.values()) == {"immutable-core", "mutable-governance"}
    assert {name for name, cat in mutability.items() if cat == "mutable-governance"} == {
        "disposition",
        "release",
        "reason",
    }


def test_finding_record_schema_example_from_spec_validates_both_before_and_after_disposition() -> (
    None
):
    """A13.1: the FR13 prose example (as appended, ``disposition: "open"``) is valid
    JSON that seeds this fixture, AND the SAME record after its remediation release
    (every immutable field byte-identical, only the three governance fields rewritten)
    stays valid — proving the schema tolerates the in-place governance rewrite SPEC
    FR13 describes."""
    schema = _schema()
    validator = Draft202012Validator(schema)

    as_appended = {
        "id": "20261020-five-release-window-F003",
        "pillar": "bugs",
        "severity": "HIGH",
        "refs": [
            "certify-skip-detail-leaks-full-codex-output",
            "codex-live-probe-gate-checks-presence-not-usability",
            "<sha-B>",
            "<sha-A>",
        ],
        "claim": (
            "fix-induced bug: the skip-detail leak rides the second render path the "
            "probe-gate fix introduced, and the probe-gate bug resolved without a "
            "structural cause"
        ),
        "evidence": (
            "git show <sha-A> -- dadaia_workspace/features/certification (second "
            "render path added); BUGS.jsonl "
            "codex-live-probe-gate-checks-presence-not-usability cause=null"
        ),
        "disposition": "open",
        "release": None,
        "reason": None,
    }
    assert list(validator.iter_errors(as_appended)) == []

    after_remediation = {
        **as_appended,
        "disposition": "fixed",
        "release": "<the remediation release id>",
        "reason": "one render path; regression test at the formatter seam",
    }
    assert list(validator.iter_errors(after_remediation)) == []

    # Every immutable-core field is byte-identical across both states.
    immutable_names = {
        name
        for name, spec in schema["properties"].items()
        if spec["x-mutability"] == "immutable-core"
    }
    for name in immutable_names:
        assert as_appended[name] == after_remediation[name], name


def test_finding_record_schema_rejects_an_unknown_property_and_a_bad_disposition() -> None:
    """``additionalProperties: false`` refuses an unknown key; ``disposition`` is a
    closed enum, not free text."""
    schema = _schema()
    validator = Draft202012Validator(schema)

    base = {
        "id": "20260101-sample-F001",
        "pillar": "specs",
        "severity": "LOW",
        "refs": ["some/path.py:10"],
        "claim": "a claim",
        "evidence": "a command -> a redacted result",
        "disposition": "open",
        "release": None,
        "reason": None,
    }
    assert list(validator.iter_errors(base)) == []

    with_extra_key = {**base, "unexpected": "nope"}
    assert list(validator.iter_errors(with_extra_key)) != []

    with_bad_disposition = {**base, "disposition": "picked"}
    assert list(validator.iter_errors(with_bad_disposition)) != []
