"""A DadaiaError carries its fix; ``fail`` prints a caller fix only when the error has none."""

from __future__ import annotations

import pytest
import typer

from dadaia_workspace.cli._fail import fail
from dadaia_workspace.core.exceptions import DadaiaError, SchemaVersionError


def test_error_with_fix_carries_it_in_text():
    error = DadaiaError("m", fix="f")
    assert error.fix == "f"
    assert str(error) == "m\nfix: f"


def test_error_without_fix_is_the_bare_message():
    error = DadaiaError("m")
    assert error.fix == ""
    assert str(error) == "m"


def test_schema_version_error_keeps_problem_fix_and_text():
    error = SchemaVersionError("p", "migrate --yes")
    assert (error.message, error.fix) == ("p", "migrate --yes")
    assert str(error) == "p\nfix: migrate --yes"


def test_fail_prints_the_caller_fix_when_the_error_has_none(capsys):
    with pytest.raises(typer.Exit) as exc:
        fail(DadaiaError("m"), "x")
    assert exc.value.exit_code == 1
    assert capsys.readouterr().err == "Error: m\nfix: x\n"


def test_fail_prints_the_errors_own_fix_once_and_ignores_the_caller_fix(capsys):
    with pytest.raises(typer.Exit) as exc:
        fail(DadaiaError("m", fix="f"), "x")
    assert exc.value.exit_code == 1
    assert capsys.readouterr().err == "Error: m\nfix: f\n"
