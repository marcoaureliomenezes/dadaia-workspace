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


# ---------------------------------------------------------------------------
# create -> show --json -> list happy lifecycle
# ---------------------------------------------------------------------------


def test_context_create_show_list_happy_lifecycle(workspace: Path) -> None:
    result = _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    assert result.exit_code == 0, result.output

    show = _runner.invoke(app, ["context", "show", "alpha", "--json"])
    assert show.exit_code == 0, show.output
    data = json.loads(show.stdout)
    assert data["name"] == "alpha"
    assert data["state"] == "dead"
    # v2: no is_primary field
    assert "is_primary" not in data
    assert "alive_since" in data
    assert "dead_since" in data
    # v2: session sub-object present (null when no binding)
    assert "session" in data
    assert data["session"] is None

    list_out = _runner.invoke(app, ["context", "list"])
    assert list_out.exit_code == 0, list_out.output
    assert "alpha" in list_out.output
    assert "dead" in list_out.output


# ---------------------------------------------------------------------------
# Error matrix: duplicate create, unknown show, delete nonexistent, uninitialized
# workspace, alive/dead verb guards, invalid bind mode, implementation/review
# bind requiring --release, release without a session.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "invoke_args",
    [
        pytest.param(["context", "show", "ghost", "--json"], id="show-unknown-json"),
        pytest.param(["context", "delete", "ghost"], id="delete-nonexistent"),
        pytest.param(["context", "alive", "ghost"], id="alive-requires-existing"),
        pytest.param(["context", "dead", "ghost"], id="dead-requires-existing"),
        pytest.param(["context", "bind", "myctx", "--mode", "turbo"], id="bind-invalid-mode"),
        pytest.param(
            ["context", "bind", "myctx", "--mode", "implementation"],
            id="bind-implementation-requires-release",
        ),
        pytest.param(
            ["context", "bind", "myctx", "--mode", "review"],
            id="bind-review-requires-release",
        ),
    ],
)
def test_context_error_matrix(workspace: Path, invoke_args: list[str]) -> None:
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, invoke_args)
    assert result.exit_code != 0


def test_context_create_duplicate_and_dead_requires_alive(workspace: Path) -> None:
    """A duplicate create fails, and (AC-T10d-2) dead <name> fails if the context is
    not ALIVE — both against the same freshly-created DEAD context."""
    _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    result = _runner.invoke(app, ["context", "create", "alpha", "--repo", "alpha"])
    assert result.exit_code != 0

    result = _runner.invoke(app, ["context", "dead", "alpha"])
    assert result.exit_code != 0


def test_context_uninitialized_workspace_and_v1_workspace_exit_nonzero(
    tmp_path_factory: pytest.TempPathFactory, workspace: Path, monkeypatch
) -> None:
    """No `.dadaia/` at all → non-zero exit, and (AC-T10c-4) any `dadaia context`
    command on a v1 workspace exits non-zero with the migration prompt."""
    uninitialized = tmp_path_factory.mktemp("uninitialized")
    monkeypatch.chdir(uninitialized)
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code != 0

    monkeypatch.chdir(workspace)
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
    (states / "spec_contexts.json").write_text(json.dumps(v1_data))
    result = _runner.invoke(app, ["context", "list"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "MIGRATION REQUIRED" in combined or "dadaia migrate" in combined


# ---------------------------------------------------------------------------
# T-10d: context bind -- mode (session creation)
# FR-R4-01: --mode optional, default read. FR-R4-02: explicit modes persisted.
# Legacy alias mapping. --print-env back-compat escape.
# ---------------------------------------------------------------------------


def test_context_bind_read_persistence_variants(workspace: Path) -> None:
    """FR-R4-01/02: bind with NO --mode exits 0, defaults to read, persists READ, and
    prints a human confirmation (context/mode/session id) — never a shell export line.
    Explicit --mode read persists READ; legacy --mode spec alias maps and persists as
    READ too."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx"])
    assert result.exit_code == 0, result.output
    # Confirmation line, NOT a shell export line
    assert "export DADAIA_CONTEXT" not in result.output
    out = result.output.lower()
    assert "myctx" in result.output
    assert "read" in out
    assert "sess_" in result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "READ"
    assert record["context"] == "myctx"

    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "READ"

    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "spec"])
    assert result.exit_code == 0, result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "READ"


def test_context_bind_print_env_read_and_implementation_shapes(workspace: Path) -> None:
    """Back-compat: --print-env emits eval-compatible export lines for both the
    default READ bind and an implementation bind, and the session record still
    persists under --print-env in both cases."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--print-env"])
    assert result.exit_code == 0, result.output
    assert "export DADAIA_CONTEXT=myctx" in result.output
    assert "export DADAIA_SESSION_ID=" in result.output
    assert "export DADAIA_MODE=READ" in result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "READ"

    result = _runner.invoke(
        app,
        ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1", "--print-env"],
    )
    assert result.exit_code == 0, result.output
    assert "export DADAIA_MODE=IMPLEMENTATION" in result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == "BOUND_IMPLEMENTATION"


# --- caller-scoped harness binding -----------------------------------------


def test_context_bind_persists_harness_owned_record(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bind persists the mode under the current harness id without a global pointer."""
    from dadaia_workspace.features.spec_context import session_identity

    monkeypatch.setenv("CODEX_THREAD_ID", "harness-session")
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    record = session_identity.read_session(workspace, "harness-session")
    assert record is not None
    assert record["context"] == "myctx"
    assert record["mode"] == "READ"
    assert not (workspace / ".dadaia" / "sessions" / "runtime").exists()


# --- FR-W2-02 (T-014-09): bind writes the standalone bind-epoch marker --------


def test_context_bind_epoch_marker_lifecycle(workspace: Path) -> None:
    """FR-W2-02: a successful bind stamps `.dadaia/states/bind_epoch/<ctx>`
    (standalone) — created on demand and refreshed on re-bind.

    The marker is the SOLE trigger for context-memory injection and the ctx-inject
    hook's harness-real discovery source.
    """
    from dadaia_workspace.features.spec_context import session_identity

    _register_alive_ctx(workspace)
    marker_dir = workspace / ".dadaia" / "states" / "bind_epoch"
    marker = marker_dir / "myctx"
    assert not marker_dir.exists()

    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    assert marker_dir.is_dir()
    assert marker.is_file(), "bind must write a standalone bind-epoch marker"

    _session_record_for(workspace, result.output)
    assert not (workspace / ".dadaia" / "sessions" / "runtime").exists()

    first_mtime = marker.stat().st_mtime
    # Backdate the marker so a refresh is observable regardless of clock granularity.
    os.utime(marker, (first_mtime - 100, first_mtime - 100))
    backdated = marker.stat().st_mtime

    assert _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"]).exit_code == 0
    assert marker.stat().st_mtime > backdated, "re-bind must refresh the bind-epoch mtime"


# --- FR-R4-02: implementation / review bind persistence --------------------


@pytest.mark.parametrize(
    ("mode", "expected_record_mode"),
    [
        pytest.param("implementation", "BOUND_IMPLEMENTATION", id="implementation"),
        pytest.param("review", "BOUND_REVIEW", id="review"),
    ],
)
def test_context_bind_implementation_and_review_persist_mode(
    workspace: Path, mode: str, expected_record_mode: str
) -> None:
    """FR-R4-02: implementation/review binds persist BOUND_* mode and a session."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", mode, "--release", "v1"])
    assert result.exit_code == 0, result.output
    record = _session_record_for(workspace, result.output)
    assert record["mode"] == expected_record_mode

    if mode == "implementation":
        session_id = record["session_id"]
        session_file = workspace / ".dadaia" / "sessions" / f"{session_id}.json"
        assert session_file.exists(), "Session file must be created"

def test_context_bind_second_implementation_does_not_block(workspace: Path) -> None:
    """Independent implementation binds both succeed; peer presence is advisory."""
    _register_alive_ctx(workspace)
    result1 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result1.exit_code == 0, result1.output
    result2 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result2.exit_code == 0, result2.output


# ---------------------------------------------------------------------------
# T-10d: context release
# ---------------------------------------------------------------------------


def test_context_release_deletes_session_and_without_session_exits_nonzero(
    workspace: Path,
) -> None:
    """Release deletes the caller's session file; missing identity exits non-zero."""
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
    env = {**os.environ, "DADAIA_SESSION_ID": session_id}
    release_result = _runner.invoke(
        app,
        ["context", "release"],
        env=env,
    )
    assert release_result.exit_code == 0, release_result.output
    assert not session_file.exists(), "Session file must be deleted after release"

    no_session_env = {k: v for k, v in os.environ.items() if k != "DADAIA_SESSION_ID"}
    no_session_result = _runner.invoke(app, ["context", "release"], env=no_session_env)
    assert no_session_result.exit_code != 0


# ---------------------------------------------------------------------------
# T-10d: show --json session sub-object
# ---------------------------------------------------------------------------


def test_context_show_json_session_null_then_populated_when_bound(workspace: Path) -> None:
    """AC-T10d-6: show --json has session=null when no session binding, and a
    populated session sub-object when DADAIA_SESSION_ID is set and the session file
    is fresh."""
    _register_alive_ctx(workspace)

    env_no_session = {k: v for k, v in os.environ.items() if k != "DADAIA_SESSION_ID"}
    result = _runner.invoke(app, ["context", "show", "myctx", "--json"], env=env_no_session)
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert "session" in data
    assert data["session"] is None

    bind_result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "spec", "--print-env"])
    assert bind_result.exit_code == 0, bind_result.output
    lines = bind_result.output.strip().split("\n")
    session_line = next(line for line in lines if "DADAIA_SESSION_ID" in line)
    session_id = session_line.split("=")[1].strip()

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
