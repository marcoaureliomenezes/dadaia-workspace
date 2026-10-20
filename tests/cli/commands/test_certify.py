"""The consumer recipe cites
only commands, flags and certify checks the wheel has (certify's own invocations run for
real in tests/features/certification/test_service.py).

size: SMALL (the skill scripts' ``--help`` runs as a subprocess).
"""

from __future__ import annotations

import ast
import itertools
import re
import sys
from pathlib import Path
from typing import Any

import pytest
import typer.main

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.certification import service
from dadaia_workspace.infrastructure.json_context_store import SCHEMA_VERSION
from tests.helpers.oslib import read_text, run

_SOURCE = Path(service.__file__)
_PUBLIC = _SOURCE.parents[2] / "public"
_RECIPE = read_text(_SOURCE.parents[3] / "scripts" / "CONSUMER_VALIDATION_RECIPE.md")
_SPANS = [
    re.sub(r"<[^>]*>", "X", part).split()
    for span in re.findall(r"`([^`]+)`", _RECIPE)
    for part in re.split(r"\s*&&\s*", span)
]


def _resolve(words: list[str]) -> tuple[str, Any]:
    """Walk the real command tree along *words* (by ``get_command``: Typer vendors Click)."""
    command: Any = typer.main.get_command(app)
    path = ["dadaia"]
    for word in words:
        child = getattr(command, "get_command", lambda *_: None)(None, word)
        if child is None:
            break
        command, path = child, [*path, word]
    return " ".join(path), command


@pytest.mark.parametrize("words", [w for w in _SPANS if w[0] == "$D"], ids=" ".join)
def test_every_recipe_command_parses_against_the_wheel(words: list[str]) -> None:
    """Every '$D …' command the recipe
    prints names a real subcommand and only its real flags."""
    name, command = _resolve(words[1:])
    rest = words[len(name.split()) :]
    group = getattr(command, "get_command", None) is not None
    assert not group or not rest or rest[0].startswith("-"), f"`{name}` has no {rest[:1]}"
    declared = {opt for param in command.params for opt in param.opts} | {"--help"}
    assert [f for f in rest if f.startswith("--") and f not in declared] == []


@pytest.mark.parametrize(
    "words", [w for w in _SPANS if w[0] == "python3" and "/scripts/" in w[1]], ids=" ".join
)
def test_every_recipe_script_flag_exists(words: list[str]) -> None:
    """Every 'python3 …scripts/*.py …'
    line's subcommand and flags are in that script's own `--help`."""
    script = _PUBLIC / "skills" / words[1].removeprefix("$S/")
    verb = list(itertools.takewhile(lambda w: w[0] != "-", words[2:]))
    shown = run([sys.executable, str(script), *verb, "--help"], timeout=20)
    assert shown.returncode == 0, shown.stderr
    assert [f for f in words[2:] if f.startswith("--") and f not in shown.stdout] == []


def test_every_recipe_certify_check_is_one_certify_runs() -> None:
    """Every certify check the recipe
    names (e.g. 'context-bind') is in certify's emitted check list."""
    checks = {
        node.args[0].value
        for node in ast.walk(ast.parse(read_text(_SOURCE)))
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "check"
        if isinstance(node.args[0], ast.Constant)
    }
    f03 = re.search(r"^- F-03 .*$", _RECIPE, re.M)
    named = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", f03.group(0) if f03 else ""))
    assert "context-bind" in named
    assert sorted(named - checks) == []


def test_the_recipe_expects_the_stamp_the_store_owns() -> None:
    assert f"schema_version {SCHEMA_VERSION} after migrate" in _RECIPE
