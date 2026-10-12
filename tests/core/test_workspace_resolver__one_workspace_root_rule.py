"""One workspace-root rule: the CLI's own venv workspace, else the nearest sentinel ancestor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.specs.memory_lint import main as memory_lint
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess


def _workspace(root: Path, registry: object = None) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    body = registry if registry is not None else {"schema_version": "2", "contexts": []}
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text(json.dumps(body))
    return root


@pytest.mark.medium
def test_workspace_root_in_the_hook_env_never_opens_a_protected_write(tmp_path: Path) -> None:
    """A WORKSPACE_ROOT elsewhere in the hook env changes nothing: the gate still BLOCKs."""
    ws = _workspace(tmp_path / "ws")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    env = {**claude_hook_env(ws), "WORKSPACE_ROOT": str(elsewhere)}
    target = ws / ".dadaia" / "sessions" / "x.json"
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "s"}
    result = run_hook_subprocess("sdd_gate", payload, env, cwd=elsewhere)
    block = result.block_envelope()
    assert block is not None and "SEC-01" in block["reason"], result.stdout + result.stderr


def test_migrate_runs_in_the_cli_own_workspace_from_any_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A v1 registry is migrated from any cwd, never "nothing to do"."""
    v1 = {"contexts": [{"name": "c", "state": "ativo", "repo_slug": "c"}]}
    own = _workspace(tmp_path / "ws", v1)
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(sys, "prefix", str(own / ".dadaia" / ".venv"))
    monkeypatch.chdir(outside)

    result = CliRunner().invoke(app, ["migrate", "--yes"])

    assert result.exit_code == 0, result.output
    registry = json.loads((own / ".dadaia" / "states" / "spec_contexts.json").read_text())
    assert registry["schema_version"] == "2"


def test_context_show_reads_name_registry_and_session_from_one_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """From another workspace, `context show` reads the CLI's own."""
    row = {"name": "zz-own", "state": "alive", "repo_slug": "zz-own", "repo_url": "u",
           "created_at": "2026-01-01T00:00:00Z", "current_branch": "main"}  # fmt: skip
    own = _workspace(tmp_path / "own", {"schema_version": "2", "contexts": [row]})
    other = _workspace(tmp_path / "other")
    monkeypatch.setattr(sys, "prefix", str(own / ".dadaia" / ".venv"))
    monkeypatch.chdir(other)
    monkeypatch.setenv("DADAIA_CONTEXT", "zz-own")

    result = CliRunner().invoke(app, ["context", "show", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["name"] == "zz-own"


def test_memory_lint_has_no_cwd_default() -> None:
    """Without --memory-dir it refuses."""
    with pytest.raises(SystemExit) as refused:
        memory_lint([])
    assert refused.value.code == 2
