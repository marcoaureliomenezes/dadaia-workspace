"""0.4.7 FR3c — ``dadaia init`` closes with the root-launch law and the Claude
``instructionFiles`` recommendation, exactly once each.

Intent: CONTRACT — 0.4.7 FR3c (T-047-57). Size: SMALL.

The library PRINTS the recommendation and never writes ``~/.claude/settings.json``:
user settings are the operator's file. The test also pins "once" — a note repeated per
installed asset would drown the payload it is meant to end.

QA-atom law (v0.1.57): ``CliRunner`` is built with NO ``mix_stderr`` kwarg.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()

_LAW = "Sessions launch at the workspace root."
_RECOMMENDATION = (
    "Claude Code: set `instructionFiles: claude-md-and-agents-md` in your user settings "
    "(~/.claude/settings.json) so a stray CLAUDE.md in a repo never hides the workspace "
    "AGENTS.md."
)


def test_init_prints_the_law_and_the_recommendation_exactly_once(tmp_path: Path) -> None:
    result = _runner.invoke(app, ["init", str(tmp_path / "ws"), "--harness", "claude"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.count(_LAW) == 1
    assert result.stdout.count(_RECOMMENDATION) == 1


def test_init_never_writes_the_operator_user_settings(tmp_path: Path) -> None:
    """The recommendation is advice, not an action — nothing is written outside the
    workspace root the operator named."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    workspace = tmp_path / "ws"

    result = _runner.invoke(app, ["init", str(workspace), "--harness", "claude"])

    assert result.exit_code == 0, result.stdout
    assert list((home / ".claude").iterdir()) == []


def test_init_for_another_harness_omits_the_claude_note(tmp_path: Path) -> None:
    """Bug init-claude-note-printed-for-every-harness: the Claude Code recommendation is
    advice about Claude Code's own settings — a codex workspace never prints it."""
    result = _runner.invoke(app, ["init", str(tmp_path / "ws"), "--harness", "codex"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.count(_LAW) == 1
    assert "instructionFiles" not in result.stdout
