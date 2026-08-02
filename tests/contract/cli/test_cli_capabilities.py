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
        / "dadaia-capabilities-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_capabilities_pin_exact_sdd_commands_and_context_safety() -> None:
    """Pins the SDD lifecycle verbs a consumer is told to use.

    This used to pin the four `dadaia lifecycle …` workflow commands. It kept passing
    after the engine was demolished — it only ever compared the document against
    itself, never against the CLI — which is why the sibling test above now checks
    every advertised command is really registered.
    """
    payload = build_capabilities()
    assert {item["command"] for item in payload["sdd_lifecycle"]} == {
        "dadaia backlog new",
        "dadaia specs release open",
        "dadaia specs segment open",
        "dadaia backlog consume",
        "dadaia backlog remove-consumed",
        "dadaia specs doctor",
    }
    assert payload["contexts"]["selection_contract"] == "explicit-or-caller-owned-bind"
    assert payload["consumer_requirements"]["exact_provider_version"] is True


def test_every_advertised_command_is_actually_registered() -> None:
    """The capability document is authoritative over remembered syntax — so it may
    not advertise a command that does not exist.

    It kept listing four `dadaia lifecycle …` verbs after the engine was demolished.
    An agent that follows our own instruction ("start every runtime with
    `dadaia capabilities --json`; this versioned document is authoritative") received
    four dead commands. Reported by the consumer-side validator as CRITICAL
    (`capabilities-advertises-unregistered-lifecycle-command-group`).
    """
    import json as _json

    from typer.testing import CliRunner

    from dadaia_workspace.cli.main import app

    runner = CliRunner()
    payload = _json.loads(runner.invoke(app, ["capabilities", "--json"]).output)

    advertised: set[str] = set()

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "command" and isinstance(value, str):
                    advertised.add(value)
                else:
                    _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    assert advertised, "the document advertises no command at all — check the walker"

    # Enumerate from the Typer app itself — parsing `--help` depends on rich's box
    # drawing and silently yields an empty set, which would make this test vacuous.
    registered = {group.name for group in app.registered_groups} | {
        command.name or (command.callback.__name__ if command.callback else "")
        for command in app.registered_commands
    }
    for command in sorted(advertised):
        group = command.split()[1]
        assert group in registered, (
            f"capabilities advertises `{command}`, but `{group}` is not a command group. "
            f"Registered: {sorted(registered)}"
        )
