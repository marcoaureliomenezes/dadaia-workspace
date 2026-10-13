"""``dadaia init --harness <set>`` scaffolds ONLY the chosen harnesses.

Each L1 harness that OWNS a workspace directory
(``core.harness_registry.HARNESS_PROJECTION_DIRS``) gets its projection ONLY when it is
THE named harness.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

# CliRunner takes no mix_stderr kwarg.
_runner = CliRunner()


def _ctx_inject_commands(claude_dir: Path) -> list[str]:
    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    entries = settings["hooks"]["UserPromptSubmit"]
    return [h["command"] for entry in entries for h in entry.get("hooks", [])]


@pytest.mark.parametrize(
    ("name", "harness", "expect_present", "expect_absent"),
    [
        # --harness claude → .claude/ + ctx-inject hook, and NO .codex/.
        ("claude_only", "claude", ("claude",), ("codex",)),
        # --harness codex → .codex/ (+ .dadaia/hooks/codex-*), NO .claude/ agents.
        ("codex_only", "codex", ("codex",), ("claude", "kimi-code")),
        # kimi-code owns no workspace directory — it reads the shared
        # .agents/ tree natively and wires its hooks at the user level.
        # --harness kimi-code → nothing of its own; .claude/ and .codex/ stay absent.
        ("kimi_only", "kimi-code", (), ("claude", "codex", "kimi-code")),
    ],
)
def test_harness_scopes_scaffold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    harness: str,
    expect_present: tuple[str, ...],
    expect_absent: tuple[str, ...],
) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["init", str(tmp_path), "--harness", harness])
    assert result.exit_code == 0, result.output

    for harness in expect_present:
        assert (tmp_path / f".{harness}").is_dir()
    for harness in expect_absent:
        assert not (tmp_path / f".{harness}").exists()

    if "claude" in expect_present:
        commands = _ctx_inject_commands(tmp_path / ".claude")
        wrapper = tmp_path / ".dadaia" / "hooks" / "claude-ctx-inject"
        assert any(c.endswith("/.dadaia/hooks/claude-ctx-inject") for c in commands), commands
        assert "dadaia_workspace.hooks.ctx_inject" in wrapper.read_text(encoding="utf-8")
    if "codex" in expect_present:
        codex_wrappers = sorted((tmp_path / ".dadaia" / "hooks").glob("codex-*"))
        assert codex_wrappers, "expected .dadaia/hooks/codex-* wrappers for a codex profile"
