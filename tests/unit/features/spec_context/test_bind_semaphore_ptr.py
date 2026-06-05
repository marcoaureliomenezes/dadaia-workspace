"""Unit tests for T-R1-05: semaphore + runtime ptr wired into dadaia context bind.

Tests verify the acceptance criteria:
- acquire-on-impl-bind: bind --mode implementation acquires the context semaphore.
- no-acquire-on-read/spec: bind --mode read/spec does NOT acquire semaphore.
- second-holder-denied-naming-holder: second impl bind denied with holder named.
- ptr-registered: bind registers runtime→session pointer at .dadaia/sessions/runtime/<sid>.ptr.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def _register_alive_ctx(workspace: Path, name: str = "myctx") -> None:
    """Register an ALIVE v2 context directly in spec_contexts.json."""
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


def _extract_session_id(output: str) -> str:
    """Extract session_id from bind output lines."""
    for line in output.strip().split("\n"):
        if "DADAIA_SESSION_ID" in line:
            return line.split("=")[1].strip()
    raise ValueError(f"No DADAIA_SESSION_ID in output: {output!r}")


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# AC-1: acquire semaphore on implementation bind
# ---------------------------------------------------------------------------


def test_tr105_impl_bind_acquires_semaphore(workspace: Path) -> None:
    """AC-1: bind --mode implementation acquires the context semaphore."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result.exit_code == 0, result.output

    sem_path = workspace / ".dadaia" / "states" / "ctx_locks" / "myctx.semaphore.json"
    assert sem_path.exists(), f"Semaphore file should exist at {sem_path}"

    data = json.loads(sem_path.read_text())
    assert data["phase"] in ("BOUND_IMPLEMENTATION", "IMPLEMENTATION")
    assert "owner" in data
    assert data["release"] == "v1"


# ---------------------------------------------------------------------------
# AC-2: read/spec phases do NOT acquire semaphore
# ---------------------------------------------------------------------------


def test_tr105_read_bind_no_semaphore(workspace: Path) -> None:
    """AC-2a: bind --mode read does NOT write a semaphore file."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output

    sem_path = workspace / ".dadaia" / "states" / "ctx_locks" / "myctx.semaphore.json"
    assert not sem_path.exists(), "bind --mode read must NOT write a semaphore file"


def test_tr105_spec_bind_no_semaphore(workspace: Path) -> None:
    """AC-2b: bind --mode spec does NOT write a semaphore file."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "spec"])
    assert result.exit_code == 0, result.output

    sem_path = workspace / ".dadaia" / "states" / "ctx_locks" / "myctx.semaphore.json"
    assert not sem_path.exists(), "bind --mode spec must NOT write a semaphore file"


# ---------------------------------------------------------------------------
# AC-3: second holder denied and holder named in error
# ---------------------------------------------------------------------------


def test_tr105_second_impl_bind_denied_naming_holder(workspace: Path) -> None:
    """AC-3: second impl bind is denied; error names the first holder's session id."""
    _register_alive_ctx(workspace)

    # First bind
    result1 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result1.exit_code == 0, result1.output
    first_session_id = _extract_session_id(result1.output)

    # Second bind — must be denied
    result2 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result2.exit_code != 0, "Second impl bind must be denied"

    combined = (result2.output or "") + (result2.stderr or "")
    # The error must name the holder
    assert first_session_id in combined, (
        f"Error must name holder '{first_session_id}'. Got: {combined!r}"
    )


def test_tr105_review_bind_denied_when_semaphore_held(workspace: Path) -> None:
    """AC-3b: bind --mode review is denied when impl semaphore is held."""
    _register_alive_ctx(workspace)

    # Implementation bind first
    result1 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result1.exit_code == 0, result1.output

    # Review bind — may be denied by semaphore or by the lock XOR check
    result2 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "review", "--release", "v1"]
    )
    assert result2.exit_code != 0, "Review bind must be denied when impl lock is held"


# ---------------------------------------------------------------------------
# AC-4: runtime ptr registered on bind
# ---------------------------------------------------------------------------


def test_tr105_impl_bind_registers_runtime_ptr(workspace: Path) -> None:
    """AC-4: bind --mode implementation writes a runtime→session pointer file."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result.exit_code == 0, result.output
    session_id = _extract_session_id(result.output)

    ptr_file = workspace / ".dadaia" / "sessions" / "runtime" / f"{session_id}.ptr"
    assert ptr_file.exists(), f"Runtime ptr file should exist at {ptr_file}"
    content = ptr_file.read_text().strip()
    assert content == session_id, f"Ptr file should contain '{session_id}', got: {content!r}"


def test_tr105_read_bind_registers_runtime_ptr(workspace: Path) -> None:
    """AC-4b: bind --mode read also writes a runtime→session pointer file (for gate resolution)."""
    _register_alive_ctx(workspace)
    result = _runner.invoke(app, ["context", "bind", "myctx", "--mode", "read"])
    assert result.exit_code == 0, result.output
    session_id = _extract_session_id(result.output)

    ptr_file = workspace / ".dadaia" / "sessions" / "runtime" / f"{session_id}.ptr"
    assert ptr_file.exists(), f"Runtime ptr file should exist at {ptr_file} even for read bind"


# ---------------------------------------------------------------------------
# T-SHIP-03 Finding 2: impl lock is rolled back when the semaphore denies the bind
# ---------------------------------------------------------------------------


def test_tr105_impl_lock_rolled_back_on_semaphore_denial(workspace: Path) -> None:
    """A second impl bind on the same context but a DIFFERENT release creates its
    own per-release impl lock, then is denied by the per-context semaphore. The
    just-created impl lock must be rolled back so a failed bind never orphans a
    lock (T-SHIP-03 Finding 2)."""
    _register_alive_ctx(workspace)

    # First holder: takes the per-context semaphore + impl lock for v1.
    result1 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v1"]
    )
    assert result1.exit_code == 0, result1.output

    # Second bind for a different release: its v2 impl lock is created, then the
    # per-context semaphore (held by the first holder) denies the bind.
    result2 = _runner.invoke(
        app, ["context", "bind", "myctx", "--mode", "implementation", "--release", "v2"]
    )
    assert result2.exit_code != 0, "Second impl bind (different release) must be denied"

    locks = workspace / ".dadaia" / "locks" / "implementation"
    assert not (locks / "myctx__v2.json").exists(), (
        "Impl lock for the denied bind must be rolled back, not orphaned"
    )
    assert (locks / "myctx__v1.json").exists(), "First holder's impl lock must remain intact"
