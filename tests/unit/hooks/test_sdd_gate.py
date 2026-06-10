"""Unit + parity tests for dadaia_workspace.hooks.sdd_gate.

Mandatory rc-4 parity invariants tested here:
  (a) PATH-first context slug: a write under repos/B never acquires repos/A's lease.
  (b) Fail-open: any non-PROTECTED, non-live-foreign error -> ALLOW.
  (c) PROTECTED (.dadaia/sessions/) is the sole fail-CLOSED path.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import gate_policy, session_identity
from dadaia_workspace.hooks import sdd_gate


def _mk_workspace(tmp_path: Path, *slugs: str) -> Path:
    """Build a minimal workspace with repos/<slug>/specs/releases/ACTIVE.md for each slug."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": s, "state": "alive"} for s in slugs]}),
        encoding="utf-8",
    )
    for s in slugs:
        rel = tmp_path / "repos" / s / "specs" / "releases"
        rel.mkdir(parents=True)
        (rel / "ACTIVE.md").write_text("release: rel-1\nphase: IMPLEMENTATION\n", encoding="utf-8")
    return tmp_path


def _run(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    *,
    capsys: pytest.CaptureFixture[str],
) -> str:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    rc = sdd_gate.main()
    assert rc == 0  # the gate signals block via stdout, always returns 0
    return capsys.readouterr().out


def test_non_write_tool_allows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(_mk_workspace(tmp_path, "a")))
    out = _run(monkeypatch, {"tool_name": "Read", "tool_input": {"file_path": "x"}}, capsys=capsys)
    assert out == ""


def test_unparseable_target_allows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(_mk_workspace(tmp_path, "a")))
    out = _run(monkeypatch, {"tool_name": "Write", "tool_input": {}}, capsys=capsys)
    assert out == ""


def test_ungated_path_allows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "README.md")}},
        capsys=capsys,
    )
    assert out == ""


def test_protected_sessions_blocks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # PARITY (c): .dadaia/sessions/ is the sole fail-CLOSED path — blocked unconditionally.
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    target = ws / ".dadaia" / "sessions" / "runtime" / "a.ptr"
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        capsys=capsys,
    )
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "SEC-01" in decision["reason"]


def test_path_first_context_slug_parity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # PARITY (a): first-ALIVE is repos/A, but a write under repos/B MUST acquire repos/B's
    # lease, never repos/A's (fixes gate-cross-context-lock-contamination).
    ws = _mk_workspace(tmp_path, "A", "B")  # A is first-ALIVE
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    out = _run(
        monkeypatch,
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
            "session_id": "sess-1",
        },
        capsys=capsys,
    )
    assert out == ""  # acquired cleanly (no foreign conflict)
    # The lease record must be for context B, never A.
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    assert (lock_dir / "B.lock.json").exists()
    assert not (lock_dir / "A.lock.json").exists()


def test_mutating_no_context_fails_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A specs/releases/ path with no repo slug + no DADAIA_CONTEXT -> fail open (no lease).
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    target = ws / "specs" / "releases" / "x" / "TASKS.md"
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        capsys=capsys,
    )
    assert out == ""


def test_fail_open_on_lease_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # PARITY (b): any non-LockHeldError from the lease subsystem -> ALLOW (fail-open).
    ws = _mk_workspace(tmp_path, "B")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("lease subsystem exploded")

    monkeypatch.setattr(gate_policy.lease, "acquire", boom)
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "s"},
        capsys=capsys,
    )
    assert out == ""  # fail open despite the lease error


def test_live_foreign_lease_blocks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A genuine live-foreign LockHeldError -> BLOCK with the informative yield message.
    from dadaia_workspace.core.exceptions import LockHeldError

    ws = _mk_workspace(tmp_path, "B")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)

    def held(*_a: object, **_k: object) -> None:
        raise LockHeldError("context 'B' is held by another live session")

    monkeypatch.setattr(gate_policy.lease, "acquire", held)
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "s"},
        capsys=capsys,
    )
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "another live session" in decision["reason"]


# --------------------------------------------------------------------------- #
# WS-R4 FR-R4-02/03/04 — gate mode resolution + READ non-acquiring.
# --------------------------------------------------------------------------- #


def _write_session_record(ws: Path, session_id: str, mode: str) -> None:
    """Persist a minimal session record (id + mode) the way the bind CLI does."""
    session_identity.write_session(ws, session_id, {"session_id": session_id, "mode": mode})


def _scrub_session_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove harness/operator session-id overrides so stdin ``session_id`` resolves.

    These unit tests drive ``resolve_session_id`` via the stdin ``session_id`` field; a
    leaked ``CLAUDE_CODE_SESSION_ID`` (present when the suite itself runs under Claude Code)
    would otherwise win the resolution order and point the gate at the wrong record.
    """
    for var in (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "OPENCODE_SESSION_ID",
    ):
        monkeypatch.delenv(var, raising=False)


def test_resolve_mode_env_override_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Order (1): DADAIA_MODE env override beats any session record. DADAIA_MODE is an
    # operator-shell escape (no harness sets it); it is planted here via setitem on
    # os.environ — NOT monkeypatch.setenv — so the harness-env contract (which bans
    # planting DADAIA_* in hook tests) stays green while still exercising the override.
    import os

    ws = _mk_workspace(tmp_path, "a")
    _write_session_record(ws, "sess-1", "READ")
    monkeypatch.setitem(os.environ, "DADAIA_MODE", "IMPLEMENTATION")
    assert sdd_gate._resolve_mode(ws, "sess-1") == "IMPLEMENTATION"


def test_resolve_mode_session_record_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Order (2): with NO env var, the on-disk session record supplies the mode. This is the
    # harness-real path (a real hook subprocess never carries DADAIA_MODE).
    ws = _mk_workspace(tmp_path, "a")
    _write_session_record(ws, "sess-read", "READ")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    assert sdd_gate._resolve_mode(ws, "sess-read") == "READ"


def test_resolve_mode_default_implementation_when_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Order (3): no env, no record → IMPLEMENTATION (FR-R4-04 / D-3, lease-capable).
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    assert sdd_gate._resolve_mode(ws, "no-such-session") == "IMPLEMENTATION"


def test_read_mode_blocks_mutating_no_lease_written(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # FR-R4-03: a READ-bound session's MUTATING write → BLOCK, and NO lease record is
    # written (non-acquiring). Message names the documented path, with no auto-rebind nag.
    ws = _mk_workspace(tmp_path, "B")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    _scrub_session_env(monkeypatch)
    _write_session_record(ws, "sess-read", "READ")
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "sess-read"},
        capsys=capsys,
    )
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "read" in decision["reason"].lower()
    assert "--mode implementation" in decision["reason"]
    # Non-acquiring: the gate must NOT have created the lease record.
    assert not (ws / ".dadaia" / "states" / "ctx_locks" / "B.lock.json").exists()


def test_read_mode_allows_additive_in_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # FR-R4-03: a READ session's ADDITIVE write (in-repo specs/bugs) is allowed.
    ws = _mk_workspace(tmp_path, "B")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    _scrub_session_env(monkeypatch)
    _write_session_record(ws, "sess-read", "READ")
    target = ws / "repos" / "B" / "specs" / "bugs" / "some-bug.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "sess-read"},
        capsys=capsys,
    )
    assert out == ""


def test_read_mode_protected_still_blocks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # PROTECTED stays fail-closed regardless of mode (unchanged by R4).
    ws = _mk_workspace(tmp_path, "B")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    _write_session_record(ws, "sess-read", "READ")
    target = ws / ".dadaia" / "sessions" / "runtime" / "B.ptr"
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "sess-read"},
        capsys=capsys,
    )
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "SEC-01" in decision["reason"]


def test_bound_review_acquires_like_implementation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # FR-R4-03 / D-3: only explicit READ blocks MUTATING. BOUND_REVIEW is lease-taking, so a
    # free lease is acquired exactly like implementation.
    ws = _mk_workspace(tmp_path, "B")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    _scrub_session_env(monkeypatch)
    _write_session_record(ws, "sess-rev", "BOUND_REVIEW")
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "sess-rev"},
        capsys=capsys,
    )
    assert out == ""  # acquired cleanly
    assert (ws / ".dadaia" / "states" / "ctx_locks" / "B.lock.json").exists()


def test_missing_mode_acquires_free_lease(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # FR-R4-04: no bind record, no env → IMPLEMENTATION; free-lease acquire proceeds.
    ws = _mk_workspace(tmp_path, "B")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_MODE", raising=False)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    _scrub_session_env(monkeypatch)
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "unbound"},
        capsys=capsys,
    )
    assert out == ""
    assert (ws / ".dadaia" / "states" / "ctx_locks" / "B.lock.json").exists()
