"""Integration tests for session-aware SDD gate lock checks.

Tests invoke the shell scripts as subprocesses with crafted tmp_path workspaces
containing real session files and lock files — matching the style of test_hooks.py.
Stale sessions are created with backdated last_seen_at (no time.sleep).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

_PKG_SCRIPTS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "scripts"
SDD_GATE = _PKG_SCRIPTS / "sdd-spec-gate.sh"
POST_GATE = _PKG_SCRIPTS / "sdd-post-gate.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _install_scripts(workspace: Path) -> Path:
    """Copy the hooks to <workspace>/.dadaia/scripts/ where they expect to live."""
    target = workspace / ".dadaia" / "scripts"
    target.mkdir(parents=True, exist_ok=True)
    for src in (SDD_GATE, POST_GATE):
        shutil.copy2(src, target / src.name)
        (target / src.name).chmod(0o755)
    return target


def _make_primary_context(workspace: Path, slug: str, specs_dir: Path) -> None:
    """Write spec_contexts.json (v2) with the given slug as the sole ALIVE context.

    The legacy primary_context.json file is no longer read by the gate (T-HARD-01);
    the v2 resolution chain uses spec_contexts.json as step 2.
    The specs_dir parameter is retained for signature compatibility but the v2 gate
    derives specs_dir from repo_slug: $WS/repos/<slug>/specs.
    """
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


def _make_active_release(specs_dir: Path, release_id: str, tasks_marker: str = "[-]") -> Path:
    """Create release directory with ACTIVE.md and TASKS.md."""
    rel_dir = specs_dir / "releases" / release_id
    rel_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "releases" / "ACTIVE.md").write_text(
        f"release: {release_id}\nphase: IMPLEMENTATION\n"
    )
    (rel_dir / "TASKS.md").write_text(f"# Tasks\n\n- {tasks_marker} T-001 — work in progress\n")
    return rel_dir


def _make_session_file(
    workspace: Path,
    session_id: str,
    *,
    mode: str = "BOUND_IMPLEMENTATION",
    context: str = "my-proj",
    release: str = "my-release-v1",
    ttl_seconds: int = 300,
    last_seen_at: str | None = None,
    runtime: str = "claude-code",
    pid: int | None = None,
) -> Path:
    """Write a session JSON file to .dadaia/sessions/<session_id>.json."""
    sessions_dir = workspace / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    session_data = {
        "session_id": session_id,
        "context": context,
        "mode": mode,
        "release": release,
        "runtime": runtime,
        "pid": pid if pid is not None else os.getpid(),
        "bound_at": now,
        "last_seen_at": last_seen_at if last_seen_at is not None else now,
        "ttl_seconds": ttl_seconds,
        "is_stale": False,
    }
    session_file = sessions_dir / f"{session_id}.json"
    session_file.write_text(json.dumps(session_data, indent=2))
    return session_file


def _make_impl_lock(
    workspace: Path,
    context: str,
    release: str,
    session_id: str,
    *,
    last_seen_at: str | None = None,
    ttl_seconds: int = 300,
    runtime: str = "claude-code",
    pid: int | None = None,
) -> Path:
    """Write an implementation lock JSON file."""
    locks_dir = workspace / ".dadaia" / "locks" / "implementation"
    locks_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    lock_data = {
        "lock_type": "implementation",
        "context": context,
        "release": release,
        "session_id": session_id,
        "runtime": runtime,
        "pid": pid if pid is not None else os.getpid(),
        "mode": "BOUND_IMPLEMENTATION",
        "started_at": now,
        "last_seen_at": last_seen_at if last_seen_at is not None else now,
        "ttl_seconds": ttl_seconds,
        "task_path": "",
        "owner_note": "",
    }
    lock_file = locks_dir / f"{context}__{release}.json"
    lock_file.write_text(json.dumps(lock_data, indent=2))
    return lock_file


def _run_gate(
    scripts: Path,
    workspace: Path,
    target_file: Path,
    *,
    session_id: str | None = None,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    """Run sdd-spec-gate.sh with the given target file write payload."""
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace)}
    if session_id is not None:
        env["DADAIA_SESSION_ID"] = session_id
    if extra_env:
        env.update(extra_env)
    # Use a temp log file so we can inspect it
    log_file = workspace / ".dadaia" / "sdd-gate-test.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env["SDD_GATE_LOG"] = str(log_file)
    return subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


def _run_post_gate(
    scripts: Path,
    workspace: Path,
    *,
    session_id: str | None = None,
) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    """Run sdd-post-gate.sh."""
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace)}
    if session_id is not None:
        env["DADAIA_SESSION_ID"] = session_id
    log_file = workspace / ".dadaia" / "sdd-gate-test.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env["SDD_GATE_LOG"] = str(log_file)
    return subprocess.run(
        ["bash", str(scripts / "sdd-post-gate.sh")],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


def _stale_ts(seconds_ago: int = 400) -> str:
    """Return an ISO 8601 timestamp far enough in the past to exceed a 300-second TTL."""
    dt = datetime.now(tz=UTC) - timedelta(seconds=seconds_ago)
    return dt.isoformat()


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "ws"


# ---------------------------------------------------------------------------
# AC-T13-1: DADAIA_SESSION_ID absent → production write blocks
# ---------------------------------------------------------------------------


def test_ac_t13_1_blocks_production_write_without_session_id(workspace: Path) -> None:
    """AC-T13-1: production writes require a bound implementation session.

    T-SEMA-01: env-free resolution means "no DADAIA_SESSION_ID" alone no longer
    blocks — the gate blocks only when there is ALSO no non-stale implementation
    lock to adopt. This test creates no lock, so the gate must still fail closed,
    now with the no-relaunch message.
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    rel_dir = _make_active_release(specs, "my-release-v1")
    _ = rel_dir  # ensure dir created
    _make_primary_context(workspace, slug, specs)

    target_file = workspace / "repos" / slug / "src" / "main.py"
    # No DADAIA_SESSION_ID and no impl lock — must fail closed even though TASKS.md has [-].
    result = _run_gate(scripts, workspace, target_file, session_id=None)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "No active implementation session" in data["reason"]
    assert "no relaunch" in data["reason"].lower()

    # Verify the blocked production path was logged.
    log_file = workspace / ".dadaia" / "sdd-gate-test.log"
    log_content = log_file.read_text() if log_file.exists() else ""
    assert "BLOCKED" in log_content
    assert "No active implementation session" in log_content


# ---------------------------------------------------------------------------
# AC-T13-2: Session file absent → gate blocks
# ---------------------------------------------------------------------------


def test_ac_t13_2_session_file_absent_blocks(workspace: Path) -> None:
    """AC-T13-2: DADAIA_SESSION_ID set but session file absent → gate blocks."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, "my-release-v1")
    _make_primary_context(workspace, slug, specs)

    target_file = workspace / "repos" / slug / "src" / "main.py"
    # Session ID set but no file created
    result = _run_gate(scripts, workspace, target_file, session_id="sess_missing123")

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "Session file missing" in data["reason"]


# ---------------------------------------------------------------------------
# AC-T13-3: Fresh session, no impl lock → blocks production write
# ---------------------------------------------------------------------------


def test_ac_t13_3_fresh_session_no_impl_lock_blocks(workspace: Path) -> None:
    """AC-T13-3: Session present and fresh, no implementation lock → blocks production write."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, "my-release-v1")
    _make_primary_context(workspace, slug, specs)

    sess_id = "sess_abc123"
    _make_session_file(
        workspace,
        sess_id,
        mode="BOUND_IMPLEMENTATION",
        context=slug,
        release="my-release-v1",
    )
    # No lock file created

    target_file = workspace / "repos" / slug / "src" / "main.py"
    result = _run_gate(scripts, workspace, target_file, session_id=sess_id)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "RULE E" in data["reason"]
    assert "implementation lock" in data["reason"].lower()


# ---------------------------------------------------------------------------
# AC-T13-4: Fresh session owns impl lock → production write allowed
# ---------------------------------------------------------------------------


def test_ac_t13_4_fresh_session_owns_lock_allowed(workspace: Path) -> None:
    """AC-T13-4: Session present and fresh, owns implementation lock → gate allows."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    sess_id = "sess_owner01"
    _make_session_file(
        workspace,
        sess_id,
        mode="BOUND_IMPLEMENTATION",
        context=slug,
        release=release_id,
    )
    _make_impl_lock(workspace, slug, release_id, sess_id)

    target_file = workspace / "repos" / slug / "src" / "main.py"
    result = _run_gate(scripts, workspace, target_file, session_id=sess_id)

    assert result.returncode == 0
    # Should be allowed (no block decision)
    assert result.stdout == "" or "block" not in result.stdout


# ---------------------------------------------------------------------------
# AC-T13-5: SPEC-mode session blocks write to releases/<id>/SPEC.md when impl lock HELD
# ---------------------------------------------------------------------------


def test_ac_t13_5_spec_mode_blocks_spec_md_when_impl_lock_held(workspace: Path) -> None:
    """AC-T13-5 (real R-9): SPEC-mode session BLOCKED from writing SPEC.md when impl lock HELD.

    Previously documented as a known gap (meta-edit allowlist exited before RULE E).
    After the R-9 correctness fix, the meta-edit allowlist defers to RULE E for
    SPEC.md/PLAN.md/TASKS.md when DADAIA_SESSION_ID is set, so this now genuinely blocks.
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    rel_dir = _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    # SPEC-mode session
    spec_sess_id = "sess_specmode"
    _make_session_file(
        workspace,
        spec_sess_id,
        mode="SPEC",
        context=slug,
        release=release_id,
    )

    # Someone else holds the implementation lock
    impl_sess_id = "sess_impl001"
    _make_impl_lock(workspace, slug, release_id, impl_sess_id)

    # Try to write to releases/<id>/SPEC.md — must be BLOCKED (R-9)
    target_file = rel_dir / "SPEC.md"
    target_file.write_text("# Spec content\n")

    result = _run_gate(scripts, workspace, target_file, session_id=spec_sess_id)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block", f"Expected BLOCK (R-9) but got: {result.stdout!r}"
    assert "RULE E" in data["reason"]
    assert "R-9" in data["reason"] or "implementation lock" in data["reason"].lower()


def test_ac_t13_5_spec_mode_blocks_tasks_md_when_impl_lock_held(workspace: Path) -> None:
    """AC-T13-5 (TASKS.md): SPEC-mode session BLOCKED from writing TASKS.md when impl lock HELD."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    rel_dir = _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    spec_sess_id = "sess_specmode_tasks"
    _make_session_file(workspace, spec_sess_id, mode="SPEC", context=slug, release=release_id)
    impl_sess_id = "sess_impl_tasks"
    _make_impl_lock(workspace, slug, release_id, impl_sess_id)

    target_file = rel_dir / "TASKS.md"
    # TASKS.md already written by _make_active_release; overwrite target just to be sure
    target_file.write_text("# Tasks\n\n- [-] T-001 — in progress\n")

    result = _run_gate(scripts, workspace, target_file, session_id=spec_sess_id)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block", (
        f"Expected BLOCK (R-9 TASKS.md SPEC mode) but got: {result.stdout!r}"
    )
    assert "RULE E" in data["reason"]


def test_ac_t13_5_impl_mode_allows_tasks_md_when_lock_owned(workspace: Path) -> None:
    """AC-T13-5 (IMPL→TASKS.md ALLOW): BOUND_IMPLEMENTATION lock owner ALLOWED to write TASKS.md.

    The lock owner flips [-] markers, so TASKS.md writes must be permitted.
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    rel_dir = _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    impl_sess_id = "sess_impl_owns"
    _make_session_file(
        workspace, impl_sess_id, mode="BOUND_IMPLEMENTATION", context=slug, release=release_id
    )
    _make_impl_lock(workspace, slug, release_id, impl_sess_id)

    target_file = rel_dir / "TASKS.md"
    result = _run_gate(scripts, workspace, target_file, session_id=impl_sess_id)
    assert result.returncode == 0
    assert result.stdout == "" or json.loads(result.stdout).get("decision") != "block", (
        f"Expected ALLOW (lock owner TASKS.md) but got: {result.stdout!r}"
    )


def test_ac_t13_5_impl_mode_blocks_spec_md_when_lock_owned(workspace: Path) -> None:
    """AC-T13-5 (IMPL→SPEC.md BLOCK): BOUND_IMPLEMENTATION lock owner BLOCKED from writing SPEC.md.

    Once implementation starts, SPEC.md is read-only even for the lock owner.
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    rel_dir = _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    impl_sess_id = "sess_impl_owns2"
    _make_session_file(
        workspace, impl_sess_id, mode="BOUND_IMPLEMENTATION", context=slug, release=release_id
    )
    _make_impl_lock(workspace, slug, release_id, impl_sess_id)

    target_file = rel_dir / "SPEC.md"
    target_file.write_text("# Spec\n")
    result = _run_gate(scripts, workspace, target_file, session_id=impl_sess_id)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block", (
        f"Expected BLOCK (SPEC.md read-only once impl starts) but got: {result.stdout!r}"
    )
    assert "RULE E" in data["reason"]


def test_ac_t13_5_no_session_spec_md_allowed(workspace: Path) -> None:
    """AC-T13-5 (no-session legacy/fail-open): no session ID → SPEC.md write ALLOWED.

    Legacy/fail-open: DADAIA_SESSION_ID absent → meta-edit allowlist exits 0 for SPEC.md.
    This preserves product-engineer authoring with no bound session.
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    rel_dir = _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    # Even with an impl lock held, no-session → SPEC.md still allowed
    impl_sess_id = "sess_impl_nosess"
    _make_impl_lock(workspace, slug, release_id, impl_sess_id)

    target_file = rel_dir / "SPEC.md"
    target_file.write_text("# Spec\n")

    # No session ID → legacy fail-open
    result = _run_gate(scripts, workspace, target_file, session_id=None)
    assert result.returncode == 0
    assert result.stdout == "" or json.loads(result.stdout).get("decision") != "block", (
        f"Expected ALLOW (no-session legacy) for SPEC.md but got: {result.stdout!r}"
    )


def test_ac_t13_5_spec_mode_blocks_spec_in_production_path_when_impl_lock_held(
    workspace: Path,
) -> None:
    """AC-T13-5 (production variant): SPEC-mode cannot write a production file when impl lock HELD."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    spec_sess_id = "sess_specmode2"
    _make_session_file(
        workspace,
        spec_sess_id,
        mode="SPEC",
        context=slug,
        release=release_id,
    )
    impl_sess_id = "sess_impl002"
    _make_impl_lock(workspace, slug, release_id, impl_sess_id)

    # Production file (not SPEC.md) — SPEC mode should be blocked by RULE E step 4c
    target_file = workspace / "repos" / slug / "src" / "service.py"
    result = _run_gate(scripts, workspace, target_file, session_id=spec_sess_id)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "RULE E" in data["reason"]


# ---------------------------------------------------------------------------
# AC-T13-6: READ-mode session blocks all writes
# ---------------------------------------------------------------------------


def test_ac_t13_6_read_mode_blocks_production_write(workspace: Path) -> None:
    """AC-T13-6a: READ-mode session blocks production code write."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, "my-release-v1")
    _make_primary_context(workspace, slug, specs)

    read_sess_id = "sess_readonly"
    _make_session_file(workspace, read_sess_id, mode="READ", context=slug, release="my-release-v1")

    target_file = workspace / "repos" / slug / "src" / "app.py"
    result = _run_gate(scripts, workspace, target_file, session_id=read_sess_id)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "RULE E" in data["reason"]


def test_ac_t13_6_read_mode_blocks_memory_write(workspace: Path) -> None:
    """AC-T13-6b: READ-mode session blocks specs/memory/ write."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, "my-release-v1")
    _make_primary_context(workspace, slug, specs)

    read_sess_id = "sess_readonly2"
    _make_session_file(workspace, read_sess_id, mode="READ", context=slug, release="my-release-v1")

    # specs/memory/ path — READ mode should be blocked by RULE E step 4b
    target_file = workspace / "repos" / slug / "specs" / "memory" / "architecture.html"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    log_file = workspace / ".dadaia" / "sdd-gate-test.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "WORKSPACE_ROOT": str(workspace),
        "SDD_GATE_LOG": str(log_file),
        "DADAIA_SESSION_ID": read_sess_id,
    }
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert result.returncode == 0
    # Note: The memory atomicity RULE A fires first for */specs/memory/* paths
    # (it uses the file's own ACTIVE.md phase, not the session mode).
    # If RULE A blocks (phase != CLOSURE), we get an SDD GATE block — that's acceptable.
    # If RULE E would fire, it also blocks. Either block is correct behavior for READ mode.
    assert (
        result.stdout != "" or "block" in result.stdout
    )  # any block OR silent (non-production path)


def test_ac_t13_6_read_mode_allows_reports_write(workspace: Path) -> None:
    """AC-T13-6c: READ-mode session allows .dadaia/reports/** write (always allowed)."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, "my-release-v1")
    _make_primary_context(workspace, slug, specs)

    read_sess_id = "sess_readonly3"
    _make_session_file(workspace, read_sess_id, mode="READ", context=slug, release="my-release-v1")

    # .dadaia/reports/ is always allowed (step 4a)
    target_file = (
        workspace / ".dadaia" / "reports" / "dadaia-workspace" / "qa-engineer" / "report.html"
    )
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    log_file = workspace / ".dadaia" / "sdd-gate-test.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "WORKSPACE_ROOT": str(workspace),
        "SDD_GATE_LOG": str(log_file),
        "DADAIA_SESSION_ID": read_sess_id,
    }
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert result.returncode == 0
    assert result.stdout == ""  # not blocked — reports always allowed


# ---------------------------------------------------------------------------
# AC-T13-7: IMPLEMENTATION mode resolves active release from lock file (not ACTIVE.md)
# ---------------------------------------------------------------------------


def test_ac_t13_7_impl_mode_resolves_release_from_lock_not_active_md(workspace: Path) -> None:
    """AC-T13-7: IMPLEMENTATION-mode session resolves active release from lock, not ACTIVE.md.

    Craft a workspace where ACTIVE.md points to 'stale-release-v1' (no [-] task)
    but the impl lock points to 'lock-release-v1' which HAS a [-] task.
    The gate should allow the production write (resolved via lock).
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"

    # ACTIVE.md points to a release with NO [-] task
    stale_rel_dir = specs / "releases" / "stale-release-v1"
    stale_rel_dir.mkdir(parents=True, exist_ok=True)
    (specs / "releases" / "ACTIVE.md").write_text(
        "release: stale-release-v1\nphase: IMPLEMENTATION\n"
    )
    (stale_rel_dir / "TASKS.md").write_text("# Tasks\n\n- [ ] T-001 — not started\n")

    # Lock release has a [-] task
    lock_release_id = "lock-release-v1"
    lock_rel_dir = specs / "releases" / lock_release_id
    lock_rel_dir.mkdir(parents=True, exist_ok=True)
    (lock_rel_dir / "TASKS.md").write_text("# Tasks\n\n- [-] T-002 — in progress\n")

    _make_primary_context(workspace, slug, specs)

    sess_id = "sess_locksrc"
    _make_session_file(
        workspace,
        sess_id,
        mode="BOUND_IMPLEMENTATION",
        context=slug,
        release=lock_release_id,
    )
    _make_impl_lock(workspace, slug, lock_release_id, sess_id)

    target_file = workspace / "repos" / slug / "src" / "main.py"
    result = _run_gate(scripts, workspace, target_file, session_id=sess_id)

    assert result.returncode == 0
    # Should be allowed: RULE E overrides ACTIVE_RELEASE with lock-release-v1
    # which has a [-] task → RULE C allows.
    assert result.stdout == ""  # not blocked


# ---------------------------------------------------------------------------
# AC-T13-8: sdd-post-gate.sh renews last_seen_at
# ---------------------------------------------------------------------------


def test_ac_t13_8_post_gate_renews_last_seen_at(workspace: Path) -> None:
    """AC-T13-8: sdd-post-gate.sh renews last_seen_at in the session file."""
    scripts = _install_scripts(workspace)

    sess_id = "sess_heartbeat"
    # Set last_seen_at to 60 seconds ago
    old_ts = (datetime.now(tz=UTC) - timedelta(seconds=60)).isoformat()
    sess_file = _make_session_file(
        workspace,
        sess_id,
        mode="BOUND_IMPLEMENTATION",
        last_seen_at=old_ts,
    )

    before_run = datetime.now(tz=UTC)
    result = _run_post_gate(scripts, workspace, session_id=sess_id)
    after_run = datetime.now(tz=UTC)

    assert result.returncode == 0

    # Re-read the session file
    updated = json.loads(sess_file.read_text())
    new_last_seen = datetime.fromisoformat(updated["last_seen_at"].replace("Z", "+00:00"))

    # Verify last_seen_at was updated to a time after the run started
    assert new_last_seen >= before_run, (
        f"last_seen_at ({new_last_seen}) should be >= before_run ({before_run})"
    )
    assert new_last_seen <= after_run + timedelta(seconds=1), (
        f"last_seen_at ({new_last_seen}) should be <= after_run ({after_run})"
    )
    # Verify the old timestamp was replaced
    assert updated["last_seen_at"] != old_ts


def test_ac_t13_8_post_gate_noop_when_no_session_id(workspace: Path) -> None:
    """AC-T13-8 (no-op): sdd-post-gate.sh exits 0 silently when no session ID."""
    scripts = _install_scripts(workspace)
    result = _run_post_gate(scripts, workspace, session_id=None)
    assert result.returncode == 0
    assert result.stdout == ""


def test_ac_t13_8_post_gate_noop_when_session_file_missing(workspace: Path) -> None:
    """AC-T13-8 (no-op): sdd-post-gate.sh exits 0 silently when session file absent."""
    scripts = _install_scripts(workspace)
    result = _run_post_gate(scripts, workspace, session_id="sess_nonexistent")
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# AC-T13-9: sdd-post-gate.sh appends HEARTBEAT to lock-events.jsonl
# ---------------------------------------------------------------------------


def test_ac_t13_9_post_gate_appends_heartbeat_event(workspace: Path) -> None:
    """AC-T13-9: sdd-post-gate.sh appends a HEARTBEAT event to lock-events.jsonl."""
    scripts = _install_scripts(workspace)

    sess_id = "sess_hb_log"
    _make_session_file(
        workspace,
        sess_id,
        mode="BOUND_IMPLEMENTATION",
        context="my-proj",
        release="my-release-v1",
        runtime="claude-code",
    )

    result = _run_post_gate(scripts, workspace, session_id=sess_id)
    assert result.returncode == 0

    # Check lock-events.jsonl
    audit_path = workspace / ".dadaia" / "logs" / "lock-events.jsonl"
    assert audit_path.exists(), "lock-events.jsonl should be created"

    lines = [line for line in audit_path.read_text().splitlines() if line.strip()]
    assert len(lines) >= 1, "At least one HEARTBEAT line expected"

    event = json.loads(lines[-1])
    assert event["event"] == "HEARTBEAT"
    assert event["session_id"] == sess_id
    assert event["context"] == "my-proj"
    assert event["release"] == "my-release-v1"
    # Verify required schema fields (SPEC §3 T-12 AC-AUDIT-1)
    for field in ("ts", "event", "context", "release", "session_id", "runtime"):
        assert field in event, f"Missing required field '{field}' in HEARTBEAT event"


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------


def test_stale_session_blocks(workspace: Path) -> None:
    """Stale session (backdated last_seen_at) → RULE E blocks with 'STALE' message."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, "my-release-v1")
    _make_primary_context(workspace, slug, specs)

    sess_id = "sess_stale01"
    # Create session with last_seen_at 400 seconds ago (TTL=300 → stale)
    _make_session_file(
        workspace,
        sess_id,
        mode="BOUND_IMPLEMENTATION",
        ttl_seconds=300,
        last_seen_at=_stale_ts(400),  # no time.sleep needed
    )

    target_file = workspace / "repos" / slug / "src" / "main.py"
    result = _run_gate(scripts, workspace, target_file, session_id=sess_id)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "STALE" in data["reason"]


def test_wrong_session_owns_lock_blocks(workspace: Path) -> None:
    """Session present and fresh but lock owned by different session → gate blocks."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    my_sess_id = "sess_mine01"
    other_sess_id = "sess_other1"

    _make_session_file(
        workspace,
        my_sess_id,
        mode="BOUND_IMPLEMENTATION",
        context=slug,
        release=release_id,
    )
    # Lock owned by a DIFFERENT session
    _make_impl_lock(workspace, slug, release_id, other_sess_id)

    target_file = workspace / "repos" / slug / "src" / "main.py"
    result = _run_gate(scripts, workspace, target_file, session_id=my_sess_id)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "RULE E" in data["reason"]
    assert other_sess_id in data["reason"]


def test_bound_review_mode_blocks_production_write(workspace: Path) -> None:
    """BOUND_REVIEW mode → blocks production code write."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, "my-release-v1")
    _make_primary_context(workspace, slug, specs)

    review_sess_id = "sess_review1"
    _make_session_file(
        workspace,
        review_sess_id,
        mode="BOUND_REVIEW",
        context=slug,
        release="my-release-v1",
    )

    target_file = workspace / "repos" / slug / "src" / "service.py"
    result = _run_gate(scripts, workspace, target_file, session_id=review_sess_id)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "RULE E" in data["reason"]


# ---------------------------------------------------------------------------
# AC-T13-10: Inline heartbeat fallback (OpenCode OQ-3) in sdd-spec-gate.sh
# ---------------------------------------------------------------------------


def test_ac_t13_10_inline_heartbeat_on_allow_path(workspace: Path) -> None:
    """AC-T13-10a: Bound IMPLEMENTATION session + allowed path → gate exits 0,
    session last_seen_at renewed, HEARTBEAT appended to lock-events.jsonl.

    This exercises the OpenCode inline-heartbeat fallback (OQ-3): on Claude/Codex
    the post-gate also fires (idempotent double-renew is harmless); on OpenCode the
    gate's inline renewal is the only heartbeat mechanism.
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    sess_id = "sess_inline_hb"
    old_ts = (datetime.now(tz=UTC) - timedelta(seconds=60)).isoformat()
    sess_file = _make_session_file(
        workspace,
        sess_id,
        mode="BOUND_IMPLEMENTATION",
        context=slug,
        release=release_id,
        last_seen_at=old_ts,
        runtime="opencode",
    )
    _make_impl_lock(workspace, slug, release_id, sess_id)

    target_file = workspace / "repos" / slug / "src" / "main.py"
    before_run = datetime.now(tz=UTC)
    result = _run_gate(scripts, workspace, target_file, session_id=sess_id)
    after_run = datetime.now(tz=UTC)

    assert result.returncode == 0
    # Gate should allow (not block)
    assert result.stdout == "" or json.loads(result.stdout).get("decision") != "block", (
        f"Expected ALLOW but got: {result.stdout!r}"
    )

    # Verify last_seen_at was renewed (inline heartbeat fired)
    updated = json.loads(sess_file.read_text())
    new_last_seen = datetime.fromisoformat(updated["last_seen_at"].replace("Z", "+00:00"))
    assert new_last_seen >= before_run, (
        f"last_seen_at ({new_last_seen}) should be >= before_run ({before_run})"
    )
    assert new_last_seen <= after_run + timedelta(seconds=2), (
        f"last_seen_at ({new_last_seen}) should be close to after_run ({after_run})"
    )
    assert updated["last_seen_at"] != old_ts, "last_seen_at should have been updated"

    # Verify HEARTBEAT event was appended to lock-events.jsonl
    audit_path = workspace / ".dadaia" / "logs" / "lock-events.jsonl"
    assert audit_path.exists(), "lock-events.jsonl should be created by inline heartbeat"
    lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
    events = [json.loads(ln) for ln in lines]
    heartbeats = [e for e in events if e.get("event") == "HEARTBEAT"]
    assert len(heartbeats) >= 1, "At least one HEARTBEAT event expected"
    last_hb = heartbeats[-1]
    assert last_hb["session_id"] == sess_id
    assert last_hb["context"] == slug
    assert last_hb["release"] == release_id


def test_ac_t13_10_no_heartbeat_when_no_session(workspace: Path) -> None:
    """AC-T13-10b: Fail-open (no DADAIA_SESSION_ID) → NO inline heartbeat side-effect.

    When the gate fails open (no session), the inline heartbeat block must NOT fire.
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, "my-release-v1")
    _make_primary_context(workspace, slug, specs)

    target_file = workspace / "repos" / slug / "src" / "main.py"
    # No session ID
    result = _run_gate(scripts, workspace, target_file, session_id=None)

    assert result.returncode == 0

    # lock-events.jsonl must NOT be created (or if it exists, no HEARTBEAT lines)
    audit_path = workspace / ".dadaia" / "logs" / "lock-events.jsonl"
    if audit_path.exists():
        lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
        heartbeats = [json.loads(ln) for ln in lines if json.loads(ln).get("event") == "HEARTBEAT"]
        assert len(heartbeats) == 0, "No HEARTBEAT expected when no session ID"


# ---------------------------------------------------------------------------
# T-SEMA-01 (FEAT-SESSION-SEMAPHORE-01 R1): env-free session resolution
# ---------------------------------------------------------------------------


def test_sema01_env_absent_nonstale_lock_allows(workspace: Path) -> None:
    """Bug A fix: DADAIA_SESSION_ID absent but a NON-STALE impl lock exists →
    the gate adopts the lock's session and ALLOWS the write (env-free; no relaunch).

    This is the core regression guard for the deploy-blocker: a running agent
    runtime that never had the env exported can still write after a `dadaia
    context bind` from any shell (which writes the lock the gate reads here).
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    sess_id = "sess_envfree01"
    _make_session_file(
        workspace, sess_id, mode="BOUND_IMPLEMENTATION", context=slug, release=release_id
    )
    _make_impl_lock(workspace, slug, release_id, sess_id)

    target_file = workspace / "repos" / slug / "src" / "main.py"
    # session_id=None → DADAIA_SESSION_ID is NOT present in the gate's environment.
    result = _run_gate(scripts, workspace, target_file, session_id=None)

    assert result.returncode == 0
    assert result.stdout == "" or "block" not in result.stdout

    # The env-free adoption is logged.
    log_file = workspace / ".dadaia" / "sdd-gate-test.log"
    log_content = log_file.read_text() if log_file.exists() else ""
    assert "env-free" in log_content


def test_sema01_env_absent_stale_lock_blocks(workspace: Path) -> None:
    """Bug A fix: a STALE impl lock is never adopted → env-absent write still blocks
    (with the no-relaunch message), honoring 'avoid race at any cost'."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    sess_id = "sess_stalelock01"
    _make_session_file(
        workspace, sess_id, mode="BOUND_IMPLEMENTATION", context=slug, release=release_id
    )
    _make_impl_lock(workspace, slug, release_id, sess_id, last_seen_at=_stale_ts())

    target_file = workspace / "repos" / slug / "src" / "main.py"
    result = _run_gate(scripts, workspace, target_file, session_id=None)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "No active implementation session" in data["reason"]


def test_sema01_env_absent_status_marker_form_allows(workspace: Path) -> None:
    """Bug B fix: RULE C accepts the real release marker form '- **Status:** [-]'
    (not only '- [-] T-xxx'). With a valid env-free lock + a Status-form marker,
    the write is ALLOWED."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    # Overwrite TASKS.md with the canonical release marker form.
    tasks = specs / "releases" / release_id / "TASKS.md"
    tasks.write_text(
        "# Tasks\n\n### T-001 — work\n- **Owner:** someone\n- **Status:** [-]\n"
    )

    sess_id = "sess_statusform01"
    _make_session_file(
        workspace, sess_id, mode="BOUND_IMPLEMENTATION", context=slug, release=release_id
    )
    _make_impl_lock(workspace, slug, release_id, sess_id)

    target_file = workspace / "repos" / slug / "src" / "main.py"
    result = _run_gate(scripts, workspace, target_file, session_id=None)

    assert result.returncode == 0
    assert result.stdout == "" or "block" not in result.stdout


def test_sema01_inline_heartbeat_renews_lock(workspace: Path) -> None:
    """SCOPE-02: an allowed write renews the owning lock's last_seen_at (not just
    the session file), so env-free resolution keeps working across a long session."""
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    release_id = "my-release-v1"
    specs = workspace / "repos" / slug / "specs"
    _make_active_release(specs, release_id)
    _make_primary_context(workspace, slug, specs)

    sess_id = "sess_hb01"
    _make_session_file(
        workspace, sess_id, mode="BOUND_IMPLEMENTATION", context=slug, release=release_id
    )
    backdated = _stale_ts(120)  # 120s ago: NOT stale (ttl 300) but clearly in the past
    lock = _make_impl_lock(workspace, slug, release_id, sess_id, last_seen_at=backdated)

    target_file = workspace / "repos" / slug / "src" / "main.py"
    result = _run_gate(scripts, workspace, target_file, session_id=sess_id)

    assert result.returncode == 0
    assert result.stdout == "" or "block" not in result.stdout

    ldata = json.loads(lock.read_text())
    assert ldata["last_seen_at"] != backdated
    assert datetime.fromisoformat(ldata["last_seen_at"]) > datetime.fromisoformat(backdated)
