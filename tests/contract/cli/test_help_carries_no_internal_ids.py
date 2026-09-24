"""Intent: CONTRACT — cli-help-leaks-internal-spec-ids.

Every command's rendered `--help` states behaviour in the reader's words: no internal
requirement, task or audit id, no code seam name. Size: SMALL (in-process CliRunner).
"""

from __future__ import annotations

import re

from typer.main import get_command
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_LEAK = re.compile(
    r"\bFR\d|SPEC v\d|\bA\d+\.\d|T-\d{3}-\d|\bv\d+\.\d+\.\d+\b|container\.|cli-no-infrastructure"
)


def _paths() -> list[list[str]]:
    out: list[list[str]] = []

    def walk(cmd: object, path: list[str]) -> None:
        out.append(path)
        for name, sub in (getattr(cmd, "commands", {}) or {}).items():
            walk(sub, [*path, name])

    walk(get_command(app), [])
    return out


def test_no_command_help_leaks_an_internal_id() -> None:
    env = {"COLUMNS": "400", "NO_COLOR": "1", "TERM": "dumb"}
    runner = CliRunner()
    leaks = []
    for path in _paths():
        result = runner.invoke(app, [*path, "--help"], env=env)
        assert result.exit_code == 0, (path, result.output)
        text = " ".join(re.sub(r"[─-╿]", " ", result.output).split())
        leaks += [f"{' '.join(path) or '<root>'}: {m.group(0)!r}" for m in _LEAK.finditer(text)]
    assert leaks == [], "\n".join(leaks)


def test_push_gate_check_help_names_the_branch_model_once() -> None:
    env = {"COLUMNS": "400", "NO_COLOR": "1", "TERM": "dumb"}
    text = CliRunner().invoke(app, ["ci", "push-gate-check", "--help"], env=env).output
    assert text.count("dd-gitflow-default") <= 1


def test_reports_validate_help_shows_each_example_once() -> None:
    env = {"COLUMNS": "400", "NO_COLOR": "1", "TERM": "dumb"}
    text = CliRunner().invoke(app, ["reports", "validate", "--help"], env=env).output
    lines = [ln.strip() for ln in text.splitlines() if "--all" in ln and "validate" in ln]
    assert len(lines) == len(set(lines)), lines
