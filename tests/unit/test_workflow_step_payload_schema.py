"""Schema-file tests for the workflow-step handoff schemas (v0.1.30 / T-30-D-02).

Pins A21's static half: the NEW envelope schema (`workflow-step-payload-v1`) and the
run-steps ledger shape schema (`lifecycle-run-workflow-steps-v1`) are well-formed
Draft 2020-12 JSON Schemas, and representative documents validate (and malformed ones
are rejected). The dynamic half — the resolver validating real produced payloads against
these contracts — lands with the resolver (T-30-D-03).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

_SCHEMAS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "schemas"


def _load(name: str) -> dict[str, object]:
    return json.loads((_SCHEMAS / name).read_text(encoding="utf-8"))


def _envelope_schema() -> dict[str, object]:
    return _load("workflow-step-payload-v1.schema.json")


def _ledger_schema() -> dict[str, object]:
    return _load("lifecycle-run-workflow-steps-v1.schema.json")


def _valid_envelope() -> dict[str, object]:
    return {
        "schema_version": "workflow-step-payload-v1",
        "run_id": "run-1",
        "producer_step": "release_scope",
        "attempt": 0,
        "output_schema": "release-scope-handoff-v1",
        "produced_at": "2026-06-27T12:00:00Z",
        "retention_mode": "delete_after_consumed",
        "declared_consumers": ["spec_create"],
        "payload": {"summary": "scope locked"},
    }


def _valid_ledger_record() -> dict[str, object]:
    return {
        "run_id": "run-1",
        "producer_step": "release_scope",
        "attempt": 0,
        "output_schema": "release-scope-handoff-v1",
        "payload_ref": ".dadaia/runs/lifecycle/run-1/steps/001-release_scope-attempt-0.step-payload.json",
        "content_hash": "a" * 64,
        "produced_at": "2026-06-27T12:00:00Z",
        "retention_mode": "delete_after_consumed",
        "declared_consumers": ["spec_create"],
        "consumptions": [
            {
                "consumer_step": "spec_create",
                "consumer_attempt": 0,
                "consumed_at": "2026-06-27T12:05:00Z",
            }
        ],
    }


# --- schemas are well-formed ------------------------------------------------------


def test_envelope_schema_is_well_formed() -> None:
    Draft202012Validator.check_schema(_envelope_schema())


def test_ledger_schema_is_well_formed() -> None:
    Draft202012Validator.check_schema(_ledger_schema())


def test_schemas_do_not_touch_generic_handoff_schema() -> None:
    """A21/anti-slop: the new schemas are separate; handoff-v1.1 is never mutated."""
    assert _envelope_schema()["$id"] == "workflow-step-payload-v1"
    assert _ledger_schema()["$id"] == "lifecycle-run-workflow-steps-v1"


# --- envelope validation ----------------------------------------------------------


def test_valid_envelope_validates() -> None:
    Draft202012Validator(_envelope_schema()).validate(_valid_envelope())


def test_envelope_rejects_wrong_schema_version() -> None:
    bad = _valid_envelope()
    bad["schema_version"] = "handoff-v1.1"
    with pytest.raises(ValidationError):
        Draft202012Validator(_envelope_schema()).validate(bad)


def test_envelope_rejects_missing_payload() -> None:
    bad = _valid_envelope()
    del bad["payload"]
    with pytest.raises(ValidationError):
        Draft202012Validator(_envelope_schema()).validate(bad)


def test_envelope_rejects_negative_attempt() -> None:
    bad = _valid_envelope()
    bad["attempt"] = -1
    with pytest.raises(ValidationError):
        Draft202012Validator(_envelope_schema()).validate(bad)


def test_envelope_rejects_unknown_retention_mode() -> None:
    bad = _valid_envelope()
    bad["retention_mode"] = "keep_forever"
    with pytest.raises(ValidationError):
        Draft202012Validator(_envelope_schema()).validate(bad)


def test_envelope_rejects_additional_properties() -> None:
    bad = _valid_envelope()
    bad["surprise"] = 1
    with pytest.raises(ValidationError):
        Draft202012Validator(_envelope_schema()).validate(bad)


def test_envelope_rejects_non_z_timestamp() -> None:
    bad = _valid_envelope()
    bad["produced_at"] = "2026-06-27 12:00:00"
    with pytest.raises(ValidationError):
        Draft202012Validator(_envelope_schema()).validate(bad)


# --- ledger validation ------------------------------------------------------------


def test_empty_ledger_validates() -> None:
    """A27: an old record's empty ledger is a valid (empty) array."""
    Draft202012Validator(_ledger_schema()).validate([])


def test_valid_ledger_validates() -> None:
    Draft202012Validator(_ledger_schema()).validate([_valid_ledger_record()])


def test_ledger_rejects_bad_payload_ref() -> None:
    bad = _valid_ledger_record()
    bad["payload_ref"] = ".dadaia/handoff/ctx/x.handoff.json"
    with pytest.raises(ValidationError):
        Draft202012Validator(_ledger_schema()).validate([bad])


def test_ledger_rejects_bad_content_hash() -> None:
    bad = _valid_ledger_record()
    bad["content_hash"] = "not-a-hash"
    with pytest.raises(ValidationError):
        Draft202012Validator(_ledger_schema()).validate([bad])


def test_ledger_rejects_missing_consumptions_field() -> None:
    bad = _valid_ledger_record()
    del bad["consumptions"]
    with pytest.raises(ValidationError):
        Draft202012Validator(_ledger_schema()).validate([bad])
