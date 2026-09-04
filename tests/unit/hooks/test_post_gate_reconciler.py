"""Unit tests for the PostToolUse hook's throttled GC cadence (``sdd_post_gate``).

Intent: CONTRACT — T-046-29 (FR11 ruling: the reconciler's unobservable dirty-path chain
is deleted) + FR-W1-03 NEVER-BLOCKS, re-seated at the seams that survive.

What remains of the "advisory working-tree reconciler" is its throttle marker
(``.dadaia/tmp/reconciler-last-<sid>``) and the ONE reaper it gates (``presence.gc``,
release 0.5.1 K2). The ``git status`` classification that used to feed a
``RECONCILER_FLAG`` log line died with the log: a dirty MUTATING path in the bound repo
spawns no git child and writes nothing. Every branch must (1) exit 0, (2) fail open.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.core import session_store
from dadaia_workspace.core.kernel_tunables import RECONCILER_THROTTLE_TTL_SECONDS
from dadaia_workspace.features.spec_context import presence
from dadaia_workspace.hooks import _common, sdd_post_gate

_SID = "session-recon"
_CTX = "demo-ctx"


def _make_workspace(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    # A registered ALIVE context is what a real `dadaia context bind` produces.
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


def _spy_git_children(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Record every ``subprocess.run`` argv — the seam any git child would cross."""
    spawned: list[list[str]] = []

    def _run(
        argv: Sequence[str], *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        spawned.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout=" M dadaia_workspace/x.py\n", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)
    return spawned


def test_dirty_mutating_path_spawns_no_git_child_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Intent: CONTRACT — T-046-29 ruling + AC10 (logs). Size: SMALL (subprocess seam spied).

    A dirty MUTATING file in the bound context repo used to make the reconciler spawn
    ``git status --porcelain`` and append ``RECONCILER_FLAG``. Both are gone: no git
    child crosses ``subprocess.run``, no ``.dadaia/logs`` appears, and the full
    PostToolUse ``main()`` still exits 0 on this path (never-blocks).
    """
    # An ambient DADAIA_CONTEXT (this suite runs inside a real bound checkout) must not
    # outrank the fixture's own session record.
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    ws = _make_workspace(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    _bind_session(ws)
    dirty = ws / "repos" / _CTX / "dadaia_workspace" / "x.py"
    dirty.parent.mkdir(parents=True)
    dirty.write_text("x = 1\n", encoding="utf-8")
    spawned = _spy_git_children(monkeypatch)

    sdd_post_gate._throttled_gc(ws, _SID)
    assert [argv for argv in spawned if argv[:1] == ["git"]] == []
    assert not (ws / ".dadaia" / "logs").exists()

    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": _SID})
    monkeypatch.setattr(_common, "resolve_session_id", lambda payload: _SID)
    assert sdd_post_gate.main() == 0
    assert [argv for argv in spawned if argv[:1] == ["git"]] == []
    assert not (ws / ".dadaia" / "logs").exists()


def test_reaper_error_fails_open_exit_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Intent: CONTRACT — FR-W1-03 never-blocks (criterion3) at the surviving seam. Size: SMALL.

    An internal error inside the throttled pass (the reaper raising, against its own
    never-raises contract) never breaks ``main()``'s exit 0 — the hook's own try/except
    is the fail-open boundary.
    """
    ws = _make_workspace(tmp_path)
    _bind_session(ws)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))

    def _boom(workspace: Path, *, now: datetime, own_session_id: str) -> presence.GcReport:
        raise RuntimeError("reaper blew up mid-pass")

    monkeypatch.setattr(presence, "gc", _boom)
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": _SID})
    monkeypatch.setattr(_common, "resolve_session_id", lambda payload: _SID)
    assert sdd_post_gate.main() == 0


def test_throttle_skips_the_reaper_inside_the_window_and_runs_after_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Intent: CONTRACT — FR-W1-03 throttle + K2 cadence (byte-identical after T-046-29). Size: SMALL.

    The throttle marker is checked BEFORE the reaper runs: two passes inside the window
    call ``presence.gc`` once; a third pass after the window calls it again.
    """
    ws = _make_workspace(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    _bind_session(ws)
    calls = {"n": 0}
    real_gc = presence.gc

    def _spy(workspace: Path, *, now: datetime, own_session_id: str) -> presence.GcReport:
        calls["n"] += 1
        return real_gc(workspace, now=now, own_session_id=own_session_id)

    monkeypatch.setattr(presence, "gc", _spy)

    sdd_post_gate._throttled_gc(ws, _SID)  # first: stamps the marker, reaps
    sdd_post_gate._throttled_gc(ws, _SID)  # second: throttled before the reaper
    assert calls["n"] == 1, "a throttled invocation must not run the reaper"

    # sdd_post_gate imports the stdlib `time` module directly, so patching the SAME
    # module object here moves the production call site's clock past the window.
    base = time.time()
    monkeypatch.setattr(time, "time", lambda: base + RECONCILER_THROTTLE_TTL_SECONDS + 1)
    sdd_post_gate._throttled_gc(ws, _SID)
    assert calls["n"] == 2, "after the window the cadence runs again"
