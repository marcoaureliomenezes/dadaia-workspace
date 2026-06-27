"""Schema-level tests for the v0.1.29 overlay harness fields (T-29-A-05).

The overlay schema (`public/schemas/workflow-model-policy-v1.schema.json`) gains an
optional per-workflow `default_harness` and a per-step `harnesses` object, both
constrained to the Layer-2 enum codex|pi, while keeping `additionalProperties:false`.
A v0.1.28 overlay (no harness fields) must still validate; a non-codex/pi harness must
be rejected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[4]
    / "dadaia_workspace"
    / "public"
    / "schemas"
    / "workflow-model-policy-v1.schema.json"
)


def _validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _overlay(workflow: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "workflow-model-policy-v1",
        "policy_id": "default",
        "contexts": {"default": {"workflows": {"implementation": workflow}}},
    }


def test_v0128_overlay_without_harness_validates() -> None:
    _validator().validate(_overlay({"steps": {"implement": "codex-implementation-standard"}}))


def test_default_harness_pi_validates() -> None:
    _validator().validate(_overlay({"steps": {}, "default_harness": "pi"}))


def test_per_step_harnesses_validate() -> None:
    _validator().validate(_overlay({"steps": {}, "harnesses": {"implement": "pi"}}))


def test_non_layer2_default_harness_rejected() -> None:
    with pytest.raises(ValidationError):
        _validator().validate(_overlay({"steps": {}, "default_harness": "claude"}))


def test_non_layer2_step_harness_rejected() -> None:
    with pytest.raises(ValidationError):
        _validator().validate(_overlay({"steps": {}, "harnesses": {"implement": "opencode"}}))


def test_unknown_workflow_field_rejected() -> None:
    with pytest.raises(ValidationError):
        _validator().validate(_overlay({"steps": {}, "bogus": "x"}))
