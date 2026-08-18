"""Unit tests for the advisory working-tree reconciler (FR-W1-03, T-014-16).

NEVER-BLOCKS contract: every branch must (1) leave exit-allow, (2) emit only advisory
output, (3) fail open on error. The git child is faked — no real ``git status`` runs, and
the throttle is asserted to short-circuit BEFORE any spawn.

v0.1.76 T-3 re-baseline: the former "session holds the lease for its bound context ⇒
in-lease ⇒ no flag" branch is DELETED along with the by-session index it read
(``lease.contexts_for_session`` no longer exists) — nothing is ever "in-lease" anymore, so
every dirty MUTATING path in a bound repo is now unconditionally flagged (see
``sdd_post_gate._reconcile_working_tree``'s updated docstring). Criterion4 (byte-identical
lease record) drops out with it — there is no lease record for the reconciler to touch.

CRIT (NEVER-BLOCKS): the flag test below folds in criterion2 (advisory-only: the ONLY
side effect is the RECONCILER_FLAG event).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.kernel_tunables import RECONCILER_THROTTLE_TTL_SECONDS
from dadaia_workspace.features.spec_context import session_identity
from dadaia_workspace.hooks import _common, sdd_post_gate

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


def _events(workspace: Path) -> list[dict[str, Any]]:
    log = workspace / ".dadaia" / "logs" / "reconciler-events.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]


def _flags(workspace: Path) -> list[dict[str, Any]]:
    return [e for e in _events(workspace) if e.get("event") == "RECONCILER_FLAG"]


def test_dirty_mutating_emits_flag_advisory_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # This suite runs inside the dadaia-workspace SOURCE checkout, itself nested under a
    # REAL registered "dadaia-workspace" context; an ambient DADAIA_CONTEXT (rung 1, the
    # normal way an agent binds a plain shell) would otherwise outrank this test's own
    # session record (rung 2) and misresolve _bound_context to a context this tmp_path
    # fixture never created a repo for (bug
    # post-gate-reconciler-tests-order-dependent-flake).
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    ws = _make_workspace(tmp_path)
    _bind_session(ws)

    # A dirty production file (MUTATING) in the bound context repo ⇒ the flagging branch
    # (unconditional now — there is no lease to be "in" anymore).
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"])

    sdd_post_gate._reconcile_working_tree(ws, _SID)

    flags = _flags(ws)
    assert len(flags) == 1
    assert flags[0]["context"] == _CTX
    assert flags[0]["dirty_mutating_paths"] >= 1

    # criterion2: the ONLY side effect is the advisory event — nothing else logged.
    events = _events(ws)
    assert len(events) == 1
    assert events[0]["event"] == "RECONCILER_FLAG"
    assert "no action taken" in events[0]["note"]

    # Companion: the full PostToolUse main() returns 0 even on this exact dirty MUTATING
    # flagging path (criterion1) — proving never-blocks holds end-to-end, not just at the
    # pure _reconcile_working_tree layer.
    ws2 = _make_workspace(tmp_path.parent / (tmp_path.name + "-main"))
    _bind_session(ws2)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws2))
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"])
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": _SID})
    monkeypatch.setattr(_common, "resolve_session_id", lambda payload: _SID)
    assert sdd_post_gate.main() == 0
    assert len(_flags(ws2)) == 1


@pytest.mark.parametrize(
    ("name", "setup_fn"),
    [
        (
            "clean_tree",
            lambda ws, mp: mp.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: []),
        ),
        (
            # specs/bugs is ADDITIVE — dirt there must NOT raise a flag.
            "additive_only_dirt",
            lambda ws, mp: mp.setattr(
                sdd_post_gate, "_porcelain_paths", lambda repo: ["specs/bugs/some-bug.md"]
            ),
        ),
        (
            # No session record written ⇒ no bound context ⇒ no flag, even with dirt.
            "no_bound_context",
            lambda ws, mp: mp.setattr(
                sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"]
            ),
        ),
    ],
)
def test_no_flag_table(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, setup_fn: object
) -> None:
    # T-50-02 (SPEC v0.5.0 FR1): "no_bound_context" now falls through
    # _bound_context's leg 2 (the single resolution authority, rungs 1-3) instead of
    # stopping at the direct record read. This suite runs inside the dadaia-workspace
    # SOURCE checkout, itself nested under a REAL registered "dadaia-workspace" context
    # — chdir + a scrubbed DADAIA_CONTEXT keep rung 3 (cwd) and rung 1 (env) from
    # leaking that real context into this "isolated" tmp_path fixture.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    ws = _make_workspace(tmp_path)
    if name != "no_bound_context":
        _bind_session(ws)
    setup_fn(ws, monkeypatch)  # type: ignore[operator]
    sdd_post_gate._reconcile_working_tree(ws, _SID)
    assert _flags(ws) == []


def test_bound_context_leg2_falls_through_to_authority_via_dadaia_context_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """T-50-02 (SPEC v0.5.0 FR1): ``_bound_context``'s NEW leg 2 — no own session
    record at all, but ``DADAIA_CONTEXT`` resolves via the single authority (the SPEC's
    kimi-launch-env disposition: a kimi session carries no native session-id env var, so
    its record can never be found by leg 1). Purely additive: leg 1 (the direct record
    read) is untouched, proven by ``test_no_flag_table``'s ``no_bound_context`` case
    staying flag-free when NEITHER leg resolves anything usable."""
    ws = _make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DADAIA_CONTEXT", "env-ctx")

    assert sdd_post_gate._bound_context(ws, "never-bound-sid") == "env-ctx"


def test_bound_context_env_wins_over_own_record_law_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """F-03 (v0.5.0 six-axis review): rung 1 ``DADAIA_CONTEXT`` beats rung 2 (the
    session binding) here too — presence attribution must agree with the gate and
    ctx_inject on the same prompt, per the DADAIA.md §3 rung order."""
    ws = _make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DADAIA_CONTEXT", "env-ctx")
    _bind_session(ws, ctx=_CTX)

    assert sdd_post_gate._bound_context(ws, _SID) == "env-ctx"

    # Without the env override the own record is the binding (rung 2), unchanged.
    monkeypatch.delenv("DADAIA_CONTEXT")
    assert sdd_post_gate._bound_context(ws, _SID) == _CTX


@pytest.mark.parametrize(
    ("name", "porcelain_fn", "use_main"),
    [
        # Must not raise and must emit nothing (git status itself failed → None).
        ("git_status_failure_fails_open", lambda repo: None, False),
        # An INTERNAL reconciler error (not a git failure) never breaks main()'s exit 0
        # (criterion3).
        (
            "internal_error_fails_open_criterion3",
            lambda repo: (_ for _ in ()).throw(RuntimeError("classifier blew up mid-pass")),
            True,
        ),
    ],
)
def test_fail_open_table(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, porcelain_fn: object, use_main: bool
) -> None:
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", porcelain_fn)
    if use_main:
        monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
        monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": _SID})
        monkeypatch.setattr(_common, "resolve_session_id", lambda payload: _SID)
        assert sdd_post_gate.main() == 0
    else:
        # Must not raise and must emit nothing.
        sdd_post_gate._reconcile_working_tree(ws, _SID)
        assert _flags(ws) == []


def test_throttle_skip_and_expiry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # See test_dirty_mutating_emits_flag_advisory_only's comment: an ambient
    # DADAIA_CONTEXT would outrank this test's own session record and misresolve the
    # bound context, short-circuiting _reconcile_working_tree before it ever spawns the
    # (mocked) git child (bug post-gate-reconciler-tests-order-dependent-flake).
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    spawn_count = {"n": 0}

    def _spy(repo: Path) -> list[str]:
        spawn_count["n"] += 1
        return ["dadaia_workspace/x.py"]

    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", _spy)

    sdd_post_gate._reconcile_working_tree(ws, _SID)  # first: runs, stamps throttle, flags
    sdd_post_gate._reconcile_working_tree(ws, _SID)  # second: throttled BEFORE any git spawn

    assert spawn_count["n"] == 1, "throttled invocation must not spawn the git child"
    assert len(_flags(ws)) == 1

    # Advance the throttle clock past the window for the third check. sdd_post_gate
    # imports the stdlib `time` module directly (`import time`), so patching the SAME
    # module object here (imported here too) affects the production call site.
    base = time.time()
    monkeypatch.setattr(time, "time", lambda: base + RECONCILER_THROTTLE_TTL_SECONDS + 1)
    sdd_post_gate._reconcile_working_tree(ws, _SID)

    assert len(_flags(ws)) == 2, "after the window the reconciler runs again"


# ---------------------------------------------------------------------------
# FR27/A27.1 (T-043-42): reconciler-events.jsonl rotates like every other
# .dadaia/logs/*.jsonl writer, funneled through the shared rotation helper.
# ---------------------------------------------------------------------------


def test_reconciler_flag_rotates_the_shared_events_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import dadaia_workspace.infrastructure.jsonl_log_rotation as rotation

    log = tmp_path / ".dadaia" / "logs" / "reconciler-events.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text('{"seed": true}\n', encoding="utf-8")
    monkeypatch.setattr(rotation, "LOG_ROTATION_MAX_BYTES", 8)

    sdd_post_gate._append_reconciler_flag(tmp_path, _SID, _CTX, 1)  # noqa: SLF001

    rotated = log.with_name(log.name + ".1")
    assert rotated.exists()
    assert json.loads(rotated.read_text(encoding="utf-8").strip()) == {"seed": True}
    new_events = _events(tmp_path)
    assert len(new_events) == 1
    assert new_events[0]["event"] == "RECONCILER_FLAG"
