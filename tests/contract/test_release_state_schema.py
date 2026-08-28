"""``release-state-v1`` schema shape (v0.5.x, successor to
``test_release_event_schema.py`` — RELEASE.jsonl -> RELEASE.json migration).

Intent: CONTRACT — the schema closes the document to exactly the nine declared
top-level properties (plus the optional ``segment`` extension), each milestone object
closes to its own declared shape, and the schema is internally valid Draft 2020-12.
Size: SMALL — pure schema/document assertions, no I/O beyond reading the packaged
schema fixture.

``tests/contract/test_release_event_schema.py`` validated the now-deleted
``release-event-v1.schema.json`` (the append-only envelope this migration retires) —
it fails post-migration (criterion (a) feature removed, this commit) and is flagged
for a qa-engineer pruning verdict; this file is its replacement, not an amendment to
it.
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
    / "release-state-v1.schema.json"
)

_REQUIRED_TOP_LEVEL = frozenset(
    {"schema", "release", "phase", "rc", "defined", "implemented", "shipped", "audited", "log"}
)


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _minimal_document(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "schema": "release-state-v1",
        "release": "0.6.0",
        "phase": "IMPLEMENTATION",
        "rc": None,
        "defined": {"sha": "a" * 40, "ts": "2026-08-27T10:31:16Z"},
        "implemented": None,
        "shipped": None,
        "audited": None,
        "log": [],
    }
    base.update(overrides)
    return base


def test_schema_is_valid_draft202012_and_closes_the_document() -> None:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == _REQUIRED_TOP_LEVEL
    assert schema["properties"]["schema"]["const"] == "release-state-v1"


def test_a_minimal_document_validates() -> None:
    validator = Draft202012Validator(_schema())
    assert list(validator.iter_errors(_minimal_document())) == []


def test_wrong_schema_id_is_rejected() -> None:
    validator = Draft202012Validator(_schema())
    doc = _minimal_document(schema="release-event-v1")
    assert list(validator.iter_errors(doc)) != []


@pytest.mark.parametrize("kind", ["defined", "implemented", "shipped", "audited"])
def test_each_milestone_object_closes_to_its_own_declared_shape(kind: str) -> None:
    """An unknown key on a milestone object is rejected -- the schema keeps each
    milestone's shape closed, the same discipline the envelope itself carries."""
    validator = Draft202012Validator(_schema())
    doc = _minimal_document(**{kind: {"sha": "a" * 40, "ts": "2026-08-27T10:31:16Z", "bogus": 1}})
    assert list(validator.iter_errors(doc)) != [], f"{kind} must reject an unknown key"


def test_notes_entries_require_ts_agent_kind_text() -> None:
    validator = Draft202012Validator(_schema())
    doc = _minimal_document(log=[{"ts": "2026-08-27T10:31:16Z", "agent": "test"}])
    assert list(validator.iter_errors(doc)) != []

    doc_ok = _minimal_document(
        log=[
            {
                "ts": "2026-08-27T10:31:16Z",
                "agent": "test",
                "kind": "note",
                "text": "hello",
            }
        ]
    )
    assert list(validator.iter_errors(doc_ok)) == []


def test_segment_is_optional_and_pattern_constrained() -> None:
    validator = Draft202012Validator(_schema())
    assert list(validator.iter_errors(_minimal_document(segment="rc-1"))) == []
    assert list(validator.iter_errors(_minimal_document(segment="not-a-segment"))) != []
    # Absent entirely is valid -- `segment` is not in the required set.
    assert "segment" not in _schema()["required"]
