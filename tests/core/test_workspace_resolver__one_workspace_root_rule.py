"""One workspace-root rule: the CLI's own venv workspace, else the nearest sentinel ancestor."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core import workspace_resolver
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.features.specs.memory_lint import main as memory_lint
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess
from tests.helpers.oslib import read_text, write_text

_PACKAGE = Path(__file__).resolve().parents[2] / "dadaia_workspace"


def _workspace(root: Path, registry: object = None) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    body = registry if registry is not None else {"schema_version": "2", "contexts": []}
    write_text(root / ".dadaia" / "states" / "spec_contexts.json", json.dumps(body))
    return root


def test_no_package_module_reads_workspace_root_from_the_environment() -> None:
    """No environment variable changes the root."""
    reads = [
        f"{path.relative_to(_PACKAGE)}:{node.lineno}"
        for path in _PACKAGE.rglob("*.py")
        for node in ast.walk(ast.parse(read_text(path)))
        if isinstance(node, ast.Constant) and node.value == "WORKSPACE_ROOT"
    ]
    assert reads == []


@pytest.mark.medium
def test_workspace_root_in_the_hook_env_never_opens_a_protected_write(tmp_path: Path) -> None:
    """WORKSPACE_ROOT elsewhere: the gate still BLOCKs."""
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
    """A v1 registry is migrated, never "nothing to do"."""
    v1 = {"contexts": [{"name": "c", "state": "ativo", "repo_slug": "c"}]}
    own = _workspace(tmp_path / "ws", v1)
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(sys, "prefix", str(own / ".dadaia" / ".venv"))
    monkeypatch.chdir(outside)

    result = CliRunner().invoke(app, ["migrate", "--yes"])

    assert result.exit_code == 0, result.output
    registry = json.loads(read_text(own / ".dadaia" / "states" / "spec_contexts.json"))
    assert registry["schema_version"] == "3"


def test_context_show_reads_name_registry_and_session_from_one_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """From another workspace, `context show` reads its own."""
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


def _sentinel_cases(tmp_path: Path) -> dict[str, tuple[Path, bool]]:
    """Each directory shape that can stand for a workspace, with the one right answer."""
    full = _workspace(tmp_path / "full")
    as_dir = tmp_path / "as_dir"
    (as_dir / ".dadaia" / "states" / "spec_contexts.json").mkdir(parents=True)
    bare = tmp_path / "bare"
    (bare / ".dadaia").mkdir(parents=True)
    no_states = tmp_path / "no_states"
    (no_states / ".dadaia" / "states").mkdir(parents=True)
    return {
        "full": (full, True),
        "sentinel-is-a-directory": (as_dir, False),
        "bare-dadaia": (bare, False),
        "empty-states": (no_states, False),
    }


def test_is_workspace_is_the_one_sentinel_every_caller_agrees_with(tmp_path: Path) -> None:
    """A file named `spec_contexts.json` marks a workspace; a directory of that name, a bare
    `.dadaia/` or an empty `states/` does not — for the kernel and for every caller."""
    root = load_owner("dd-bug-resolution", "_root")
    for name, (ws, expected) in _sentinel_cases(tmp_path).items():
        probe = ws / "repos" / "x" / "f.txt"
        got = {
            "is_workspace": root.is_workspace(ws),
            "acting_root": workspace_resolver.acting_root(probe) == ws.resolve(),
            "owning_root": workspace_resolver.owning_root(probe) == ws.resolve(),
        }
        try:
            container.build_doctor_service(ws)
            got["container"] = True
        except WorkspaceNotInitializedError:
            got["container"] = False
        try:
            workspace_resolver.resolve_cli_workspace_root(ws)
            got["explicit"] = True
        except WorkspaceNotInitializedError:
            got["explicit"] = False
        assert got == dict.fromkeys(got, expected), name
