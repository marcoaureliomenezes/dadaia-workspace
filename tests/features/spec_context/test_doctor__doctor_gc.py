"""Doctor cleanup: retired concurrency state, caller-owned sessions and the one expiry table.

Re-classification note (T-011-04 / FR-W1-04, ADR-8 amended): SESSION-record (bind) GC TTL
semantics measure against the heartbeat-renewed ``last_seen_at`` (``session_store.is_live``);
the bind-CLI pid is never consulted (dead by construction).

CRITICAL GC: renewed-bind survival prevents live-session collection — kept verbatim,
exercising the REAL PostToolUse renewal path (no planted-pid fixtures).
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core.workspace_layout import DADAIA_ZONES, ZoneClass, zones_with_ttl
from dadaia_workspace.features.spec_context.doctor import DoctorService, FindingVerdict
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess
from tests.fixtures.stores import context_store


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"contexts": []}', encoding="utf-8"
    )
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / "repos").mkdir()
    return ws


def _make_doctor(ws: Path, store: JsonContextStore | None = None) -> DoctorService:
    if store is None:
        store = context_store(ws / ".dadaia" / "states")
    return DoctorService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=ws,
    )


def _ago(seconds: float) -> str:
    return (datetime.now(tz=UTC) - timedelta(seconds=seconds)).isoformat()


def _stale() -> str:  # past a day: a dead session, never a paused one
    return _ago(86400 + 60)


def _bind(ws: Path, sid: str, last_seen_at: str) -> Path:
    """A READ bind record written by the production session-store writer."""
    from dadaia_workspace.core import session_store

    record = {"session_id": sid, "context": "myctx", "mode": "READ", "release": None, "runtime": "test",
              "pid": 4242, "last_seen_at": last_seen_at}  # fmt: skip
    session_store.write_session(ws, sid, record)
    return ws / ".dadaia" / "sessions" / f"{sid}.json"


def test_gc_deletion_matrix(tmp_path: Path) -> None:
    """Retired context-global state (every ctx_locks shape: stale, sentinel, invalid JSON, incomplete)
    goes as one directory (WS-states-slop); an expired session record goes by GRAVEYARD-GC."""
    ws = _make_workspace(tmp_path)
    locks = ws / ".dadaia" / "states" / "ctx_locks"
    locks.mkdir(parents=True)
    (locks / "myctx.lock.json").write_text(
        json.dumps({"context": "myctx", "heartbeat": _stale()}), encoding="utf-8"
    )
    (locks / "myctx.lock.sentinel").write_text("", encoding="utf-8")
    (locks / "badctx.lock.json").write_text("NOT JSON {{{", encoding="utf-8")
    (locks / "incompletectx.lock.json").write_text('{"context": "x"}', encoding="utf-8")
    expired = _bind(ws, "old-sess-001", _stale())

    actions = _make_doctor(ws).fix()

    assert not locks.exists() and not expired.exists()
    assert any("WS-states-slop" in a for a in actions), actions
    assert any("GRAVEYARD-GC" in a and "old-sess-001.json" in a for a in actions), actions


def _post_gate_heartbeat(ws: Path, sess_id: str) -> None:
    """Invoke the REAL PostToolUse heartbeat (refreshes last_seen_at) for ``sess_id``, as the
    harness does: a child process whose env carries the native session id (resolve_session_id,
    env only). The renewal path the operator's live sessions take — not a planted timestamp.
    """
    env = claude_hook_env(ws, session_id=sess_id)
    assert run_hook_subprocess("sdd_post_gate", {"session_id": sess_id}, env).returncode == 0


@pytest.mark.parametrize(
    ("idle", "renew", "sessions_outside", "survives"),
    [
        pytest.param(360, False, False, True, id="bind-lost-silently-after-five-idle-minutes-idle-bind-survives"),
        pytest.param(None, True, False, True, id="FR-W1-04-heartbeat-renewed-bind-survives-and-resolves"),
        pytest.param(None, False, False, False, id="FR-W1-04-unrenewed-stale-bind-collected"),
        pytest.param(None, False, True, False, id="doctor-reports-a-refused-removal-as-deleted"),
    ],
)  # fmt: skip
def test_no_stale_records(
    tmp_path: Path, idle: int | None, renew: bool, sessions_outside: bool, survives: bool
) -> None:
    """T-011-04, bind-lost-silently-after-five-idle-minutes: another session's
    SessionStart lane collects a bind only past a dead session's TTL (a day), measured against
    ``last_seen_at`` renewed through the REAL PostToolUse path; idle minutes never unbind. A
    sessions dir resolving outside the workspace is refused, never reported deleted."""
    from dadaia_workspace.core.session_store import live_session

    ws = _make_workspace(tmp_path)
    sid = "sess_01"
    if sessions_outside:
        (ws / ".dadaia" / "sessions").rename(tmp_path / "elsewhere")
        (ws / ".dadaia" / "sessions").symlink_to(tmp_path / "elsewhere")
    record = _bind(ws, sid, _stale() if idle is None else _ago(idle))
    if renew:
        # post-gate-runs-the-reaper-on-the-tool-hot-path: the heartbeat never reaps.
        expired = ws / ".dadaia" / "tmp" / "expired.txt"
        expired.parent.mkdir(parents=True, exist_ok=True)
        expired.touch()
        os.utime(expired, (0, 0))
        _post_gate_heartbeat(ws, sid)
        assert expired.exists(), "a tool call must never run the reaper"

    actions = _make_doctor(ws).expire()

    assert record.exists() is (survives or sessions_outside)
    assert any("GRAVEYARD-GC: deleted" in a and sid in a for a in actions) is not (
        survives or sessions_outside
    )
    assert (live_session(ws, sid) is not None) is survives


@pytest.mark.parametrize("lane", ["expire", "fix"])
@pytest.mark.parametrize(
    ("rel", "past_ttl", "after"),
    [
        pytest.param("tmp/claude/20260801", 60, "gone", id="ephemeral-tmp-deleted"),
        pytest.param("reaped/20260901/x", 60, "gone", id="ephemeral-hold-deleted-at-its-ttl"),
        pytest.param("handoff/ctx/p.handoff.json", 60, "held", id="AC2.10-output-handoff-held"),
        pytest.param("tmp/claude/today", -60, "kept", id="live-entry-no-finding"),
        pytest.param("handoff/AGENTS.md", 400 * 86_400, "kept", id="zone-law-never-a-candidate"),
        pytest.param("tmp/link", 60, "gone", id="a-link-is-acted-on-never-followed"),
    ],
)  # fmt: skip
def test_a_ttl_expiry_is_its_zone_class_act(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lane: str, rel: str, past_ttl: int, after: str
) -> None:
    """AC2.10, AC2.12 (the one expiry table; bugs
    bug-proposal-handoff-reaped-without-a-hold, reaper-judges-ttl-by-walking-every-file,
    doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk finding 2): an expired entry is one
    finding; both lanes take it by its zone class — EPHEMERAL deleted, OUTPUT held in reaped/
    and named by one REAPED finding; a live entry or a zone law yields none; a link is acted on,
    its target never; a failing seed never stops the pass."""
    ws = _make_workspace(tmp_path)
    victim = tmp_path / "outside" / "keep.txt"
    victim.parent.mkdir()
    victim.write_text("keep", encoding="utf-8")
    entry = ws / ".dadaia" / rel
    entry.parent.mkdir(parents=True, exist_ok=True)
    if rel.endswith("link"):
        if os.utime not in os.supports_follow_symlinks:
            pytest.skip("ageing a link itself needs utime(follow_symlinks=False)")
        entry.symlink_to(victim.parent, target_is_directory=True)
    else:
        entry.write_text('{"findings": [{"message": "bug-proposal: x"}]}', encoding="utf-8")
    zone = next(z for z in DADAIA_ZONES if z.name == rel.split("/")[0])
    stamp = time.time() - (zone.ttl_seconds or 0) - past_ttl
    os.utime(entry, (stamp, stamp), **({"follow_symlinks": False} if entry.is_symlink() else {}))
    monkeypatch.setattr(JsonHarnessProfileStore, "write", _denied)
    doctor = _make_doctor(ws)
    before = [f.verdict for f in doctor.scan_ttl()]

    actions = getattr(doctor, lane)()

    held = list((ws / ".dadaia" / "reaped").glob(f"*/.dadaia/{rel}"))
    assert before == ([] if after == "kept" else [FindingVerdict.EXPIRED])
    assert (entry.is_symlink() or entry.exists(), bool(held)) == (after == "kept", after == "held")
    remaining = [f.verdict for f in doctor.scan_ttl()]
    assert remaining == ([FindingVerdict.REAPED] if after == "held" else [])
    assert victim.read_text(encoding="utf-8") == "keep"
    assert any("skipped 'states/harness_profile.json' (errno 13" in a for a in actions), actions
    # The rows cover exactly these two classes; a new TTL class needs a row here.
    assert {z.cls for z in zones_with_ttl()} <= {ZoneClass.OUTPUT, ZoneClass.EPHEMERAL}


def _denied(*_: object, **__: object) -> None:
    raise PermissionError(13, "Permission denied")


def test_the_expire_lane_walks_each_expired_entry_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rc-9 AC3.6 row 25 (ttl-expire-lane-walks-each-expired-entry-content-twice): the
    linked-worktree question is asked once per expired entry, at the filesystem seam."""
    from dadaia_workspace.features.spec_context import sweep

    ws = _make_workspace(tmp_path)
    entry = ws / ".dadaia" / "tmp" / "agent" / "20200101"
    (entry / "deep").mkdir(parents=True)
    (entry / "deep" / "f.txt").write_text("x", encoding="utf-8")
    for path in (entry / "deep" / "f.txt", entry / "deep", entry):
        os.utime(path, (0, 0))
    walked: list[Path] = []
    real_question = sweep.linked_worktree

    def _counting_question(root: Path, target: Path) -> Path | None:
        walked.append(target)
        return real_question(root, target)

    # shutil.rmtree's own os.walk (3.12.10+, Windows) is no question of ours
    monkeypatch.setattr(sweep, "linked_worktree", _counting_question)

    _make_doctor(ws).expire()

    assert walked == [entry.parent] and not entry.parent.exists()  # reaped whole: all below expired


def test_scan_leaves_an_expired_worktree_holder_to_its_worktree_row(tmp_path: Path) -> None:
    """rc-9 AC3.6 (doctor `_scan_ttl_zone`): an expired tmp entry holding a linked worktree
    yields no TTL finding (its WORKTREE `foreign` row reports it); a plain expired sibling
    is one EXPIRED finding whose detail states its age against the one-day TTL."""
    ws = _make_workspace(tmp_path)
    tmp = ws / ".dadaia" / "tmp"
    holder, plain = tmp / "a" / "20200101", tmp / "b" / "20200101"
    (holder / "wt").mkdir(parents=True)
    (holder / "wt" / ".git").write_text("gitdir: /elsewhere/.git/worktrees/wt\n", "utf-8")
    plain.mkdir(parents=True)
    stamp = time.time() - 3 * 86_400 - 60
    for path in (holder / "wt" / ".git", holder / "wt", holder, holder.parent, plain, plain.parent):
        os.utime(path, (stamp, stamp))

    found = [(f.path, f.verdict, f.detail) for f in _make_doctor(ws).scan_ttl()]

    assert found == [("tmp/b", FindingVerdict.EXPIRED, "(mtime 3d > ttl 1d)")]
