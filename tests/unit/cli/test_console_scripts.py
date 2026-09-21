"""Two console-script names, one callable.

Intent: CONTRACT — T-047-85 (SPEC 0.4.7 FR3, AC3.1): `[tool.poetry.scripts]` declares
both `dadaia` and `dadaia-workspace`, and both targets import to the SAME callable
object — so `uvx dadaia-workspace init <dir> --harness <name> --repo <url>` resolves
against the distribution name a reader already knows, without a second CLI existing.
Size: SMALL — `tomllib` over this repo's `pyproject.toml` plus one `importlib` lookup;
no build, no subprocess, no network.

The seam is the entry-point table: poetry-core compiles it into the wheel's
`entry_points.txt` verbatim, so the table IS the shipped contract and reading it here
needs no build. Identity, not string equality: two names that happened to spell
different callables would be the second CLI ADR 0018 forbids.
"""

from __future__ import annotations

import tomllib
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
#: The distribution name and the short verb — the only two names PyPI installs.
_EXPECTED_NAMES = ("dadaia", "dadaia-workspace")
_TARGET = "dadaia_workspace.cli.main:_safe_app"


def _scripts() -> dict[str, str]:
    with (_REPO_ROOT / "pyproject.toml").open("rb") as handle:
        table = tomllib.load(handle)["tool"]["poetry"]["scripts"]
    assert isinstance(table, dict)
    return {str(name): str(target) for name, target in table.items()}


def _resolve(target: str) -> Any:
    """`module:attr` resolved the way a generated console script resolves it."""
    module_name, _, attr = target.partition(":")
    return getattr(import_module(module_name), attr)


def test_both_console_script_names_are_declared() -> None:
    """`uvx dadaia-workspace …` needs the distribution name in the table; `dadaia` is
    what the installed workspace invokes. Neither name may be dropped for the other."""
    assert sorted(_scripts()) == sorted(_EXPECTED_NAMES)


def test_every_declared_name_resolves_to_the_one_callable() -> None:
    """One CLI, two names (ADR 0018): the resolved objects are identical, so there is no
    second entry module to drift — a new name is a table line, never a new module."""
    resolved = {name: _resolve(target) for name, target in _scripts().items()}
    expected = _resolve(_TARGET)

    assert all(callable(obj) for obj in resolved.values())
    assert set(map(id, resolved.values())) == {id(expected)}
