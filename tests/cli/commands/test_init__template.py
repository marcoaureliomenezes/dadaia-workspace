"""``init DIR --template <id>`` saves the template on a new workspace and on a re-run
(the upgrade) and re-projects; no flag keeps the saved one; ``reconcile`` keeps it and takes no
flag. Ids come from ``TEMPLATES``, never literals.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.core.platform import PLATFORM

pytestmark = [pytest.mark.medium, pytest.mark.slow(reason="runs the init and reconcile seams")]


def _overlay(ws: Path) -> Path:
    return ws / ".dadaia" / "states" / "agent_model_policy.json"


def _applied(ws: Path) -> str:
    return json.loads(_overlay(ws).read_text(encoding="utf-8"))["applied_template"]


def _others() -> tuple[str, str, str]:
    """Two template ids and a core agent whose cell differs between them, so a re-projection shows."""
    from dadaia_workspace.core.model_registry import CORE_AGENTS, TEMPLATES

    a = next(iter(TEMPLATES))
    for b in TEMPLATES:
        for agent in CORE_AGENTS:
            if TEMPLATES[b][agent] != TEMPLATES[a][agent]:
                return a, b, agent
    raise AssertionError("no two templates differ")


def _persona(ws: Path, agent: str) -> str:
    return (ws / ".claude" / "agents" / f"{agent}.md").read_text(encoding="utf-8")


def _init(ws: Path, *flags: str) -> None:
    from dadaia_workspace.cli.main import app

    result = CliRunner().invoke(app, ["init", str(ws), "--harness", "claude", *flags])
    assert result.exit_code == 0, result.output


def test_new_workspace_saves_the_template_and_projects_it(tmp_path: Path) -> None:
    a, b, agent = _others()
    _init(tmp_path / "plain", "--template", a)
    _init(tmp_path / "ws", "--template", b)

    assert _applied(tmp_path / "ws") == b
    assert _persona(tmp_path / "ws", agent) != _persona(tmp_path / "plain", agent)


def test_rerun_with_the_flag_switches_the_template_and_reprojects(tmp_path: Path) -> None:
    a, b, agent = _others()
    ws = tmp_path / "ws"
    _init(ws, "--template", a)
    before = _persona(ws, agent)

    _init(ws, "--template", b)

    assert _applied(ws) == b
    assert _persona(ws, agent) != before


def test_rerun_without_the_flag_keeps_the_saved_template(tmp_path: Path) -> None:
    _, b, agent = _others()
    ws = tmp_path / "ws"
    _init(ws, "--template", b)
    saved = _persona(ws, agent)

    _init(ws)

    assert _applied(ws) == b
    assert _persona(ws, agent) == saved


def test_reconcile_keeps_the_saved_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace.cli.main import app
    from dadaia_workspace.features.capabilities import distribution_version

    _, b, agent = _others()
    ws = tmp_path / "ws"
    _init(ws, "--template", b)
    saved = _persona(ws, agent)
    venv_bin = ws / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True, exist_ok=True)
    launcher = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    launcher.write_text("", encoding="utf-8")
    launcher.chmod(0o755)
    monkeypatch.chdir(ws)

    result = CliRunner().invoke(
        app, ["reconcile", "--expect-version", distribution_version(), "--json"], terminal_width=200
    )

    assert result.exit_code == 0, result.output
    assert _applied(ws) == b
    assert _persona(ws, agent) == saved
