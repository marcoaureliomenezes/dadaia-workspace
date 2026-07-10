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


def test_next_json_text_all_completed_no_active_release_and_plan_without_owners(
    tmp_path: Path, monkeypatch
) -> None:
    """--json is parseable with the correct next/pending agents; the text form prints
    the same next agent; once every agent has a handoff, next_agent is None. Plus the
    exit-3 error paths: no active release, and a PLAN with no declared owners."""
    json_ws = tmp_path / "json-case"
    _init_workspace(json_ws)
    _seed_context(json_ws, handoffs={"qa-engineer": _RELEASE})
    monkeypatch.chdir(json_ws)
    json_result = _runner.invoke(app, ["reports", "next", "--context", _CTX, "--json"])
    assert json_result.exit_code == 0, json_result.output
    payload = json.loads(json_result.output)
    assert payload["next_agent"] == "devops-engineer"
    assert payload["release_id"] == _RELEASE
    assert payload["completed_agents"] == ["qa-engineer"]
    assert payload["pending_agents"] == ["devops-engineer"]

    text_ws = tmp_path / "text-case"
    _init_workspace(text_ws)
    _seed_context(text_ws)
    monkeypatch.chdir(text_ws)
    text_result = _runner.invoke(app, ["reports", "next", "--context", _CTX])
    assert text_result.exit_code == 0, text_result.output
    assert "Next expected agent: qa-engineer" in text_result.output

    completed_ws = tmp_path / "completed-case"
    _init_workspace(completed_ws)
    _seed_context(completed_ws, handoffs={"qa-engineer": _RELEASE, "devops-engineer": _RELEASE})
    monkeypatch.chdir(completed_ws)
    completed_result = _runner.invoke(app, ["reports", "next", "--context", _CTX, "--json"])
    assert completed_result.exit_code == 0, completed_result.output
    completed_payload = json.loads(completed_result.output)
    assert completed_payload["next_agent"] is None
    assert completed_payload["pending_agents"] == []

    # Exit-3 error paths: no active release, and a PLAN with no declared owners.
    no_release_ws = tmp_path / "no-release-case"
    _init_workspace(no_release_ws)
    _seed_context(no_release_ws, active="release: none\nphase: DISCOVERY\n")
    monkeypatch.chdir(no_release_ws)
    no_release_result = _runner.invoke(app, ["reports", "next", "--context", _CTX])
    assert no_release_result.exit_code == 3

    no_owners_ws = tmp_path / "no-owners-case"
    _init_workspace(no_owners_ws)
    _seed_context(no_owners_ws, plan="# PLAN\n\nNothing here.\n")
    monkeypatch.chdir(no_owners_ws)
    no_owners_result = _runner.invoke(app, ["reports", "next", "--context", _CTX])
    assert no_owners_result.exit_code == 3
