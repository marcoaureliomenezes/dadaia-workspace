"""Intent: CONTRACT — 0.4.7 FR4/T-047-16: certify only shells flags the real CLI has.

``dadaia certify`` is the release blocker: every check shells the installed CLI in a
disposable workspace. A flag deleted from a verb but left behind in a certification
check makes certify fail at the subprocess, far from the deletion. This test parses
every ``cli(...)`` invocation in the certification service and asserts each ``--flag``
it passes is a declared parameter of that verb's real Click command.

size: SMALL.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
import typer.main

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.certification import service

_SOURCE = Path(service.__file__)


def _invocations() -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Every ``cli(...)`` call as ``(words, flags)`` — literal arguments only."""
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    found: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "cli":
            continue
        words = tuple(
            a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)
        )
        flags = tuple(w for w in words if w.startswith("--"))
        if flags:
            found.append((words, flags))
    return found


def _resolve(words: tuple[str, ...]) -> tuple[str, Any]:
    """Walk the real command tree along *words*, stopping at the leaf command.

    Typer vendors its own Click (``typer._click``), so the tree is walked by the
    ``get_command`` capability rather than by ``isinstance(..., click.Group)``.
    """
    command: Any = typer.main.get_command(app)
    path = ["dadaia"]
    for word in words:
        get_command = getattr(command, "get_command", None)
        if word.startswith("-") or get_command is None:
            break
        child = get_command(None, word)
        if child is None:
            break
        command, path = child, [*path, word]
    return " ".join(path), command


_INVOCATIONS = _invocations()


@pytest.mark.parametrize(
    ("words", "flags"),
    _INVOCATIONS,
    ids=[" ".join(w) for w, _ in _INVOCATIONS],
)
def test_certify_invocation_flags_exist_on_the_real_cli(
    words: tuple[str, ...], flags: tuple[str, ...]
) -> None:
    name, command = _resolve(words)
    declared = {opt for param in command.params for opt in param.opts}
    for flag in flags:
        assert flag in declared, f"`{name}` has no option {flag} — certify would exit 2"
