"""AC-3 (v0.1.58 FR2) — ``dadaia init --harness <set>`` scaffolds ONLY the chosen harnesses.

RED-first: before FR2 ``dadaia init`` had no ``--harness`` flag and ALWAYS produced the
all-four scaffold (``.claude`` + ``.codex`` + ``.pi``). This suite pins the harness-aware
behaviour — each L1 harness gets its projection ONLY when named in the set, the default
(omitted) stays all-four (back-compat), and a bad value is a width-independent Click
``BadParameter`` (exit 2, message on stderr, empty stdout). The AC-9(b) mutation-sanity
sabotage (init ignores the harness set ⇒ always all-four) makes the claude-only case below
FAIL — that is the discriminating proof the scaffold is genuinely harness-gated.

QA-atom law (v0.1.57): ``CliRunner`` is built with NO ``mix_stderr`` kwarg (removed in
Click 8.2; TypeErrors on the installed 8.4.1); ``result.stderr``/``result.stdout`` are read
as separate channels; the error assert is width-independent (strip ANSI + Rich box glyphs,
collapse whitespace).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.helpers.golden_platform import norm_stderr

# NEVER pass mix_stderr (removed in Click 8.2; the installed 8.4.1 TypeErrors on it).
_runner = CliRunner()


def _ctx_inject_commands(claude_dir: Path) -> list[str]:
    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    entries = settings["hooks"]["UserPromptSubmit"]
    return [h["command"] for entry in entries for h in entry.get("hooks", [])]


@pytest.mark.parametrize(
    ("name", "harness_set", "expect_present", "expect_absent"),
    [
        # AC-9(b) sabotage detector: --harness claude → .claude/ + ctx-inject hook, and
        # NO .codex/ / .pi/.
        ("claude_only", "claude", ("claude",), ("codex", "pi")),
        # --harness codex,pi → .codex/ (+ .dadaia/hooks/codex-*) + .pi/, NO .claude/
        # agents.
        ("codex_and_pi", "codex,pi", ("codex", "pi"), ("claude",)),
    ],
)
def test_harness_scopes_scaffold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    harness_set: str,
    expect_present: tuple[str, ...],
    expect_absent: tuple[str, ...],
) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["init", "--workspace", str(tmp_path), "--harness", harness_set])
    assert result.exit_code == 0, result.output

    for harness in expect_present:
        assert (tmp_path / f".{harness}").is_dir()
    for harness in expect_absent:
        assert not (tmp_path / f".{harness}").exists()

    if "claude" in expect_present:
        commands = _ctx_inject_commands(tmp_path / ".claude")
        assert any("dadaia_workspace.hooks.ctx_inject" in c for c in commands), commands
    if "codex" in expect_present:
        codex_wrappers = sorted((tmp_path / ".dadaia" / "hooks").glob("codex-*"))
        assert codex_wrappers, "expected .dadaia/hooks/codex-* wrappers for a codex profile"


def test_harness_omitted_scaffolds_all_four(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--harness`` omitted → all-four scaffold (back-compat with pre-v0.1.58 init)."""
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["init", "--workspace", str(tmp_path)])
    assert result.exit_code == 0, result.output

    assert (tmp_path / ".claude").is_dir()
    assert (tmp_path / ".codex").is_dir()
    assert (tmp_path / ".pi").is_dir()


def test_harness_bad_value_is_bad_parameter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--harness zzz`` → exit 2, width-independent stderr naming the bad value, empty stdout."""
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["init", "--workspace", str(tmp_path), "--harness", "zzz"])
    assert result.exit_code == 2
    norm = norm_stderr(result.stderr)
    assert "zzz" in norm, norm
    assert "harness" in norm, norm
    # The UsageError is on stderr — no partial payload leaks to stdout.
    assert result.stdout == ""
