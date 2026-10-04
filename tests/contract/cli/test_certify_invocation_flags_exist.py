"""sa-reconcile-certify-skip-the-workspace-walk: the consumer recipe cites
only commands, flags and certify checks the wheel has (certify's own invocations run for
real in tests/integration/features/certification/test_certify_journey.py).

size: SMALL (the skill scripts' ``--help`` runs as a subprocess).
"""

from __future__ import annotations

import ast
import itertools
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import typer.main

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.certification import service

_SOURCE = Path(service.__file__)
_PUBLIC = _SOURCE.parents[2] / "public"
_RECIPE = (_PUBLIC / "data" / "CONSUMER_VALIDATION_RECIPE.md").read_text(encoding="utf-8")
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
    """sa-reconcile-certify-skip-the-workspace-walk#B3: every '$D …' command the recipe
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
    """sa-reconcile-certify-skip-the-workspace-walk#B3: every 'python3 …scripts/*.py …'
    line's subcommand and flags are in that script's own `--help`."""
    script = _PUBLIC / "skills" / words[1].removeprefix("$S/")
    verb = list(itertools.takewhile(lambda w: w[0] != "-", words[2:]))
    shown = subprocess.run(
        [sys.executable, str(script), *verb, "--help"], capture_output=True, text=True, timeout=20
    )
    assert shown.returncode == 0, shown.stderr
    assert [f for f in words[2:] if f.startswith("--") and f not in shown.stdout] == []


def test_every_recipe_certify_check_is_one_certify_runs() -> None:
    """sa-reconcile-certify-skip-the-workspace-walk#B4: every certify check the recipe
    names (e.g. 'context-bind') is in certify's emitted check list."""
    checks = {
        node.args[0].value
        for node in ast.walk(ast.parse(_SOURCE.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "check"
        if isinstance(node.args[0], ast.Constant)
    }
    f03 = re.search(r"^- F-03 .*$", _RECIPE, re.M)
    named = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", f03.group(0) if f03 else ""))
    assert "context-bind" in named
    assert sorted(named - checks) == []
