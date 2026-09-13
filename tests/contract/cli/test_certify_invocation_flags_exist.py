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
import itertools
from pathlib import Path
from typing import Any

import pytest
import typer.main

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.certification import service

_SOURCE = Path(service.__file__)


#: What a non-literal argument (``str(path)``, an f-string) is called in the parsed
#: invocation: its VALUE is unknown here, its POSITION is not.
_COMPUTED = "<computed>"


def _invocations() -> list[tuple[str, ...]]:
    """Every ``cli(...)`` call as its argument words, in order.

    A non-literal argument becomes :data:`_COMPUTED`: the flag check ignores it, the
    arity check counts it — a positional the service passes is a positional whether or
    not the test can read its value.
    """
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    found: list[tuple[str, ...]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "cli":
            continue
        if any(isinstance(a, ast.Starred) for a in node.args):
            continue  # `cli(*args)` — a forwarding wrapper, not an invocation
        words = tuple(
            a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else _COMPUTED
            for a in node.args
        )
        if words:
            found.append(words)
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
_IDS = [" ".join(w) for w in _INVOCATIONS]


@pytest.mark.parametrize("words", _INVOCATIONS, ids=_IDS)
def test_certify_invocation_flags_exist_on_the_real_cli(words: tuple[str, ...]) -> None:
    name, command = _resolve(words)
    declared = {opt for param in command.params for opt in param.opts}
    for flag in (w for w in words if w.startswith("--")):
        assert flag in declared, f"`{name}` has no option {flag} — certify would exit 2"


def _arity(command: Any) -> tuple[int, int | None]:
    """(minimum, maximum) positional count the resolved command accepts; ``None`` = a
    variadic argument, so there is no maximum."""
    minimum = 0
    maximum: int | None = 0
    for param in command.params:
        if param.param_type_name != "argument":
            continue
        if param.nargs == -1:
            maximum = None
            continue
        if param.required:
            minimum += param.nargs
        if maximum is not None:
            maximum += param.nargs
    return minimum, maximum


@pytest.mark.parametrize("words", _INVOCATIONS, ids=_IDS)
def test_certify_invocation_positional_arity_matches_the_real_cli(words: tuple[str, ...]) -> None:
    """A verb that gains or loses a positional breaks certify at the subprocess too —
    the flag check alone left ``cli("context", "bind", "certified-consumer")`` asserting
    nothing at all (0.4.7 c2 review)."""
    name, command = _resolve(words)
    consumed = len(name.split()) - 1  # "dadaia" is not one of the invocation's words
    tail = words[consumed:]
    positionals = list(itertools.takewhile(lambda w: not w.startswith("-"), tail))
    minimum, maximum = _arity(command)
    assert minimum <= len(positionals), (
        f"`{name}` takes at least {minimum} positional(s); certify passes {positionals}"
    )
    assert maximum is None or len(positionals) <= maximum, (
        f"`{name}` takes at most {maximum} positional(s); certify passes {positionals}"
    )
