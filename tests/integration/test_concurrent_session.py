"""T-R1-07: E2E concurrent-session denial and write-gate enforcement.

Acceptance criteria:
  - Two sessions attempt to bind the SAME context in implementation mode.
  - The second bind is DENIED and names the first holder's session id (semaphore).
  - While the first session holds the lock, a write-gate run for that session
    is allowed (decision=allow); a write-gate run with an unknown session id is
    blocked (decision=block).
  - After the first session releases, a fresh third session can bind
    successfully.

Design: uses the Typer CLI runner for bind/release and invokes sdd-spec-gate.sh
as a subprocess to verify gate enforcement — matching the integration-test
patterns established in test_gate_session_locks.py and
test_bind_semaphore_ptr.py.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_PKG_SCRIPTS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "scripts"
SDD_GATE = _PKG_SCRIPTS / "sdd-spec-gate.sh"
POST_GATE = _PKG_SCRIPTS / "sdd-post-gate.sh"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Initialise a minimal dadaia workspace in a temp directory.

    Uses WorkspaceService.init to create a valid workspace tree, then registers
    an ALIVE spec-context 'myctx' directly in spec_contexts.json (no git clone
    needed — gate tests only require the JSON + script files).
    """
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)

    # Register a minimal ALIVE context
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": "myctx",
                        "state": "alive",
                        "repo_slug": "myctx",
                        "repo_url": "https://example.com/myctx.git",
                        "created_at": "2026-01-01T00:00:00Z",
                        "alive_since": "2026-01-01T00:00:00Z",
                        "dead_since": None,
                        "current_branch": "main",
                    }
                ],
            }
        )
    )

    # Create the repos/myctx directory with a minimal specs tree so the gate
    # can resolve ACTIVE.md and TASKS.md.
    ctx_specs = tmp_path / "repos" / "myctx" / "specs"
    rel_dir = ctx_specs / "releases" / "v1"
    rel_dir.mkdir(parents=True)
    (ctx_specs / "releases" / "ACTIVE.md").write_text("release: v1\nphase: IMPLEMENTATION\n")
    (rel_dir / "TASKS.md").write_text("# Tasks\n\n- [-] T-001 — work in progress\n")

    # Copy shell scripts into .dadaia/scripts/ where the gate resolves them
    scripts_dest = tmp_path / ".dadaia" / "scripts"
    scripts_dest.mkdir(parents=True, exist_ok=True)
    for src in (SDD_GATE, POST_GATE):
        shutil.copy2(src, scripts_dest / src.name)
        (scripts_dest / src.name).chmod(0o755)

    return tmp_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_session_id(output: str) -> str:
    """Extract session_id from bind output lines."""
    for line in output.strip().split("\n"):
        if "DADAIA_SESSION_ID" in line:
            return line.split("=")[1].strip()
    raise ValueError(f"No DADAIA_SESSION_ID in output: {output!r}")


def _run_gate(
    workspace: Path,
    target_file: Path,
    *,
    session_id: str | None = None,
) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    """Run sdd-spec-gate.sh for a Write to target_file."""
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace)}
    if session_id is not None:
        env["DADAIA_SESSION_ID"] = session_id
    log_file = workspace / ".dadaia" / "sdd-gate-test.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env["SDD_GATE_LOG"] = str(log_file)
    return subprocess.run(
        ["bash", str(workspace / ".dadaia" / "scripts" / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


# ---------------------------------------------------------------------------
# T-R1-07 tests
# ---------------------------------------------------------------------------


def test_concurrent_second_bind_denied_naming_holder(workspace: Path) -> None:
    """Two impl binds on the same context: second is denied and names first holder."""
    runner = CliRunner()

    # First bind — must succeed
    result1 = runner.invoke(
        app,
        ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"],
    )
    assert result1.exit_code == 0, f"First bind failed: {result1.output}"
    first_session_id = _extract_session_id(result1.output)

    # Second bind — must be denied
    result2 = runner.invoke(
        app,
        ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"],
    )
    assert result2.exit_code != 0, (
        f"Second bind must be denied; exit={result2.exit_code}; output={result2.output!r}"
    )

    # Error message must name the first holder
    combined = (result2.output or "") + (result2.stderr or "")
    assert first_session_id in combined, (
        f"Denial message must name holder '{first_session_id}'. Got: {combined!r}"
    )


def test_first_session_can_write_second_session_is_blocked(workspace: Path) -> None:
    """First-session gate allows write; intruder session (no lock) is blocked."""
    runner = CliRunner()

    # Bind first session
    result1 = runner.invoke(
        app,
        ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"],
    )
    assert result1.exit_code == 0, f"First bind failed: {result1.output}"
    first_session_id = _extract_session_id(result1.output)

    # Target production file (inside the context's repo)
    target = workspace / "repos" / "myctx" / "src" / "main.py"

    # Gate for first (holder) session: must allow.
    # The gate exits 0 with EMPTY stdout on allow (no JSON emitted); it only
    # emits {"decision":"block",...} JSON on block.  An empty stdout + rc=0
    # is the canonical allow signal — see gate implementation and
    # test_gate_session_locks.py pattern.
    gate_ok = _run_gate(workspace, target, session_id=first_session_id)
    assert gate_ok.returncode == 0, f"Gate shell error: {gate_ok.stderr}"
    assert gate_ok.stdout.strip() == "", (
        f"First session write should be allowed (empty stdout); got: {gate_ok.stdout!r}"
    )

    # Gate for an intruder with no lock or session file: must block.
    gate_block = _run_gate(workspace, target, session_id="sess_intruder_T_R1_07")
    assert gate_block.returncode == 0, f"Gate shell error: {gate_block.stderr}"
    gate_block_data = json.loads(gate_block.stdout)
    assert gate_block_data["decision"] == "block", (
        f"Intruder write should be blocked; got {gate_block_data!r}"
    )


def test_release_first_allows_third_session_to_bind(workspace: Path) -> None:
    """After first session releases, a new third session can bind successfully."""
    runner1 = CliRunner()
    runner_rel = CliRunner()
    runner3 = CliRunner()

    # Bind first session
    result1 = runner1.invoke(
        app,
        ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"],
    )
    assert result1.exit_code == 0, f"First bind failed: {result1.output}"
    first_session_id = _extract_session_id(result1.output)

    # Confirm second bind is denied
    runner2 = CliRunner()
    result2 = runner2.invoke(
        app,
        ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"],
    )
    assert result2.exit_code != 0, "Second bind must be denied while first holds lock"

    # Release first session: invoke with DADAIA_SESSION_ID set
    result_rel = runner_rel.invoke(
        app,
        ["context", "release"],
        env={"DADAIA_SESSION_ID": first_session_id},
    )
    assert result_rel.exit_code == 0, f"Release failed: {result_rel.output}"

    # Third session bind — must now succeed
    result3 = runner3.invoke(
        app,
        ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"],
    )
    assert result3.exit_code == 0, (
        f"Third bind after release should succeed; output={result3.output!r}"
    )
    _extract_session_id(result3.output)  # confirm we got a valid session id
