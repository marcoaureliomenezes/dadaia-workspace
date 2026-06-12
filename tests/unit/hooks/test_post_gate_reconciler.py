"""Unit tests for the advisory working-tree reconciler (FR-W1-03, T-014-16).

NEVER-BLOCKS contract: every branch must (1) leave exit-allow, (2) emit only advisory
output, (3) fail open on error, (4) never mutate a lease. The git child is faked — no real
``git status`` runs, and the throttle is asserted to short-circuit BEFORE any spawn.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.spec_context import session_identity
from dadaia_workspace.hooks import sdd_post_gate

_SID = "session-recon"
_CTX = "demo-ctx"


def _make_workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (tmp_path / "repos" / _CTX).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _bind_session(workspace: Path, ctx: str = _CTX) -> None:
    session_identity.write_session(
        workspace,
        _SID,
        {"session_id": _SID, "context": ctx, "mode": "IMPLEMENTATION", "pid": 1},
    )


def _events(workspace: Path) -> list[dict]:
    log = workspace / ".dadaia" / "logs" / "lock-events.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]


def _flags(workspace: Path) -> list[dict]:
    return [e for e in _events(workspace) if e.get("event") == "RECONCILER_FLAG"]


def test_dirty_mutating_no_lease_emits_flag(monkeypatch, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    # A dirty production file (MUTATING) in the context repo.
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"])

    sdd_post_gate._reconcile_working_tree(ws, _SID)

    flags = _flags(ws)
    assert len(flags) == 1
    assert flags[0]["context"] == _CTX
    assert flags[0]["dirty_mutating_paths"] >= 1


def test_held_lease_no_flag(monkeypatch, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"])
    # Session holds the lease for its bound context ⇒ in-lease ⇒ no flag.
    monkeypatch.setattr(sdd_post_gate.lease, "contexts_for_session", lambda ws_, sid: [_CTX])

    sdd_post_gate._reconcile_working_tree(ws, _SID)
    assert _flags(ws) == []


def test_clean_tree_no_flag(monkeypatch, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: [])

    sdd_post_gate._reconcile_working_tree(ws, _SID)
    assert _flags(ws) == []


def test_additive_only_dirt_no_flag(monkeypatch, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    # specs/bugs is ADDITIVE — dirt there must NOT raise a flag.
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["specs/bugs/some-bug.md"])

    sdd_post_gate._reconcile_working_tree(ws, _SID)
    assert _flags(ws) == []


def test_git_status_failure_fails_open(monkeypatch, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: None)

    # Must not raise and must emit nothing.
    sdd_post_gate._reconcile_working_tree(ws, _SID)
    assert _flags(ws) == []


def test_no_bound_context_no_flag(monkeypatch, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    # No session record written ⇒ no bound context.
    called = {"git": False}

    def _spy(repo: Path):
        called["git"] = True
        return ["dadaia_workspace/x.py"]

    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", _spy)
    sdd_post_gate._reconcile_working_tree(ws, _SID)
    assert _flags(ws) == []


def test_throttle_skips_second_invocation_without_spawning_git(monkeypatch, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    spawn_count = {"n": 0}

    def _spy(repo: Path):
        spawn_count["n"] += 1
        return ["dadaia_workspace/x.py"]

    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", _spy)

    sdd_post_gate._reconcile_working_tree(ws, _SID)  # first: runs, stamps throttle, flags
    sdd_post_gate._reconcile_working_tree(ws, _SID)  # second: throttled BEFORE any git spawn

    assert spawn_count["n"] == 1, "throttled invocation must not spawn the git child"
    assert len(_flags(ws)) == 1


def test_throttle_expires_after_window(monkeypatch, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"])

    # First run stamps the marker "now".
    sdd_post_gate._reconcile_working_tree(ws, _SID)
    # Advance the throttle clock past the window for the second check.
    base = sdd_post_gate.time.time()
    monkeypatch.setattr(
        sdd_post_gate.time,
        "time",
        lambda: base + sdd_post_gate.RECONCILER_THROTTLE_TTL_SECONDS + 1,
    )
    sdd_post_gate._reconcile_working_tree(ws, _SID)

    assert len(_flags(ws)) == 2, "after the window the reconciler runs again"


def test_main_never_raises_with_reconciler(monkeypatch, tmp_path: Path) -> None:
    """The full PostToolUse main() returns 0 even if the reconciler would emit a flag."""
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"])
    monkeypatch.setattr(sdd_post_gate._common, "read_stdin_json", lambda: {"session_id": _SID})
    monkeypatch.setattr(sdd_post_gate._common, "resolve_session_id", lambda payload: _SID)

    assert sdd_post_gate.main() == 0


# ---------------------------------------------------------------------------------------
# The four explicit never-blocks acceptance criteria (T-014-16 "Done"):
# (1) always exit-allow even on the out-of-lease dirty MUTATING path,
# (2) advisory output only,
# (3) fail-open on an INTERNAL error (not just a git failure),
# (4) no lease mutation.
# ---------------------------------------------------------------------------------------
def test_criterion1_exit_allow_on_out_of_lease_dirty_mutating(monkeypatch, tmp_path: Path) -> None:
    """The exact flagging path (dirty MUTATING + no held lease) still returns exit 0."""
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"])
    # No held lease for the bound context → this is the flagging branch.
    monkeypatch.setattr(sdd_post_gate.lease, "contexts_for_session", lambda ws_, sid: [])
    monkeypatch.setattr(sdd_post_gate._common, "read_stdin_json", lambda: {"session_id": _SID})
    monkeypatch.setattr(sdd_post_gate._common, "resolve_session_id", lambda payload: _SID)

    assert sdd_post_gate.main() == 0
    # (2) advisory output only: a RECONCILER_FLAG event was appended, nothing was blocked.
    assert len(_flags(ws)) == 1


def test_criterion2_only_advisory_event_appended(monkeypatch, tmp_path: Path) -> None:
    """The reconciler's ONLY side effect is the advisory event — nothing else is logged."""
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"])
    monkeypatch.setattr(sdd_post_gate.lease, "contexts_for_session", lambda ws_, sid: [])

    sdd_post_gate._reconcile_working_tree(ws, _SID)

    events = _events(ws)
    assert len(events) == 1
    assert events[0]["event"] == "RECONCILER_FLAG"
    assert "no action taken" in events[0]["note"]


def test_criterion3_internal_error_fails_open(monkeypatch, tmp_path: Path) -> None:
    """An INTERNAL reconciler error (not a git failure) never breaks main()'s exit 0."""
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))

    def _boom(repo):
        raise RuntimeError("classifier blew up mid-pass")

    # Force an exception INSIDE the reconciler (after the throttle, during path inspection).
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", _boom)
    monkeypatch.setattr(sdd_post_gate._common, "read_stdin_json", lambda: {"session_id": _SID})
    monkeypatch.setattr(sdd_post_gate._common, "resolve_session_id", lambda payload: _SID)

    # main()'s reconciler try/except must swallow it and still return 0.
    assert sdd_post_gate.main() == 0


def test_criterion4_no_lease_mutation(monkeypatch, tmp_path: Path) -> None:
    """The flagging pass must NEVER touch the lease record — it is byte-for-byte unchanged."""
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    # A real lease record on disk for a DIFFERENT (foreign) session.
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lease_path = lock_dir / f"{_CTX}.lock.json"
    lease_path.write_text(
        json.dumps(
            {
                "context": _CTX,
                "session_id": "foreign-holder",
                "mode": "IMPLEMENTATION",
                "pid": 999999,
                "heartbeat": "2026-06-12T00:00:00+00:00",
                "ttl": 120,
            }
        ),
        encoding="utf-8",
    )
    before = lease_path.read_bytes()

    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"])
    monkeypatch.setattr(sdd_post_gate.lease, "contexts_for_session", lambda ws_, sid: [])

    sdd_post_gate._reconcile_working_tree(ws, _SID)

    assert lease_path.read_bytes() == before, "reconciler must not mutate the lease record"
    assert len(_flags(ws)) == 1
