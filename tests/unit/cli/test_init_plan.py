"""Intent: CONTRACT — 0.4.8 FR1 AC1.1–AC1.4 (T-048-04): one ``InitPlan``, quiet output.

Flags and TTY prompts fill the SAME plan object, so both produce the same tree; the
output is at most 12 lines (asset count, absolute venv CLI path, next step); ``DIR`` and
``--harness`` are optional in ``--help``; a non-TTY missing either exits 2 with one fix.

size: SMALL. QA-atom law (v0.1.57): ``CliRunner`` is built with NO ``mix_stderr`` kwarg.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import init as init_cmd
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import cli_path

_runner = CliRunner()


def _tree(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


def _contexts(root: Path) -> object:
    return json.loads((root / ".dadaia" / "states" / "spec_contexts.json").read_text("utf-8"))


def test_prompts_and_flags_fill_the_same_plan(tmp_path: Path, monkeypatch) -> None:
    """AC1.3: name -> ./<name>, harness, blank main URL; equal trees to the flag run."""
    flags_dir, prompt_dir = tmp_path / "flags", tmp_path / "prompt"
    flags_dir.mkdir()
    prompt_dir.mkdir()
    monkeypatch.chdir(flags_dir)
    by_flags = _runner.invoke(app, ["init", "ws", "--harness", "codex"])
    assert by_flags.exit_code == 0, by_flags.output

    monkeypatch.chdir(prompt_dir)
    monkeypatch.setattr(init_cmd, "_interactive", lambda: True)
    by_prompts = _runner.invoke(app, ["init"], input="ws\ncodex\n\n")
    assert by_prompts.exit_code == 0, by_prompts.output

    assert _tree(prompt_dir / "ws") == _tree(flags_dir / "ws")
    assert _contexts(prompt_dir / "ws") == _contexts(flags_dir / "ws")


def test_output_is_at_most_twelve_lines_with_count_and_venv_path(tmp_path: Path) -> None:
    """AC1.1: one count line, never the per-asset listing; the absolute CLI path."""
    ws = tmp_path / "ws"
    result = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])

    assert result.exit_code == 0, result.output
    lines = result.stdout.splitlines()
    assert len(lines) <= 12, result.stdout
    assert f"CLI: {cli_path(ws)}" in result.stdout.splitlines()
    assert not any(line.startswith("  ") for line in lines), "no per-asset listing"


def test_help_shows_dir_and_harness_optional() -> None:
    """AC1.4: DIR is bracketed (optional) in usage."""
    result = _runner.invoke(app, ["init", "--help"])

    assert result.exit_code == 0, result.output
    assert "[DIR]" in result.stdout


@pytest.mark.parametrize("argv", [["init", "--harness", "claude"], ["init", "demo"]])
def test_non_tty_missing_field_exits_2_with_one_fix(
    argv: list[str], tmp_path: Path, monkeypatch
) -> None:
    """AC1.2: no prompt off a TTY — exit 2 with the uvx fix; nothing scaffolded."""
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, argv)

    assert result.exit_code == 2, result.output
    fixes = [ln for ln in result.output.splitlines() if ln.startswith("fix: ")]
    assert len(fixes) == 1, result.output
    assert fixes[0].startswith("fix: uvx dadaia-workspace init "), fixes
    assert "--harness" in fixes[0]
    assert not list(tmp_path.iterdir())


def test_non_tty_fix_line_repeats_the_repo_flags(tmp_path: Path, monkeypatch) -> None:
    """Bug init-missing-harness-fix-line-drops-repo-flags: running the fix as printed
    keeps level 2 — every --repo/--associated-repo the invocation carried."""
    monkeypatch.chdir(tmp_path)
    argv = ["init", "myws", "--repo", "https://h/m.git", "--associated-repo", "https://h/a.git"]
    argv += ["--associated-repo", "https://h/b.git"]

    result = _runner.invoke(app, argv)

    assert result.exit_code == 2, result.output
    [fix] = [ln for ln in result.output.splitlines() if ln.startswith("fix: ")]
    assert fix == (
        "fix: uvx dadaia-workspace init myws --harness claude --repo https://h/m.git "
        "--associated-repo https://h/a.git --associated-repo https://h/b.git"
    )
