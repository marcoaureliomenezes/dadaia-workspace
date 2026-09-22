"""Intent: CONTRACT — capabilities-advertises-verbs-and-surfaces-that-do-not-exist.

Everything ``dadaia capabilities --json`` advertises exists: each verb is a path of
the live command tree and the harness list is the harness registry.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from dadaia_workspace.cli.help_digest import command_paths
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES


def _payload() -> dict[str, object]:
    result = CliRunner().invoke(app, ["capabilities", "--json"])
    assert result.exit_code == 0, result.output
    payload: dict[str, object] = json.loads(result.stdout)
    return payload


def test_every_advertised_verb_exists_in_the_live_tree() -> None:
    payload = _payload()
    live = command_paths()
    contexts = payload["contexts"]
    assert isinstance(contexts, dict)
    assert "modes" not in contexts
    assert {("context", verb) for verb in contexts["commands"]} <= live
    assert "heartbeat" not in contexts["commands"]
    surfaces = payload["surfaces"]
    assert isinstance(surfaces, dict)
    for group, verbs in surfaces.items():
        assert {(group, verb) for verb in verbs} <= live, group
    assert "panel" not in surfaces


def test_advertised_harnesses_are_the_registry() -> None:
    harnesses = _payload()["harnesses"]
    assert isinstance(harnesses, dict)
    assert harnesses["layer_1"] == list(L1_ENTRY_HARNESSES)
