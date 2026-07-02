"""Master lifecycle journey E2E — the ONE narrative chain (v0.1.51 FR1 / AC-1).

Chains what the isolated probes prove separately, as production composes it:

    context create → context alive (real clone) → context bind (real subprocess,
    own minted sid) → ctx_inject (second subprocess, DIFFERENT sid, attributed via
    the bind-epoch ancestry marker) → pre_gate MUTATING write acquires the lease →
    a foreign-sid MUTATING attempt is blocked (no-steal).

`tests/e2e/test_two_actor_lease.py` proves lease no-steal in isolation and
`tests/e2e/features/test_ctx_inject_bind_boundary.py` proves the bind→inject cross-sid
boundary in isolation; NEITHER chains the composition, so a regression in how bind
attribution feeds injection feeds the gate is invisible to them. This journey asserts
the COMPOSITION, not new mechanics: if a step fails here while the isolated probes
stay green, that composition seam is the suspect (register a bug — test-only release,
never an inline fix).

Sandboxing: everything lives under ``tmp_path`` — a hand-assembled minimal workspace
(NEVER a real venv build) and a local bare git remote for the clone; no network, no
live-workspace state. Every actor is a bounded ``subprocess.run`` (its own deadline);
no ``time.sleep`` anywhere.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

_JOURNEY_CTX = "journey"
_GATE_SID = "s-journey-hook"
_FOREIGN_SID = "s-journey-intruder"


def _git(cwd: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-c", "user.email=e2e@test", "-c", "user.name=e2e", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60.0,
    )
    assert proc.returncode == 0, f"git {args}: {proc.stderr or proc.stdout}"


def _seed_bare_remote(tmp_path: Path) -> Path:
    """Build a local bare remote whose clone carries the context's specs tree.

    The clone is what ``context alive`` materializes under ``repos/<slug>/`` — it must
    already contain the memory tree ctx_inject injects from and an ACTIVE.md for the
    gate's phase read.
    """
    seed = tmp_path / "remote-seed"
    (seed / "specs" / "memory" / "product").mkdir(parents=True)
    (seed / "specs" / "releases").mkdir(parents=True)
    (seed / "specs" / "memory" / "tech-stack.md").write_text(
        "# tech journey\nPython 3.12 JOURNEY-MARKER\n", encoding="utf-8"
    )
    (seed / "specs" / "memory" / "product" / "catalog.json").write_text(
        '{"features": []}', encoding="utf-8"
    )
    (seed / "specs" / "releases" / "ACTIVE.md").write_text(
        "---\nrelease: v0-journey\nphase: IMPLEMENTATION\n---\n", encoding="utf-8"
    )
    _git(seed, "-c", "init.defaultBranch=main", "init")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-m", "seed: journey context specs tree")

    bare = tmp_path / "remote.git"
    _git(tmp_path, "clone", "--bare", str(seed), str(bare))
    return bare


def _cli(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a real ``dadaia`` CLI verb as its own process (own minted sid on bind)."""
    proc = subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", *args],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=120.0,
    )
    return proc


def _inject(workspace: Path, session_id: str) -> str:
    """ctx_inject as a real subprocess; sid arrives via the stdin field (harness-real)."""
    env = claude_hook_env(workspace, session_id="harness-native-ignored")
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    result = run_hook_subprocess("ctx_inject", {"session_id": session_id}, env)
    assert result.returncode == 0, result.stderr
    return result.stdout


def _gate(workspace: Path, session_id: str, file_path: Path):  # type: ignore[no-untyped-def]
    """pre_gate as a real subprocess for a MUTATING Write payload."""
    env = claude_hook_env(workspace, session_id=session_id)
    payload = {
        "session_id": session_id,
        "tool_name": "Write",
        "tool_input": {"file_path": str(file_path)},
        "cwd": str(workspace),
    }
    return run_hook_subprocess("pre_gate", payload, env)


def test_master_lifecycle_journey_create_alive_bind_inject_gate(tmp_path: Path) -> None:
    """AC-1: the full chain in ONE narrative path, real subprocesses at every seam."""
    workspace = tmp_path / "ws"
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True)
    # The workspace-root sentinel (resolve_workspace_root walks up to it): an empty
    # v2 registry, the same minimal shape the bind-boundary e2e hand-builds.
    (states / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}', encoding="utf-8"
    )
    remote = _seed_bare_remote(tmp_path)

    # 1) create — registers the context (DEAD, no clone) in spec_contexts.json.
    create = _cli(
        workspace,
        "context",
        "create",
        _JOURNEY_CTX,
        "--repo",
        _JOURNEY_CTX,
        "--url",
        str(remote),
    )
    assert create.returncode == 0, create.stderr or create.stdout
    registry = workspace / ".dadaia" / "states" / "spec_contexts.json"
    assert registry.is_file(), "context create must persist the registry"

    # 2) alive — REAL clone from the local bare remote into repos/<slug>/.
    alive = _cli(workspace, "context", "alive", _JOURNEY_CTX)
    assert alive.returncode == 0, alive.stderr or alive.stdout
    cloned_marker = workspace / "repos" / _JOURNEY_CTX / "specs" / "memory" / "tech-stack.md"
    assert cloned_marker.is_file(), "alive must materialize the context's specs tree"

    # 3) fresh hook session — generic preflight only (stamps the sentinel; DP-2: a
    #    pre-existing marker never binds a fresh session), ALIVE list names the context.
    fresh = _inject(workspace, _GATE_SID)
    assert "[no bound context]" in fresh
    assert f"- {_JOURNEY_CTX}" in fresh
    assert "JOURNEY-MARKER" not in fresh

    # 4) bind — real subprocess, own minted sid; writes the bind-epoch ancestry marker
    #    NEWER than the hook session's sentinel.
    bind = _cli(
        workspace,
        "context",
        "bind",
        _JOURNEY_CTX,
        "--mode",
        "implementation",
        "--release",
        "v0-journey",
    )
    assert bind.returncode == 0, bind.stderr or bind.stdout
    marker = workspace / ".dadaia" / "states" / "bind_epoch" / _JOURNEY_CTX
    assert marker.is_file(), "bind must write the bind-epoch marker"
    assert marker.read_text(encoding="utf-8").strip(), "marker must carry the ancestry chain"

    # 5) inject — SECOND subprocess, DIFFERENT sid: the bound context's memory arrives
    #    across the process boundary via marker attribution (not a session record).
    injected = _inject(workspace, _GATE_SID)
    assert f"[{_JOURNEY_CTX}]" in injected
    assert "JOURNEY-MARKER" in injected
    assert "end memory bootstrap" in injected

    # 6) gate — a MUTATING write by the journey session ALLOWs and acquires the lease.
    target = workspace / "repos" / _JOURNEY_CTX / "src" / "app.py"
    allowed = _gate(workspace, _GATE_SID, target)
    assert allowed.returncode == 0, allowed.stderr
    assert allowed.block_envelope() is None, allowed.stdout

    lock_path = workspace / ".dadaia" / "states" / "ctx_locks" / f"{_JOURNEY_CTX}.lock.json"
    assert lock_path.is_file(), "the MUTATING allow must have acquired the lease"
    record = json.loads(lock_path.read_text(encoding="utf-8"))
    assert record["context"] == _JOURNEY_CTX
    assert record["session_id"] == _GATE_SID

    # 7) no-steal — a foreign sid's MUTATING attempt against the live holder is blocked
    #    and the holder's record survives untouched.
    blocked = _gate(workspace, _FOREIGN_SID, target)
    envelope = blocked.block_envelope()
    assert envelope is not None, (
        f"foreign MUTATING attempt must be blocked; stdout={blocked.stdout!r} "
        f"stderr={blocked.stderr!r}"
    )
    surviving = json.loads(lock_path.read_text(encoding="utf-8"))
    assert surviving["session_id"] == _GATE_SID, "no-steal: holder record must survive"
