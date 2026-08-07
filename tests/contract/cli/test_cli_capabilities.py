"""Public machine-readable capability contract."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.capabilities import build_capabilities


def test_capabilities_json_matches_service_and_public_schema() -> None:
    result = CliRunner().invoke(app, ["capabilities", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload == build_capabilities()

    schema_path = (
        Path(__file__).parents[3]
        / "dadaia_workspace"
        / "public"
        / "schemas"
        / "dadaia-capabilities-v2.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_capabilities_pin_context_safety() -> None:
    payload = build_capabilities()
    assert "workflows" not in payload
    assert payload["contexts"]["selection_contract"] == "explicit-or-caller-owned-bind"
    assert payload["consumer_requirements"]["exact_provider_version"] is True
