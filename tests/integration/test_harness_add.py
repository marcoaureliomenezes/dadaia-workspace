"""`dadaia harness add` — the verb that replaced `public install --target`.

Intent: CONTRACT — 0.4.7 AC2.1 (T-047-72); size: MEDIUM (integration).

A Claude-only workspace is scaffolded through the real `dadaia init` CLI (the
conftest autouse fixture fakes venv creation, so no real venv is built), then
`harness add codex` must project the `.codex/` set, register `codex` in
`.dadaia/states/harness_profile.json`, keep `public doctor` at exit 0, and be a
no-op on re-add.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app as cli_app

_runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _profile(workspace: Path) -> list[str]:
    data = json.loads(
        (workspace / ".dadaia" / "states" / "harness_profile.json").read_text(encoding="utf-8")
    )
    harnesses = data["harnesses"]
    assert isinstance(harnesses, list)
    return [str(h) for h in harnesses]


def _claude_only_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "ws"
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(cli_app, ["init", str(ws), "--harness", "claude"])
    assert result.exit_code == 0, result.output
    assert not (ws / ".codex").exists(), "fixture must start Claude-only"
    monkeypatch.chdir(ws)
    return ws


def test_harness_add_projects_the_set_registers_it_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2.1 third clause: `harness add codex` on a Claude-only workspace yields the
    `.codex/` set, `harness list` shows both, `public doctor` exits 0, and a second
    `add` changes nothing."""
    ws = _claude_only_workspace(tmp_path, monkeypatch)

    added = _runner.invoke(cli_app, ["harness", "add", "codex"])
    assert added.exit_code == 0, added.output

    assert (ws / ".codex" / "agents").is_dir(), ".codex/agents/ not projected by harness add"
    assert (ws / ".codex" / "hooks.json").is_file(), ".codex/hooks.json not projected"
    assert (ws / ".codex" / "config.toml").is_file(), ".codex/config.toml not projected"
    assert (ws / ".claude").is_dir(), "the pre-existing claude projection was destroyed"
    assert _profile(ws) == ["claude", "codex"]

    listed = _runner.invoke(cli_app, ["harness", "list"])
    assert listed.exit_code == 0, listed.output
    assert json.loads(_runner.invoke(cli_app, ["harness", "list", "--json"]).stdout) == {
        "harnesses": ["claude", "codex"]
    }

    doctor = _runner.invoke(cli_app, ["public", "doctor"])
    assert doctor.exit_code == 0, doctor.output

    profile_bytes = (ws / ".dadaia" / "states" / "harness_profile.json").read_bytes()
    again = _runner.invoke(cli_app, ["harness", "add", "codex"])
    assert again.exit_code == 0, again.output
    assert (ws / ".dadaia" / "states" / "harness_profile.json").read_bytes() == profile_bytes
    assert _profile(ws) == ["claude", "codex"]


def test_harness_add_refuses_an_unregistered_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unknown harness exits 2 naming the registered records; nothing is written."""
    ws = _claude_only_workspace(tmp_path, monkeypatch)

    result = _runner.invoke(cli_app, ["harness", "add", "emacs"])
    assert result.exit_code == 2, result.output
    assert _profile(ws) == ["claude"]


def test_public_install_help_carries_no_target_flag() -> None:
    """AC2.1 second clause: `public install --target` is gone from `--help`."""
    result = _runner.invoke(cli_app, ["public", "install", "--help"])
    assert result.exit_code == 0, result.output
    assert "--target" not in _ANSI.sub("", result.stdout)
