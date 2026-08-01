"""Two sessions working the same context at the same time; neither waits for the other.

The operator's requirement in their own words: *no locks, no infinite tasks*. The
NO-LOCKS doctrine is covered at the hook level in
``tests/unit/hooks/test_gate_never_blocks_doctrine.py`` — eight tests over presence,
advisory warnings and mode resolution — but those call the hook directly. What the
operator does is run a WORKFLOW while another session is running one, and nothing in the
suite drove that.

The distinction is not academic. Round 25 was refused outright by the validator with "há um
`codex exec` concorrente persistente no workspace … para respeitar a serialização exigida,
não executei o Passo 0" — an invented serialization rule, blocking on a process that was
already dead. The doctrine held everywhere it was tested and the behaviour still appeared
where it was not.

Two real subprocesses, two distinct session identities, one context, launched together.
Both must finish, and each must leave its own work on disk: isolation comes from disjoint
write sets, never from waiting.
"""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.e2e

_runner = CliRunner()
_CTX = "concctx"
_REPO = "concrepo"
_DADAIA = Path("/home/ubuntu/workspace/.dadaia/.venv/bin/dadaia")


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    repo = tmp_path / "repos" / _REPO
    repo.mkdir(parents=True)
    for args in (
        ["init", "-q"],
        ["config", "user.email", "e2e@test"],
        ["config", "user.name", "e2e"],
        ["commit", "-q", "--allow-empty", "-m", "init"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DADAIA_SESSION_ID", "e2e-conc-setup")
    assert (
        _runner.invoke(
            app, ["context", "create", _CTX, "--repo", _REPO, "--url", str(repo)]
        ).exit_code
        == 0
    )
    assert _runner.invoke(app, ["context", "alive", _CTX]).exit_code == 0
    return tmp_path


@pytest.mark.skipif(not _DADAIA.is_file(), reason="workspace venv console script not present")
def test_two_concurrent_sessions_on_one_context_both_finish(workspace: Path) -> None:
    outcomes: dict[str, tuple[int, str]] = {}

    def drive(session_id: str, run_id: str) -> None:
        env = {**os.environ, "DADAIA_SESSION_ID": session_id}
        proc = subprocess.run(
            [str(_DADAIA), "lifecycle", "backlog-definition",
             "--context", _CTX, "--release-id", "v0.1.0", "--run-id", run_id,
             "--harness", "fake", "--demand", f"demand from {session_id}"],
            cwd=workspace, env=env, capture_output=True, text=True, timeout=300,
        )  # fmt: skip
        outcomes[session_id] = (proc.returncode, proc.stdout + proc.stderr)

    first = threading.Thread(target=drive, args=("session-a", "bd-a"))
    second = threading.Thread(target=drive, args=("session-b", "bd-b"))
    first.start()
    second.start()
    first.join(timeout=310)
    second.join(timeout=310)

    assert set(outcomes) == {"session-a", "session-b"}, (
        f"a session never returned — that is the infinite task: {sorted(outcomes)}"
    )
    for session_id, (code, output) in sorted(outcomes.items()):
        assert code == 0, f"{session_id} did not complete:\n{output}"
        assert "LockHeldError" not in output, f"{session_id} hit a lock:\n{output}"

    items = {
        path.stem
        for path in (workspace / "repos" / _REPO / "specs" / "backlog").glob("*.md")
        if path.stem != "README"
    }
    assert len(items) == 2, (
        "each session must leave its OWN work on disk — one item means the sessions "
        f"collided rather than working disjoint sets: {sorted(items)}"
    )
