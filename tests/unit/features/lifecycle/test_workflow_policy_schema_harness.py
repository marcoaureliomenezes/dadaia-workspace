"""Schema-level tests for the v0.1.29 overlay harness fields (T-29-A-05).

The overlay schema (`public/schemas/workflow-model-policy-v1.schema.json`) gains an
optional per-workflow `default_harness` and a per-step `harnesses` object, both
constrained to the Layer-2 enum codex|pi, while keeping `additionalProperties:false`.
A v0.1.28 overlay (no harness fields) must still validate; a non-codex/pi harness must
be rejected.

Layer-2 residue enforcement, schema layer.
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


# --- ① validates param: v0.1.28 shape / default_harness pi / per-step harnesses --------


@pytest.mark.parametrize(
    "workflow",
    [
        {"steps": {"implement": "codex-implementation-standard"}},
        {"steps": {}, "default_harness": "pi"},
        {"steps": {}, "harnesses": {"implement": "pi"}},
    ],
    ids=["v0128-shape-no-harness", "default-harness-pi", "per-step-harnesses"],
)
def test_validates_matrix(workflow: dict[str, object]) -> None:
    _validator().validate(_overlay(workflow))


# --- ② rejects param: claude default / opencode step / unknown field -------------------


@pytest.mark.parametrize(
    "workflow",
    [
        {"steps": {}, "default_harness": "claude"},
        {"steps": {}, "harnesses": {"implement": "opencode"}},
        {"steps": {}, "bogus": "x"},
    ],
    ids=["non-layer2-default-harness", "non-layer2-step-harness", "unknown-workflow-field"],
)
def test_rejects_matrix(workflow: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _validator().validate(_overlay(workflow))
