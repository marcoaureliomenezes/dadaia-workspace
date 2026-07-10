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


def test_schemas_well_formed_do_not_touch_generic_handoff_schema_and_valid_envelope() -> None:
    """A21/anti-slop: the new schemas are separate and well-formed; handoff-v1.1 is
    never mutated ($id separation); a valid envelope validates cleanly."""
    Draft202012Validator.check_schema(_envelope_schema())
    Draft202012Validator.check_schema(_ledger_schema())
    assert _envelope_schema()["$id"] == "workflow-step-payload-v1"
    assert _ledger_schema()["$id"] == "lifecycle-run-workflow-steps-v1"
    Draft202012Validator(_envelope_schema()).validate(_valid_envelope())


# --- envelope validation ----------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "mutate_fn"),
    [
        ("wrong_schema_version", lambda d: d.__setitem__("schema_version", "handoff-v1.1")),
        ("missing_payload", lambda d: d.__delitem__("payload")),
        ("negative_attempt", lambda d: d.__setitem__("attempt", -1)),
        ("unknown_retention_mode", lambda d: d.__setitem__("retention_mode", "keep_forever")),
        ("additional_properties", lambda d: d.__setitem__("surprise", 1)),
        ("non_z_timestamp", lambda d: d.__setitem__("produced_at", "2026-06-27 12:00:00")),
    ],
)
def test_envelope_rejection_table(name: str, mutate_fn: object) -> None:
    bad = _valid_envelope()
    mutate_fn(bad)  # type: ignore[operator]
    with pytest.raises(ValidationError):
        Draft202012Validator(_envelope_schema()).validate(bad)


# --- ledger validation ------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "mutate_fn"),
    [
        (
            "bad_payload_ref",
            lambda d: d.__setitem__("payload_ref", ".dadaia/handoff/ctx/x.handoff.json"),
        ),
        ("bad_content_hash", lambda d: d.__setitem__("content_hash", "not-a-hash")),
        ("missing_consumptions_field", lambda d: d.__delitem__("consumptions")),
    ],
)
def test_ledger_rejection_table(name: str, mutate_fn: object) -> None:
    bad = _valid_ledger_record()
    mutate_fn(bad)  # type: ignore[operator]
    with pytest.raises(ValidationError):
        Draft202012Validator(_ledger_schema()).validate([bad])

    if name == "bad_payload_ref":
        # A27: an old record's empty ledger is a valid (empty) array; a well-formed
        # record list also validates.
        Draft202012Validator(_ledger_schema()).validate([])
        Draft202012Validator(_ledger_schema()).validate([_valid_ledger_record()])
