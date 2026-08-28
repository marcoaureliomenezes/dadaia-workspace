"""``decision-record-v1`` schema shape (v0.5.0 specs-canon closure, operator ruling
2026-08-28).

Intent: CONTRACT — v0.5.0 specs-canon closure

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
    / "ADRs"
    / "decision-record-v1.schema.json"
)

_BASE: dict[str, Any] = {
    "id": "0001",
    "ts": "2026-08-28T12:00:00Z",
    "title": "Features depend on ports, not adapters",
    "status": "proposed",
    "context": "Features need I/O but must stay unit-testable without real I/O.",
    "decision": "We will define a Protocol per I/O boundary and inject an adapter.",
    "consequences": "+ testable with fakes\n- one extra indirection layer",
    "measured_by": None,
    "supersedes": None,
    "amends": None,
}


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def test_decision_record_schema_is_draft_2020_12_valid_and_closes_the_envelope() -> None:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert set(schema["properties"]) == {
        "id",
        "ts",
        "title",
        "status",
        "context",
        "decision",
        "consequences",
        "measured_by",
        "supersedes",
        "amends",
    }


def test_a_valid_proposed_record_validates() -> None:
    validator = Draft202012Validator(_schema())
    assert list(validator.iter_errors(_BASE)) == []


def test_an_accepted_record_with_measured_by_validates() -> None:
    validator = Draft202012Validator(_schema())
    accepted = {**_BASE, "status": "accepted", "measured_by": "tests/contract/test_x.py"}
    assert list(validator.iter_errors(accepted)) == []


def test_rejects_an_unknown_property() -> None:
    validator = Draft202012Validator(_schema())
    with_extra = {**_BASE, "unexpected": "nope"}
    assert list(validator.iter_errors(with_extra)) != []


def test_rejects_an_invalid_status_value() -> None:
    validator = Draft202012Validator(_schema())
    bad = {**_BASE, "status": "in-review"}
    assert list(validator.iter_errors(bad)) != []


def test_rejects_a_non_4_digit_id() -> None:
    validator = Draft202012Validator(_schema())
    bad = {**_BASE, "id": "1"}
    assert list(validator.iter_errors(bad)) != []


@pytest.mark.parametrize("field_name", ["supersedes", "amends"])
def test_cross_reference_fields_accept_a_string_or_null(field_name: str) -> None:
    validator = Draft202012Validator(_schema())
    with_ref = {**_BASE, field_name: "0002"}
    assert list(validator.iter_errors(with_ref)) == []
