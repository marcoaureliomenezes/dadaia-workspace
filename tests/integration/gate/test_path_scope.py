"""Integration tests for gate path classification + precedence in sdd-spec-gate.sh.

0.1.7 rc-3 removed RULE D (the per-persona write-allowlist via agents.index.json). It
was fail-open and never fired for an agent (persona is never set in the hook process
environment), so it was a dormant latent lock. With it gone, a MUTATING write
(``specs/releases/**``, ``repos/<ctx>/**``) is governed only by the single-session
lease — the one deterministic lock the product keeps. ADDITIVE paths always flow;
MEMORY and FROZEN still decide before the lease.

These black-box tests invoke ``sdd-spec-gate.sh`` as a subprocess with controlled
stdin/env and assert on stdout (block JSON) and exit code.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_GATE = (
    Path(__file__).parent.parent.parent.parent
    / "dadaia_workspace"
    / "public"
    / "scripts"
    / "sdd-spec-gate.sh"
)


def _build_workspace(
    tmp_path: Path,
    active_phase: str = "TASKS",
    active_release: str = "test-release-v1",
    context_name: str = "dadaia-workspace",
) -> Path:
    """Minimal workspace: spec_contexts.json + bound-context ACTIVE.md."""
    # Bound-context ACTIVE.md lives under repos/<ctx>/specs (gate reads it there).
    rel_dir = tmp_path / "repos" / context_name / "specs" / "releases" / active_release
    rel_dir.mkdir(parents=True)
    (tmp_path / "repos" / context_name / "specs" / "releases" / "ACTIVE.md").write_text(
        f"release: {active_release}\nphase: {active_phase}\n", encoding="utf-8"
    )

    state_dir = tmp_path / ".dadaia" / "states"
    state_dir.mkdir(parents=True)
    (state_dir / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [{"name": context_name, "state": "alive", "repo_slug": context_name}],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def _run_gate(
    ws: Path,
    file_path: str,
    env_overrides: dict[str, str] | None = None,
    tool: str = "Write",
) -> tuple[str, int]:
    payload = {"tool_name": tool, "tool_input": {"file_path": file_path}}
    env = os.environ.copy()
    for key in (
        "DADAIA_AGENT_PERSONA",
        "CLAUDE_AGENT_PERSONA",
        "CODEX_AGENT_PERSONA",
        "OPENCODE_AGENT_PERSONA",
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
    ):
        env.pop(key, None)
    env["WORKSPACE_ROOT"] = str(ws)
    env["SDD_GATE_LOG"] = str(ws / "gate.log")
    # Distinct lease session per test → no cross-test live-lease interference.
    env["CLAUDE_CODE_SESSION_ID"] = f"sess-{abs(hash(file_path)) % 10**8}"
    if env_overrides:
        env.update(env_overrides)
    proc = subprocess.run(
        ["bash", str(_GATE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return proc.stdout, proc.returncode


def _blocked(stdout: str) -> bool:
    return '"decision": "block"' in stdout or '"decision":"block"' in stdout


# --- ADDITIVE paths always flow --------------------------------------------


def test_additive_report_path_allowed(tmp_path: Path) -> None:
    """An agent writing to ANY .dadaia/reports path is ALLOWED (ADDITIVE)."""
    ws = _build_workspace(tmp_path)
    out, _ = _run_gate(
        ws,
        ".dadaia/reports/other-agent/x.html",
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
    )
    assert not _blocked(out)


# --- MUTATING is governed only by the lease (RULE D removed) ----------------


def test_mutating_with_persona_allowed_no_allowlist(tmp_path: Path) -> None:
    """A MUTATING write with any persona is allowed — no per-persona allowlist deny."""
    ws = _build_workspace(tmp_path)
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/specs/releases/test-release-v1/SPEC.md",
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
    )
    assert not _blocked(out)
    assert "write_allowlist" not in out


def test_mutating_no_persona_allowed(tmp_path: Path) -> None:
    """No persona env → lease allows (fresh session)."""
    ws = _build_workspace(tmp_path)
    out, _ = _run_gate(ws, "repos/dadaia-workspace/specs/releases/test-release-v1/SPEC.md")
    assert not _blocked(out)


def test_mutating_repos_path_allowed(tmp_path: Path) -> None:
    """A write under repos/<ctx>/** is MUTATING and lease-allowed for a fresh session."""
    ws = _build_workspace(tmp_path)
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/dadaia_workspace/features/x.py",
        env_overrides={"DADAIA_AGENT_PERSONA": "software-engineer"},
    )
    assert not _blocked(out)


# --- precedence: MEMORY / FROZEN decide before the lease -------------------


def test_memory_atomicity_blocks(tmp_path: Path) -> None:
    """A memory write outside DEFINITION/CLOSURE is blocked regardless of persona."""
    ws = _build_workspace(tmp_path, active_phase="TASKS")
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/specs/memory/architecture.md",
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
    )
    assert _blocked(out)
    assert "memory/ is atomic" in out


def test_archive_path_blocked(tmp_path: Path) -> None:
    """A write under specs/_archive/ is FROZEN regardless of persona."""
    ws = _build_workspace(tmp_path)
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/specs/_archive/old.md",
        env_overrides={"DADAIA_AGENT_PERSONA": "software-engineer"},
    )
    assert _blocked(out)
    assert "_archive/ is read-only" in out


# --- the KEPT lock: single-session lease still BLOCKs a live foreign writer -----


def test_mutating_blocked_by_live_foreign_lease(tmp_path: Path) -> None:
    """rc-3 keeps exactly ONE deterministic lock: the single-session lease. Prove it
    end-to-end at the gate (black-box): a live FOREIGN session holding the context
    lease must BLOCK a second session's MUTATING write (yield-iff-live-foreign).

    Closes the coverage gap flagged in 0.1.7 rc-3 review (qa + code-reviewer): the
    surviving lock's block path had only unit-level coverage in test_lease_*.py.
    """
    ws = _build_workspace(tmp_path)
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.UTC).isoformat()
    (lock_dir / "dadaia-workspace.lock.json").write_text(
        json.dumps(
            {
                "context": "dadaia-workspace",
                "release": "test-release-v1",
                "session_id": "foreign-holder-9999",
                "mode": "IMPLEMENTATION",
                "acquired_at": now,
                "heartbeat": now,  # fresh → live within TTL
                "ttl": 120,
            }
        ),
        encoding="utf-8",
    )
    # A DIFFERENT session attempts a MUTATING write → blocked by the live foreign lease.
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/specs/releases/test-release-v1/SPEC.md",
        env_overrides={"CLAUDE_CODE_SESSION_ID": "my-other-session-0001"},
    )
    assert _blocked(out), f"expected MUTATING block by live foreign lease, got: {out!r}"


def test_mutating_renews_for_lease_holder(tmp_path: Path) -> None:
    """The lease holder is never self-blocked: same session id RENEWs (ALLOW)."""
    ws = _build_workspace(tmp_path)
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    runtime = ws / ".dadaia" / "sessions" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.UTC).isoformat()
    holder = "incumbent-session-0001"
    (lock_dir / "dadaia-workspace.lock.json").write_text(
        json.dumps(
            {
                "context": "dadaia-workspace",
                "release": "test-release-v1",
                "session_id": holder,
                "mode": "IMPLEMENTATION",
                "acquired_at": now,
                "heartbeat": now,
                "ttl": 120,
            }
        ),
        encoding="utf-8",
    )
    (runtime / "dadaia-workspace.ptr").write_text(holder, encoding="utf-8")
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/specs/releases/test-release-v1/SPEC.md",
        env_overrides={"CLAUDE_CODE_SESSION_ID": holder},
    )
    assert not _blocked(out), f"holder must RENEW, not block; got: {out!r}"


# --- rc-4: context resolved from the write PATH → no cross-context contamination -----


def test_no_cross_context_lease_contamination(tmp_path: Path) -> None:
    """rc-4 / T-017-29 (fixes gate-cross-context-lock-contamination): a live lease held for
    context A must NOT block a MUTATING write to a DIFFERENT context B. The gate resolves the
    lease context from the write-target path (repos/<slug>/...), not from first-ALIVE.
    """
    ws = _build_workspace(tmp_path)  # bound/first-ALIVE context = dadaia-workspace
    # Seed a live foreign lease for a DIFFERENT context (the contaminator in the real bug).
    (ws / "repos" / "other-ctx" / "specs" / "releases" / "r1").mkdir(parents=True)
    (ws / "repos" / "other-ctx" / "specs" / "releases" / "ACTIVE.md").write_text(
        "release: r1\nphase: TASKS\n", encoding="utf-8"
    )
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.UTC).isoformat()
    (lock_dir / "other-ctx.lock.json").write_text(
        json.dumps(
            {
                "context": "other-ctx",
                "release": "r1",
                "session_id": "holder-of-other-ctx",
                "mode": "IMPLEMENTATION",
                "acquired_at": now,
                "heartbeat": now,
                "ttl": 120,
            }
        ),
        encoding="utf-8",
    )
    # Write to dadaia-workspace's repo while other-ctx is locked → must ALLOW (no cross-block).
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/specs/releases/test-release-v1/SPEC.md",
        env_overrides={"CLAUDE_CODE_SESSION_ID": "ws-session"},
    )
    assert not _blocked(out), f"cross-context write must NOT be blocked; got: {out!r}"
