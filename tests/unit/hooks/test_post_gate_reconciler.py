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

FR11 (T-046-29): the reconciler writes no event log any more — a dirty MUTATING pass
leaves no ``.dadaia/logs`` behind; its only side effects are the throttle marker and
the reaper's own work under ``.dadaia/tmp/``.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.core import session_store
from dadaia_workspace.core.kernel_tunables import RECONCILER_THROTTLE_TTL_SECONDS
from dadaia_workspace.hooks import _common, sdd_post_gate

_SID = "session-recon"
_CTX = "demo-ctx"


def _make_workspace(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    # _bound_context now routes through core.invocation.resolve, whose rung-2 (own
    # session record) requires the context to be REGISTERED (single-authority
    # semantics) — the direct session_store.read_session the old implementation used
    # never checked this. A registered ALIVE context is what a real `dadaia context
    # bind` produces, so this fixture models that instead of working around it.
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [{"name": _CTX, "repo_slug": _CTX, "state": "alive"}],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "repos" / _CTX).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _bind_session(workspace: Path, ctx: str = _CTX) -> None:
    session_store.write_session(
        workspace,
        _SID,
        {
            "session_id": _SID,
            "context": ctx,
            "mode": "IMPLEMENTATION",
            "pid": 1,
            # rung 2 (core.invocation._live_session_context) is liveness-gated —
            # a fresh heartbeat keeps this fixture's record un-stale.
            "last_seen_at": datetime.now(tz=UTC).isoformat(),
        },
    )


def test_dirty_mutating_path_leaves_no_logs_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Intent: CONTRACT — AC10 (logs), T-046-29. Size: SMALL (git child faked).

    The dirty-MUTATING pass — the branch that used to append ``RECONCILER_FLAG`` to
    ``.dadaia/logs/reconciler-events.jsonl`` — creates no ``.dadaia/logs`` directory,
    neither through ``_reconcile_working_tree`` nor through the full PostToolUse
    ``main()``, which still exits 0 on this path (never-blocks, criterion1).
    """
    # This suite runs inside the dadaia-workspace SOURCE checkout, itself nested under a
    # REAL registered "dadaia-workspace" context; an ambient DADAIA_CONTEXT (rung 1, the
    # normal way an agent binds a plain shell) would otherwise outrank this test's own
    # session record (rung 2) and misresolve _bound_context to a context this tmp_path
    # fixture never created a repo for (bug
    # post-gate-reconciler-tests-order-dependent-flake).
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    ws = _make_workspace(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    _bind_session(ws)
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: ["dadaia_workspace/x.py"])

    sdd_post_gate._reconcile_working_tree(ws, _SID)
    assert not (ws / ".dadaia" / "logs").exists()

    ws2 = _make_workspace(tmp_path.parent / (tmp_path.name + "-main"))
    _bind_session(ws2)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws2))
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": _SID})
    monkeypatch.setattr(_common, "resolve_session_id", lambda payload: _SID)
    assert sdd_post_gate.main() == 0
    assert not (ws2 / ".dadaia" / "logs").exists()


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
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setenv("DADAIA_CONTEXT", "env-ctx")

    assert sdd_post_gate._bound_context("never-bound-sid") == "env-ctx"


def test_bound_context_env_wins_over_own_record_law_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """F-03 (v0.5.0 six-axis review): rung 1 ``DADAIA_CONTEXT`` beats rung 2 (the
    session binding) here too — presence attribution must agree with the gate and
    ctx_inject on the same prompt, per the DADAIA.md §3 rung order."""
    ws = _make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setenv("DADAIA_CONTEXT", "env-ctx")
    _bind_session(ws, ctx=_CTX)

    assert sdd_post_gate._bound_context(_SID) == "env-ctx"

    # Without the env override the own record is the binding (rung 2), unchanged.
    monkeypatch.delenv("DADAIA_CONTEXT")
    assert sdd_post_gate._bound_context(_SID) == _CTX


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
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", porcelain_fn)
    if use_main:
        monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": _SID})
        monkeypatch.setattr(_common, "resolve_session_id", lambda payload: _SID)
        assert sdd_post_gate.main() == 0
    else:
        # Must not raise, and the failed pass leaves no log behind either.
        sdd_post_gate._reconcile_working_tree(ws, _SID)
        assert not (ws / ".dadaia" / "logs").exists()


def test_throttle_skip_and_expiry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # See test_dirty_mutating_emits_flag_advisory_only's comment: an ambient
    # DADAIA_CONTEXT would outrank this test's own session record and misresolve the
    # bound context, short-circuiting _reconcile_working_tree before it ever spawns the
    # (mocked) git child (bug post-gate-reconciler-tests-order-dependent-flake).
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    ws = _make_workspace(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    _bind_session(ws)
    spawn_count = {"n": 0}

    def _spy(repo: Path) -> list[str]:
        spawn_count["n"] += 1
        return ["dadaia_workspace/x.py"]

    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", _spy)

    sdd_post_gate._reconcile_working_tree(ws, _SID)  # first: runs, stamps throttle, flags
    sdd_post_gate._reconcile_working_tree(ws, _SID)  # second: throttled BEFORE any git spawn

    assert spawn_count["n"] == 1, "throttled invocation must not spawn the git child"

    # Advance the throttle clock past the window for the third check. sdd_post_gate
    # imports the stdlib `time` module directly (`import time`), so patching the SAME
    # module object here (imported here too) affects the production call site.
    base = time.time()
    monkeypatch.setattr(time, "time", lambda: base + RECONCILER_THROTTLE_TTL_SECONDS + 1)
    sdd_post_gate._reconcile_working_tree(ws, _SID)

    assert spawn_count["n"] == 2, "after the window the reconciler runs again"
