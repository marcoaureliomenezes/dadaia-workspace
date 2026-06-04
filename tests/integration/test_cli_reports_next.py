"""Integration tests for `dadaia reports next` CLI (T-RN-03 / AC-RN-1, AC-RN-2).

Uses --context to point at a synthetic context under repos/<ctx>/specs, avoiding
primary-context setup. Verifies exit codes and --json parseability.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_CTX = "demo"
_RELEASE = "rel-x"


def _init_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(workspace)


def _seed_context(
    workspace: Path,
    *,
    active: str = f"release: {_RELEASE}\nphase: TASKS\n",
    plan: str = "**Owner:** qa-engineer\n**Owner:** devops-engineer\n",
    handoffs: dict[str, str] | None = None,
) -> None:
    releases = workspace / "repos" / _CTX / "specs" / "releases"
    (releases / _RELEASE).mkdir(parents=True)
    (releases / "ACTIVE.md").write_text(active, encoding="utf-8")
    (releases / _RELEASE / "PLAN.md").write_text(plan, encoding="utf-8")
    for agent, rel in (handoffs or {}).items():
        handoff_dir = workspace / ".dadaia" / "handoff" / _CTX
        handoff_dir.mkdir(parents=True, exist_ok=True)
        (handoff_dir / f"2026-06-04T000000Z-{agent}-h.handoff.json").write_text(
            json.dumps({"release_id": rel, "agent": agent}), encoding="utf-8"
        )


def test_next_json_is_parseable(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    _seed_context(tmp_path, handoffs={"qa-engineer": _RELEASE})
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["reports", "next", "--context", _CTX, "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["next_agent"] == "devops-engineer"
    assert payload["release_id"] == _RELEASE
    assert payload["completed_agents"] == ["qa-engineer"]
    assert payload["pending_agents"] == ["devops-engineer"]


def test_next_text_output(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    _seed_context(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["reports", "next", "--context", _CTX])
    assert result.exit_code == 0, result.output
    assert "Next expected agent: qa-engineer" in result.output


def test_next_all_completed(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    _seed_context(tmp_path, handoffs={"qa-engineer": _RELEASE, "devops-engineer": _RELEASE})
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["reports", "next", "--context", _CTX, "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["next_agent"] is None
    assert payload["pending_agents"] == []


def test_next_no_active_release_exits_3(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    _seed_context(tmp_path, active="release: none\nphase: DISCOVERY\n")
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["reports", "next", "--context", _CTX])
    assert result.exit_code == 3


def test_next_plan_without_owners_exits_3(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    _seed_context(tmp_path, plan="# PLAN\n\nNothing here.\n")
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["reports", "next", "--context", _CTX])
    assert result.exit_code == 3
