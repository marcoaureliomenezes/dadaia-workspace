"""Public CLI contracts for `dadaia context`."""

import json
import os
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


def _session_record_for(workspace: Path, output: str) -> dict:
    """Resolve the persisted session record from a bind command's confirmation output."""
    import re

    from dadaia_workspace.features.spec_context import session_identity

    session_id = ""
    for line in output.strip().split("\n"):
        if "DADAIA_SESSION_ID=" in line:
            session_id = line.split("DADAIA_SESSION_ID=", 1)[1].strip()
            break
        m = re.search(r"(sess_[0-9a-f]+)", line)
        if m:
            session_id = m.group(1)
            break
    assert session_id, f"no session id in bind output: {output!r}"
    record = session_identity.read_session(workspace, session_id)
    assert record is not None, f"session record {session_id} not persisted"
    return record


# --- FR-R4-01: --mode optional, default read ------------------------------


def test_context_bind_no_mode_exits_zero_default_read(workspace: Path) -> None:
    """FR-R4-01: bind with NO --mode exits 0 and defaults to read."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx"])
    assert result.exit_code == 0, result.output
    # Confirmation line, NOT a shell export line
    assert "export DADAIA_CONTEXT" not in result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "READ"
    assert record["context"] == "myctx"


def test_context_bind_no_mode_prints_human_confirmation(workspace: Path) -> None:
    """FR-R4-01/02: default bind prints a human confirmation (context/mode/session id)."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx"])
    assert result.exit_code == 0, result.output
    out = result.output.lower()
    assert "myctx" in result.output
    assert "read" in out
    assert "sess_" in result.output


# --- FR-R4-02: explicit modes persisted into the session record -----------


def test_context_bind_read_persists_read(workspace: Path) -> None:
    """FR-R4-02: explicit --mode read persists READ in the session record."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "READ"


def test_context_bind_refreshes_context_incumbent_pointer(workspace: Path) -> None:
    """NF-2 (rc-2): bind writes the CONTEXT incumbent pointer to the bind's session id.

    The incumbent pointer is what makes a default in-session bind bind the CONTEXT (not just
    a throwaway sid): the SDD gate resolves a harness session's mode through
    ``resolve_identity(ctx)`` → ``<ctx>.ptr`` → the persisted record.
    """
    from dadaia_workspace.features.spec_context import session_identity

    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    record = _session_record_for(workspace, result.output)
    incumbent = session_identity.read_incumbent_ptr(workspace, "myctx")
    assert incumbent == record["session_id"], (
        "bind must refresh the context incumbent pointer to its session id"
    )
    # And the gate resolves the bound mode through the incumbent for a DIFFERENT harness sid.
    identity = session_identity.resolve_identity(workspace, "myctx")
    assert identity["incumbent"] == record["session_id"]
    assert identity["mode"] == "READ"


# --- FR-W2-02 (T-014-09): bind writes the standalone bind-epoch marker --------


def test_context_bind_writes_bind_epoch_marker(workspace: Path) -> None:
    """FR-W2-02: a successful bind stamps `.dadaia/states/bind_epoch/<ctx>` (standalone).

    The marker is the SOLE trigger for context-memory injection and the ctx-inject hook's
    harness-real discovery source. It is NOT a field in the lease `.ptr`.
    """
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    marker = workspace / ".dadaia" / "states" / "bind_epoch" / "myctx"
    assert marker.is_file(), "bind must write a standalone bind-epoch marker"


def test_context_bind_marker_dir_created_on_demand(workspace: Path) -> None:
    """FR-W2-02: the bind_epoch dir is created on demand by the first bind."""
    _register_alive_ctx(workspace)
    marker_dir = workspace / ".dadaia" / "states" / "bind_epoch"
    assert not marker_dir.exists()
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    assert marker_dir.is_dir()


def test_context_bind_does_not_write_marker_into_ptr(workspace: Path) -> None:
    """FR-W2-02: the bind-epoch is a standalone file; the `.ptr` is untouched by it.

    The incumbent `.ptr` content must remain the bare session id — the epoch lives in
    its own file, never coupled to lease-incumbency.
    """
    from dadaia_workspace.features.spec_context import session_identity

    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    record = _session_record_for(workspace, result.output)
    incumbent = session_identity.read_incumbent_ptr(workspace, "myctx")
    assert incumbent == record["session_id"]
    # The `.ptr` carries ONLY the session id — no epoch/marker payload folded in.
    ptr_text = (
        (workspace / ".dadaia" / "sessions" / "runtime" / "myctx.ptr")
        .read_text(encoding="utf-8")
        .strip()
    )
    assert ptr_text == record["session_id"]


def test_context_rebind_refreshes_marker_mtime(workspace: Path) -> None:
    """FR-W2-02: re-binding the same context refreshes the marker mtime."""
    import os

    _register_alive_ctx(workspace)
    marker = workspace / ".dadaia" / "states" / "bind_epoch" / "myctx"

    assert _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"]).exit_code == 0
    first_mtime = marker.stat().st_mtime
    # Backdate the marker so a refresh is observable regardless of clock granularity.
    os.utime(marker, (first_mtime - 100, first_mtime - 100))
    backdated = marker.stat().st_mtime

    assert _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"]).exit_code == 0
    assert marker.stat().st_mtime > backdated, "re-bind must refresh the bind-epoch mtime"


def test_context_bind_implementation_persists_bound_implementation(workspace: Path) -> None:
    """FR-R4-02: --mode implementation persists BOUND_IMPLEMENTATION + creates session."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result.exit_code == 0, result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "BOUND_IMPLEMENTATION"
    assert record["release"] == "v1"

    session_id = record["session_id"]
    session_file = workspace / ".dadaia" / "sessions" / f"{session_id}.json"
    assert session_file.exists(), "Session file must be created"

    # Lock-3 retired: no per-release implementation lock file is written on bind.
    lock_file = workspace / ".dadaia" / "locks" / "implementation" / "myctx__v1.json"
    assert not lock_file.exists(), "bind must NOT create a Lock-3 implementation lock (v0.1.6)"


def test_context_bind_review_persists_bound_review(workspace: Path) -> None:
    """FR-R4-02: --mode review persists BOUND_REVIEW + creates session, no lock."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "review", "--release", "v1"]
    )
    assert result.exit_code == 0, result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "BOUND_REVIEW"

    lock_file = workspace / ".dadaia" / "locks" / "implementation" / "myctx__v1.json"
    assert not lock_file.exists(), "Review bind must NOT create implementation lock"


def test_context_bind_implementation_rebinds_same_harness_live_holder_coherently(
    workspace: Path,
) -> None:
    """A lease-taking rebind must not point `.ptr` at the CLI's throwaway sid.

    The live lock holder is the coherent runtime identity. Rebinding from the same process
    tree updates the holder's session record + lease release/mode and keeps doctor-visible
    identity sources aligned.
    """
    from dadaia_workspace.features.spec_context import lease, session_identity

    _register_alive_ctx(workspace)
    holder_sid = "sess_holder"
    lease.acquire(
        workspace,
        "myctx",
        holder_sid,
        "v0",
        "BOUND_IMPLEMENTATION",
        pid=os.getpid(),
    )

    result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result.exit_code == 0, result.output
    cli_record = _session_record_for(workspace, result.output)
    assert cli_record["session_id"] != holder_sid

    lock_record = lease.read_record(workspace, "myctx")
    assert lock_record is not None
    assert lock_record["session_id"] == holder_sid
    assert lock_record["release"] == "v1"
    assert lock_record["mode"] == "BOUND_IMPLEMENTATION"
    assert session_identity.read_incumbent_ptr(workspace, "myctx") == holder_sid

    holder_record = session_identity.read_session(workspace, holder_sid)
    assert holder_record is not None
    assert holder_record["session_id"] == holder_sid
    assert holder_record["release"] == "v1"
    assert holder_record["mode"] == "BOUND_IMPLEMENTATION"
    assert session_identity.coherence(workspace, "myctx", lock_holder=holder_sid) is None


def test_context_bind_read_does_not_move_incumbent_from_live_holder(workspace: Path) -> None:
    """A read bind must not create doctor-visible incoherence against a live holder."""
    from dadaia_workspace.features.spec_context import lease, session_identity

    _register_alive_ctx(workspace)
    holder_sid = "sess_holder"
    lease.acquire(
        workspace,
        "myctx",
        holder_sid,
        "v0",
        "BOUND_IMPLEMENTATION",
        pid=os.getpid(),
    )

    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    cli_record = _session_record_for(workspace, result.output)
    assert cli_record["mode"] == "READ"
    assert session_identity.read_incumbent_ptr(workspace, "myctx") == holder_sid
    assert session_identity.coherence(workspace, "myctx", lock_holder=holder_sid) is None


# --- legacy alias mapping --------------------------------------------------


def test_context_bind_spec_alias_maps_to_read(workspace: Path) -> None:
    """Legacy alias: --mode spec maps and persists as READ (no lease-taking)."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "spec"])
    assert result.exit_code == 0, result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "READ"


def test_context_bind_implementation_requires_release(workspace: Path) -> None:
    """--mode implementation without --release must error."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "implementation"])
    assert result.exit_code != 0


def test_context_bind_review_alias_requires_release(workspace: Path) -> None:
    """--mode review (lease-taking) without --release must error."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "review"])
    assert result.exit_code != 0


def test_context_bind_second_implementation_does_not_block(workspace: Path) -> None:
    """v0.1.6: bind no longer serializes — a second implementation bind succeeds
    (the gate's single TTL-lease, not bind, enforces one writer at write time)."""
    _register_alive_ctx(workspace)
    result1 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result1.exit_code == 0, result1.output
    result2 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result2.exit_code == 0, result2.output


def test_context_bind_invalid_mode(workspace: Path) -> None:
    """Unsupported mode exits non-zero."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "turbo"])
    assert result.exit_code != 0


# --- --print-env back-compat escape ---------------------------------------


def test_context_bind_print_env_emits_export_lines(workspace: Path) -> None:
    """Back-compat: --print-env still emits eval-compatible export lines."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--print-env"])
    assert result.exit_code == 0, result.output
    assert "export DADAIA_CONTEXT=myctx" in result.output
    assert "export DADAIA_SESSION_ID=" in result.output
    assert "export DADAIA_MODE=READ" in result.output
    # record still persisted under --print-env
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "READ"


def test_context_bind_print_env_implementation(workspace: Path) -> None:
    """--print-env with implementation emits BOUND-free DADAIA_MODE=IMPLEMENTATION."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(
        app,
        ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1", "--print-env"],
    )
    assert result.exit_code == 0, result.output
    assert "export DADAIA_MODE=IMPLEMENTATION" in result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "BOUND_IMPLEMENTATION"


# ---------------------------------------------------------------------------
# T-10d: context release
# ---------------------------------------------------------------------------


def test_context_release_deletes_session(workspace: Path) -> None:
    """v0.1.6: release deletes the session file (Lock-3 retired — no lock file to delete)."""
    _register_alive_ctx(workspace)
    bind_result = _runner.invoke(
        app,
        ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1", "--print-env"],
    )
    assert bind_result.exit_code == 0, bind_result.output

    lines = bind_result.output.strip().split("\n")
    session_line = next(line for line in lines if "DADAIA_SESSION_ID" in line)
    session_id = session_line.split("=")[1].strip()

    session_file = workspace / ".dadaia" / "sessions" / f"{session_id}.json"
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
    bind_result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "spec", "--print-env"])
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


def test_push_uses_explicit_upstream_ref_when_branch_names_differ(tmp_path: Path) -> None:
    """Regression: local branch `feature` tracking `origin/development` must push."""
    bare = tmp_path / "bare.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, check=True)

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
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=local, capture_output=True, check=True)
    (local / "README.md").write_text("one", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=local, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "one"], cwd=local, capture_output=True, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare)],
        cwd=local,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "HEAD:development"],
        cwd=local,
        capture_output=True,
        check=True,
    )

    upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=local,
        capture_output=True,
        text=True,
        check=True,
    )
    assert upstream.stdout.strip() == "origin/development"
    assert subprocess.run(["git", "push"], cwd=local, capture_output=True).returncode != 0

    (local / "README.md").write_text("two", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=local, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "two"], cwd=local, capture_output=True, check=True)
    pushed_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=local,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    GitSubprocessClient().push(local)

    remote_head = subprocess.run(
        ["git", "--git-dir", str(bare), "rev-parse", "development"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert remote_head == pushed_head
