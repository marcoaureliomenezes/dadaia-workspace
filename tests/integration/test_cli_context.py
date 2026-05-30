"""dadaia context CLI — happy path + error paths (v2 model: ALIVE/DEAD).

T-10d: New verbs alive/dead/bind/release; old verbs activate/deactivate/promote/use
return non-zero with pointer to new verbs.
"""

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _register_alive_ctx(workspace: Path, name: str = "myctx") -> None:
    """Register an ALIVE v2 context directly in spec_contexts.json.

    `context bind --mode implementation|review` requires the context to be ALIVE
    (T-11 AC-T11-5). Writing the state file directly avoids a real `context alive`
    git clone in these CLI integration tests.
    """
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": name,
                        "state": "alive",
                        "repo_slug": name,
                        "repo_url": f"https://example.com/{name}.git",
                        "created_at": "2026-01-01T00:00:00Z",
                        "alive_since": "2026-01-01T00:00:00Z",
                        "dead_since": None,
                        "current_branch": "main",
                    }
                ],
            }
        )
    )


def test_context_create_lists_state_dead(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    assert result.exit_code == 0, result.output
    list_out = _runner.invoke(app, ["context", "list"])
    assert "alpha" in list_out.output
    assert "dead" in list_out.output


def test_context_show_json_returns_structured(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    result = _runner.invoke(app, ["context", "show", "alpha", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["name"] == "alpha"
    assert data["state"] == "dead"
    # v2: no is_primary field
    assert "is_primary" not in data
    assert "alive_since" in data
    assert "dead_since" in data
    # v2: session sub-object present (null when no binding)
    assert "session" in data
    assert data["session"] is None


def test_context_create_rejects_duplicate(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    result = _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    assert result.exit_code != 0


def test_context_show_json_unknown_returns_error(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "show", "ghost", "--json"])
    assert result.exit_code != 0


def test_context_show_table_output(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "beta", "--repo", "beta"])
    result = _runner.invoke(app, ["context", "show", "beta"])
    assert result.exit_code == 0, result.output
    assert "beta" in result.output


def test_context_show_no_active_context_json(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "show", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data.get("context") is None


def test_context_list_empty_workspace(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code == 0, result.output
    assert "No contexts" in result.output


def test_context_delete_dead_context(workspace: Path) -> None:
    _runner.invoke(app, ["context", "create", "to-del", "--repo", "to-del"])
    result = _runner.invoke(app, ["context", "delete", "to-del"])
    assert result.exit_code == 0, result.output
    assert "deleted" in result.output.lower() or "to-del" in result.output


def test_context_delete_nonexistent_errors(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "delete", "ghost"])
    assert result.exit_code != 0


def test_context_list_shows_alive_context(workspace: Path) -> None:
    """Write a v2 alive context directly to verify list shows it correctly."""
    states = workspace / ".dadaia" / "states"
    ctx_data = {
        "schema_version": "2",
        "contexts": [
            {
                "name": "alive-ctx",
                "state": "alive",
                "repo_slug": "alive-ctx",
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00Z",
                "alive_since": "2026-01-01T00:00:00Z",
                "dead_since": None,
                "current_branch": "main",
            }
        ],
    }
    import json as _json

    (states / "spec_contexts.json").write_text(_json.dumps(ctx_data))
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code == 0, result.output
    assert "alive-ctx" in result.output


def test_context_workspace_not_initialized_exits(tmp_path: Path, monkeypatch) -> None:
    # No .dadaia/ → workspace not initialized
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code != 0


def test_context_command_on_v1_workspace_exits_nonzero(workspace: Path) -> None:
    """AC-T10c-4: any dadaia context command on v1 workspace must exit non-zero
    with the migration prompt."""
    states = workspace / ".dadaia" / "states"
    v1_data = {
        "schema_version": "1",
        "contexts": [
            {
                "name": "old-ctx",
                "state": "ativo",
                "repo_slug": "old-ctx",
                "repo_url": "",
                "is_primary": False,
                "created_at": "2026-01-01T00:00:00Z",
                "activated_at": None,
            }
        ],
    }
    import json as _json

    (states / "spec_contexts.json").write_text(_json.dumps(v1_data))
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "MIGRATION REQUIRED" in combined or "dadaia migrate" in combined


# ---------------------------------------------------------------------------
# T-10d: deprecated verb stubs — must exit non-zero (AC-T10d-7)
# ---------------------------------------------------------------------------


def test_context_activate_exits_nonzero_with_pointer(workspace: Path) -> None:
    """AC-T10d-7: 'activate' exits non-zero with message pointing to new verb."""
    result = _runner.invoke(app, ["context", "activate", "some-ctx"])
    assert result.exit_code != 0
    combined = (result.output or "") + (result.stderr or "")
    assert "alive" in combined.lower() or "removed" in combined.lower()


def test_context_deactivate_exits_nonzero_with_pointer(workspace: Path) -> None:
    """AC-T10d-7: 'deactivate' exits non-zero with message pointing to new verb."""
    _runner.invoke(app, ["context", "deactivate"])
    # Missing argument may cause different exit code; either way must exit != 0
    # Since it's a deprecated stub with required arg, test without name too
    result2 = _runner.invoke(app, ["context", "deactivate", "some-ctx"])
    assert result2.exit_code != 0
    combined = (result2.output or "") + (result2.stderr or "")
    assert "dead" in combined.lower() or "removed" in combined.lower()


def test_context_promote_exits_nonzero_with_pointer(workspace: Path) -> None:
    """AC-T10d-7: 'promote' exits non-zero with message pointing to new verb."""
    result = _runner.invoke(app, ["context", "promote", "some-ctx"])
    assert result.exit_code != 0
    combined = (result.output or "") + (result.stderr or "")
    assert "removed" in combined.lower() or "v2" in combined.lower()


def test_context_use_exits_nonzero_with_pointer(workspace: Path) -> None:
    """AC-T10d-7: 'use' exits non-zero with message pointing to new verb."""
    result = _runner.invoke(app, ["context", "use", "some-ctx"])
    assert result.exit_code != 0
    combined = (result.output or "") + (result.stderr or "")
    assert "removed" in combined.lower() or "bind" in combined.lower()


# ---------------------------------------------------------------------------
# T-10d: new verbs alive / dead
# ---------------------------------------------------------------------------


def test_context_alive_requires_existing_context(workspace: Path) -> None:
    """AC-T10d-1: alive <name> must fail for a non-existent context."""
    result = _runner.invoke(app, ["context", "alive", "ghost"])
    assert result.exit_code != 0


def test_context_dead_requires_alive_context(workspace: Path) -> None:
    """AC-T10d-2: dead <name> must fail if context is not ALIVE."""
    _runner.invoke(app, ["context", "create", "proj", "--repo", "proj"])
    result = _runner.invoke(app, ["context", "dead", "proj"])
    assert result.exit_code != 0


def test_context_dead_requires_existing_context(workspace: Path) -> None:
    """AC-T10d-2: dead <name> must fail for a non-existent context."""
    result = _runner.invoke(app, ["context", "dead", "ghost"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# T-10d: context bind -- mode (session creation)
# ---------------------------------------------------------------------------


def test_context_bind_read_outputs_eval_lines(workspace: Path) -> None:
    """AC-T10d-3: bind --mode read prints eval-compatible export lines."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    assert "export DADAIA_CONTEXT=myctx" in result.output
    assert "export DADAIA_SESSION_ID=" in result.output
    assert "export DADAIA_MODE=READ" in result.output


def test_context_bind_spec_outputs_eval_lines(workspace: Path) -> None:
    """bind --mode spec prints eval-compatible export lines."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "spec"])
    assert result.exit_code == 0, result.output
    assert "export DADAIA_CONTEXT=myctx" in result.output
    assert "export DADAIA_SESSION_ID=" in result.output
    assert "export DADAIA_MODE=SPEC" in result.output


def test_context_bind_implementation_creates_lock_file(workspace: Path) -> None:
    """AC-T10d-3: bind --mode implementation creates session + lock files."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result.exit_code == 0, result.output
    assert "export DADAIA_CONTEXT=myctx" in result.output
    assert "export DADAIA_SESSION_ID=" in result.output
    assert "export DADAIA_MODE=IMPLEMENTATION" in result.output

    # Lock file must exist
    lock_file = workspace / ".dadaia" / "locks" / "implementation" / "myctx__v1.json"
    assert lock_file.exists(), "Implementation lock file must be created"

    # Session file must exist
    lines = result.output.strip().split("\n")
    session_line = next(line for line in lines if "DADAIA_SESSION_ID" in line)
    session_id = session_line.split("=")[1].strip()
    session_file = workspace / ".dadaia" / "sessions" / f"{session_id}.json"
    assert session_file.exists(), "Session file must be created"


def test_context_bind_implementation_requires_release(workspace: Path) -> None:
    """--mode implementation without --release must error."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "implementation"])
    assert result.exit_code != 0


def test_context_bind_implementation_lock_held_raises(workspace: Path) -> None:
    """AC-T10d-4: second bind --mode implementation with same context/release raises LockHeldError."""
    _register_alive_ctx(workspace)
    # First bind
    result1 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result1.exit_code == 0, result1.output

    # Second bind — must fail
    result2 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result2.exit_code != 0
    combined = (result2.output or "") + (result2.stderr or "")
    assert "HELD" in combined or "held" in combined.lower() or "lock" in combined.lower()


def test_context_bind_review_no_lock_file_created(workspace: Path) -> None:
    """AC-T10d-8: bind --mode review creates session file but NO implementation lock."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "review", "--release", "v1"]
    )
    assert result.exit_code == 0, result.output
    assert "export DADAIA_CONTEXT=myctx" in result.output
    assert "export DADAIA_SESSION_ID=" in result.output
    assert "export DADAIA_MODE=REVIEW" in result.output

    # No implementation lock file
    lock_file = workspace / ".dadaia" / "locks" / "implementation" / "myctx__v1.json"
    assert not lock_file.exists(), "Review bind must NOT create implementation lock"


def test_context_bind_review_blocks_when_impl_lock_held(workspace: Path) -> None:
    """AC-T10d-9: bind --mode review when impl lock HELD raises ReviewBlockedByImplementationError."""
    import os
    from datetime import UTC
    from datetime import datetime as _dt

    _register_alive_ctx(workspace)

    # Create a HELD impl lock (fresh timestamp + live PID so T-11 state machine = HELD)
    locks_dir = workspace / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock_file = locks_dir / "myctx__v1.json"
    now = _dt.now(tz=UTC).isoformat()
    lock_file.write_text(
        json.dumps({
            "lock_type": "implementation",
            "session_id": "sess_owner123",
            "context": "myctx",
            "release": "v1",
            "pid": os.getpid(),
            "last_seen_at": now,
            "ttl_seconds": 300,
        })
    )

    result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "review", "--release", "v1"]
    )
    assert result.exit_code != 0
    combined = (result.output or "") + (result.stderr or "")
    assert "sess_owner123" in combined or "implementation" in combined.lower()


def test_context_bind_implementation_blocks_when_review_session_exists(workspace: Path) -> None:
    """AC-T10d-10: bind --mode implementation raises ImplementationBlockedByReviewError when BOUND_REVIEW exists."""
    _register_alive_ctx(workspace)

    # Create a review session directly
    from datetime import UTC, datetime

    sessions_dir = workspace / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / "sess_review001.json"
    session_file.write_text(
        json.dumps(
            {
                "session_id": "sess_review001",
                "context": "myctx",
                "mode": "BOUND_REVIEW",
                "release": "v1",
                "runtime": "claude-code",
                "pid": 12345,
                "bound_at": datetime.now(tz=UTC).isoformat(),
                "last_seen_at": datetime.now(tz=UTC).isoformat(),
                "ttl_seconds": 300,
                "is_stale": False,
            }
        )
    )

    result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result.exit_code != 0
    combined = (result.output or "") + (result.stderr or "")
    assert "sess_review001" in combined or "review" in combined.lower()


def test_context_bind_invalid_mode(workspace: Path) -> None:
    """Unsupported mode exits non-zero."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "turbo"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# T-10d: context release
# ---------------------------------------------------------------------------


def test_context_release_deletes_session_and_lock(workspace: Path) -> None:
    """AC-T10d-5: release deletes session file and implementation lock."""
    _register_alive_ctx(workspace)
    bind_result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert bind_result.exit_code == 0, bind_result.output

    lines = bind_result.output.strip().split("\n")
    session_line = next(line for line in lines if "DADAIA_SESSION_ID" in line)
    session_id = session_line.split("=")[1].strip()

    lock_file = workspace / ".dadaia" / "locks" / "implementation" / "myctx__v1.json"
    session_file = workspace / ".dadaia" / "sessions" / f"{session_id}.json"
    assert lock_file.exists()
    assert session_file.exists()

    # Release with DADAIA_SESSION_ID env var set
    import os

    env = {**os.environ, "DADAIA_SESSION_ID": session_id}
    release_result = _runner.invoke(
        app,
        ["context", "release"],
        env=env,
    )
    assert release_result.exit_code == 0, release_result.output
    assert not lock_file.exists(), "Lock file must be deleted after release"
    assert not session_file.exists(), "Session file must be deleted after release"


def test_context_release_without_session_exits_nonzero(workspace: Path) -> None:
    """release without DADAIA_SESSION_ID exits non-zero."""
    import os

    # Ensure env var is absent
    env = {k: v for k, v in os.environ.items() if k != "DADAIA_SESSION_ID"}
    result = _runner.invoke(app, ["context", "release"], env=env)
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# T-10d: show --json session sub-object
# ---------------------------------------------------------------------------


def test_context_show_json_session_null_when_no_binding(workspace: Path) -> None:
    """AC-T10d-6: show --json has session=null when no session binding."""
    _register_alive_ctx(workspace)
    import os

    env = {k: v for k, v in os.environ.items() if k != "DADAIA_SESSION_ID"}
    result = _runner.invoke(app, ["context", "show", "myctx", "--json"], env=env)
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert "session" in data
    assert data["session"] is None


def test_context_show_json_session_populated_when_bound(workspace: Path) -> None:
    """AC-T10d-6: show --json has session sub-object when DADAIA_SESSION_ID is set and session file is fresh."""
    _register_alive_ctx(workspace)
    bind_result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "spec"]
    )
    assert bind_result.exit_code == 0, bind_result.output

    lines = bind_result.output.strip().split("\n")
    session_line = next(line for line in lines if "DADAIA_SESSION_ID" in line)
    session_id = session_line.split("=")[1].strip()

    import os

    env = {**os.environ, "DADAIA_SESSION_ID": session_id}
    show_result = _runner.invoke(app, ["context", "show", "myctx", "--json"], env=env)
    assert show_result.exit_code == 0, show_result.output
    data = json.loads(show_result.stdout)
    assert data["session"] is not None
    assert data["session"]["session_id"] == session_id


# ---------------------------------------------------------------------------
# T-BCR-08 smoke test — git push -u when no upstream tracking
# ---------------------------------------------------------------------------


def test_push_uses_set_upstream_when_no_tracking(tmp_path: Path) -> None:
    """Smoke test: GitSubprocessClient.push() uses -u on a repo with no upstream."""
    # Create a bare remote
    bare = tmp_path / "bare.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, check=True)

    # Create a local repo with at least one commit
    local = tmp_path / "local"
    local.mkdir()
    subprocess.run(["git", "init", str(local)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=local,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=local,
        capture_output=True,
        check=True,
    )
    (local / "README.md").write_text("hello")
    subprocess.run(["git", "add", "README.md"], cwd=local, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=local,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare)],
        cwd=local,
        capture_output=True,
        check=True,
    )

    # Pre-condition: no upstream tracking branch
    no_upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        cwd=local,
        capture_output=True,
        text=True,
    )
    assert no_upstream.returncode != 0, "pre-condition: upstream must NOT be set"

    # Exercise the fix
    client = GitSubprocessClient()
    client.push(local)  # must not raise

    # Post-condition: upstream tracking branch is now set
    has_upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        cwd=local,
        capture_output=True,
        text=True,
    )
    assert has_upstream.returncode == 0, (
        "upstream tracking must be set after git push -u; "
        f"got stderr: {has_upstream.stderr.strip()!r}"
    )
