"""``release-event-v1`` schema shape (v0.5.0 FR4, D3/D7/D11, T-050-11).

Intent: CONTRACT — SPEC v0.5.0 FR4 (seven event kinds, closed envelope, no
``session_id``). Size: SMALL — pure schema/document assertions, no I/O beyond reading
the packaged schema fixture.
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
    / "releases"
    / "release-event-v1.schema.json"
)

_SEVEN_KINDS = frozenset({"phase", "defined", "implemented", "shipped", "audited", "rc", "note"})


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def test_release_event_schema_closes_the_envelope_to_exactly_seven_kinds_no_session_id() -> None:
    """Draft 2020-12, ``additionalProperties: false`` at the envelope, ``event`` closed
    to exactly the seven canonical kinds (D3/D7/D11 — the first Draft's fifteen
    collapsed), and no ``session_id`` property anywhere in the envelope (a harness
    session id is PROTECTED and must never be committed into governance records)."""
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"ts", "event", "agent", "data"}
    assert "session_id" not in schema["properties"]
    assert set(schema["properties"]["event"]["enum"]) == _SEVEN_KINDS

    validator = Draft202012Validator(schema)

    valid_record = {
        "ts": "2026-08-27T10:31:16Z",
        "event": "defined",
        "agent": "product-engineer",
        "data": {"sha": "389166052c837769e31d3e79ccbf89e69c641ed8", "pr": None},
    }
    assert list(validator.iter_errors(valid_record)) == []

    with_session_id = {**valid_record, "session_id": "claude-sess-1"}
    assert list(validator.iter_errors(with_session_id)) != []

    eighth_kind = {**valid_record, "event": "archive"}
    assert list(validator.iter_errors(eighth_kind)) != []
