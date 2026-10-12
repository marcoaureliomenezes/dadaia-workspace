"""`dadaia doctor` over an explicit ``--specs-dir`` needs no
instance around it.

CI runs the doctor over a bare checkout (``dadaia doctor --specs-dir specs``): there
is no ``.dadaia/states/`` above the runner's cwd. The `specs` and `ledgers` sections
read the tree they were pointed at; the `workspace` section, with no instance to
walk, is empty (0/0) — never a refusal. With NOTHING to read (no instance, no
explicit tree) the run still refuses with the one initialization message.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture
def no_instance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    return tmp_path


def test_nothing_to_read_refuses_with_one_fix(no_instance: Path) -> None:
    run = _runner.invoke(app, ["doctor"])

    assert run.exit_code == 1
    assert run.output.count("\nfix: ") == 1


def test_two_trees_is_a_usage_error_before_any_resolution(no_instance: Path) -> None:
    run = _runner.invoke(app, ["doctor", "--context", "ctx", "--specs-dir", str(no_instance)])

    assert run.exit_code == 2, run.output
    # Rich box-wraps the usage error at the runner's width and may split a token across
    # lines: strip ANSI codes and box glyphs before asserting the tokens are named.
    clean = re.sub(r"\x1b\[[0-9;]*m", "", run.output)
    clean = re.sub(r"[\u2500-\u257f\n ]", "", clean)
    assert "--context" in clean and "--specs-dir" in clean, run.output
