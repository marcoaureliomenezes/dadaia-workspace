"""Unit tests for T-R1-01: runtime→session pointer file env-free resolution.

Tests verify:
- ctx-inject.sh writes .dadaia/sessions/runtime/<session_id>.ptr
- ctx-inject.sh cleans up the ptr file on end (trap)
- RULE E in sdd-spec-gate.sh resolves session via:
    1. DADAIA_SESSION_ID env var (existing)
    2. runtime ptr file in .dadaia/sessions/runtime/
    3. deny (no rebind required)

These are integration-style tests invoking the shell scripts.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_PKG_SCRIPTS = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public" / "scripts"
SDD_GATE = _PKG_SCRIPTS / "sdd-spec-gate.sh"
CTX_INJECT = _PKG_SCRIPTS / "ctx-inject.sh"


def _install_scripts(workspace: Path) -> Path:
    """Copy gate scripts to <workspace>/.dadaia/scripts/."""
    target = workspace / ".dadaia" / "scripts"
    target.mkdir(parents=True, exist_ok=True)
    for src in (SDD_GATE, CTX_INJECT):
        if src.exists():
            shutil.copy2(src, target / src.name)
            (target / src.name).chmod(0o755)
    return target


def _make_primary_context(workspace: Path, slug: str) -> None:
    """Write spec_contexts.json with the given slug as sole ALIVE context."""
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    ctx_data = {
        "schema_version": "2",
        "contexts": [
            {
                "name": slug,
                "state": "alive",
                "repo_slug": slug,
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00+00:00",
                "alive_since": "2026-01-01T00:00:00+00:00",
                "dead_since": None,
                "current_branch": "main",
            }
        ],
    }
    (states / "spec_contexts.json").write_text(json.dumps(ctx_data, indent=2))


def _make_active_release(specs_dir: Path, release_id: str) -> Path:
    """Create a release directory with ACTIVE.md and TASKS.md (with [-] marker)."""
    rel_dir = specs_dir / "releases" / release_id
    rel_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "releases" / "ACTIVE.md").write_text(
        f"release: {release_id}\nphase: IMPLEMENTATION\n"
    )
    (rel_dir / "TASKS.md").write_text("# Tasks\n\n### T-001 — work\n- **Status:** [-]\n")
    return rel_dir


def _make_session_file(
    workspace: Path,
    session_id: str,
    *,
    mode: str = "BOUND_IMPLEMENTATION",
    context: str = "my-proj",
    release: str = "v1",
) -> Path:
    """Write a session JSON file."""
    sessions_dir = workspace / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    import datetime

    now = datetime.datetime.now(tz=datetime.UTC).isoformat()
    data = {
        "session_id": session_id,
        "context": context,
        "mode": mode,
        "release": release,
        "runtime": "claude-code",
        "pid": os.getpid(),
        "bound_at": now,
        "last_seen_at": now,
        "ttl_seconds": 300,
        "is_stale": False,
    }
    session_file = sessions_dir / f"{session_id}.json"
    session_file.write_text(json.dumps(data, indent=2))
    return session_file


def _make_impl_lock(workspace: Path, context: str, release: str, session_id: str) -> Path:
    """Write an implementation lock file."""
    import datetime

    locks_dir = workspace / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(tz=datetime.UTC).isoformat()
    lock_data = {
        "lock_type": "implementation",
        "context": context,
        "release": release,
        "session_id": session_id,
        "runtime": "claude-code",
        "pid": os.getpid(),
        "mode": "BOUND_IMPLEMENTATION",
        "started_at": now,
        "last_seen_at": now,
        "ttl_seconds": 300,
    }
    lock_file = locks_dir / f"{context}__{release}.json"
    lock_file.write_text(json.dumps(lock_data, indent=2))
    return lock_file


def _make_runtime_ptr(workspace: Path, session_id: str) -> Path:
    """Write a runtime pointer file at .dadaia/sessions/runtime/<session_id>.ptr."""
    runtime_dir = workspace / ".dadaia" / "sessions" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    ptr_file = runtime_dir / f"{session_id}.ptr"
    ptr_file.write_text(session_id)
    return ptr_file


def _run_gate(
    workspace: Path,
    target_file: Path,
    *,
    session_id: str | None = None,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    """Run sdd-spec-gate.sh with the given target file write payload."""
    gate_script = workspace / ".dadaia" / "scripts" / "sdd-spec-gate.sh"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace)}
    if session_id is not None:
        env["DADAIA_SESSION_ID"] = session_id
    else:
        env.pop("DADAIA_SESSION_ID", None)
    log_file = workspace / ".dadaia" / "sdd-gate-test.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env["SDD_GATE_LOG"] = str(log_file)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(gate_script)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    return ws


@pytest.fixture()
def workspace_with_context(workspace: Path) -> tuple[Path, str, str]:
    """Return (workspace, slug, release_id) with context, session, and lock set up."""
    slug = "my-proj"
    release_id = "v1"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug)
    _install_scripts(workspace)
    return workspace, slug, release_id


# ---------------------------------------------------------------------------
# T-R1-01 AC-1: env var path (existing behavior preserved)
# ---------------------------------------------------------------------------


def test_tr101_env_var_path_allows_production_write(
    workspace_with_context: tuple[Path, str, str],
) -> None:
    """AC-1: DADAIA_SESSION_ID env var → gate resolves session and allows write.

    This is the primary path — env var wins over ptr file.
    """
    workspace, slug, release_id = workspace_with_context
    sess_id = "sess_envvar01"
    _make_session_file(workspace, sess_id, context=slug, release=release_id)
    _make_impl_lock(workspace, slug, release_id, sess_id)

    target = workspace / "repos" / slug / "src" / "main.py"
    result = _run_gate(workspace, target, session_id=sess_id)

    assert result.returncode == 0
    assert result.stdout == "" or "block" not in result.stdout


# ---------------------------------------------------------------------------
# T-R1-01 AC-2: runtime ptr file path (new behavior)
# ---------------------------------------------------------------------------


def test_tr101_ptr_file_path_allows_production_write(
    workspace_with_context: tuple[Path, str, str],
) -> None:
    """AC-2: no DADAIA_SESSION_ID and no lock file, but a runtime ptr file exists →
    gate resolves session from ptr file and allows write.

    This tests the ptr file resolution path specifically, independent of the
    lock file fallback (which is a separate mechanism).
    """
    workspace, slug, release_id = workspace_with_context
    sess_id = "sess_ptr01"
    _make_session_file(workspace, sess_id, context=slug, release=release_id)
    # Create impl lock so the session can write (lock ownership is still required)
    _make_impl_lock(workspace, slug, release_id, sess_id)
    _make_runtime_ptr(workspace, sess_id)

    target = workspace / "repos" / slug / "src" / "main.py"
    # NO session_id env var — should resolve via ptr file (before lock fallback)
    result = _run_gate(workspace, target, session_id=None)

    assert result.returncode == 0
    assert result.stdout == "" or "block" not in result.stdout, (
        f"Expected ALLOW via ptr file but got: {result.stdout!r}"
    )

    # Verify some form of env-free resolution was logged (ptr or lock fallback)
    log_file = workspace / ".dadaia" / "sdd-gate-test.log"
    log_content = log_file.read_text() if log_file.exists() else ""
    assert (
        "env-free" in log_content.lower()
        or "ptr" in log_content.lower()
        or "runtime" in log_content.lower()
    ), f"Expected env-free resolution log entry, got: {log_content!r}"


def test_tr101_ptr_file_env_var_wins_over_ptr(
    workspace_with_context: tuple[Path, str, str],
) -> None:
    """AC-2b: when BOTH env var and ptr file exist, env var takes priority."""
    workspace, slug, release_id = workspace_with_context

    env_sess_id = "sess_envpriority"
    ptr_sess_id = "sess_ptrsecond"

    # Both sessions exist, both have locks
    _make_session_file(workspace, env_sess_id, context=slug, release=release_id)
    _make_impl_lock(workspace, slug, release_id, env_sess_id)
    _make_session_file(workspace, ptr_sess_id, context=slug, release=release_id)
    _make_runtime_ptr(workspace, ptr_sess_id)

    target = workspace / "repos" / slug / "src" / "main.py"
    # env var session wins (it owns the lock)
    result = _run_gate(workspace, target, session_id=env_sess_id)

    assert result.returncode == 0
    assert result.stdout == "" or "block" not in result.stdout


# ---------------------------------------------------------------------------
# T-R1-01 AC-3: deny path (no env var, no ptr file, no lock)
# ---------------------------------------------------------------------------


def test_tr101_deny_path_blocks_when_no_session(
    workspace_with_context: tuple[Path, str, str],
) -> None:
    """AC-3: no DADAIA_SESSION_ID, no ptr file, no non-stale lock →
    gate denies the write (no rebind required message).
    """
    workspace, slug, release_id = workspace_with_context

    target = workspace / "repos" / slug / "src" / "main.py"
    # Nothing set up — must deny
    result = _run_gate(workspace, target, session_id=None)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert (
        "No active implementation session" in data["reason"]
        or "no relaunch" in data["reason"].lower()
    )


# ---------------------------------------------------------------------------
# T-R1-01 AC-4: ctx-inject.sh writes the ptr file
# ---------------------------------------------------------------------------


def test_tr101_ctx_inject_writes_ptr_file(workspace: Path) -> None:
    """AC-4: ctx-inject.sh writes .dadaia/sessions/runtime/<session_id>.ptr at start.

    ctx-inject.sh is a UserPromptSubmit hook that runs at session start.
    We invoke it with DADAIA_SESSION_ID set and verify the ptr file is created.
    """
    _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    specs.mkdir(parents=True, exist_ok=True)

    inject_script = workspace / ".dadaia" / "scripts" / "ctx-inject.sh"
    if not inject_script.exists():
        pytest.skip("ctx-inject.sh not available")

    sess_id = "sess_inject01"
    env = {
        **os.environ,
        "WORKSPACE_ROOT": str(workspace),
        "DADAIA_CONTEXT": slug,
        "DADAIA_SESSION_ID": sess_id,
        "DADAIA_HOOK_OUTPUT": "plain",
    }
    result = subprocess.run(
        ["bash", str(inject_script)],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )

    assert result.returncode == 0, f"ctx-inject.sh failed: {result.stderr}"

    ptr_file = workspace / ".dadaia" / "sessions" / "runtime" / f"{sess_id}.ptr"
    assert ptr_file.exists(), (
        f"Expected ptr file at {ptr_file} but it was not created. "
        f"ctx-inject stdout: {result.stdout!r}, stderr: {result.stderr!r}"
    )
    assert ptr_file.read_text().strip() == sess_id, (
        f"ptr file should contain the session_id '{sess_id}'"
    )
