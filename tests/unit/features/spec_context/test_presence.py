"""Presence module contract — v0.1.76 FR2 (advisory presence replaces the lease).

``features/spec_context/presence.py`` is the ONLY concurrency-signal surface after the
lock-liberation doctrine (SPEC v0.1.76, backlog ``lock-lease-session-identity-kernel``).
It is NOT a lock: it can never block a write, never raise into a caller, and never
starve another session. This file is the RED-first invariant suite (T-1); the module
does not exist yet — every test below FAILS at collection/import until T-2 implements it.

Doctrine invariants asserted here (SPEC AC4 successor list):
  * ``upsert`` never raises — even when the presence directory is unwritable.
  * ``others_alive`` excludes self, excludes stale (heartbeat older than
    ``LEASE_TTL_SECONDS``), and skips corrupt records.
  * ``renew`` touches the heartbeat of every record the session owns.
  * ``clear`` removes only the caller's own records and is idempotent.
  * ``sweep`` GCs stale records workspace-wide (doctor path).
"""

from __future__ import annotations

import json
import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.features.spec_context import presence

pytestmark = pytest.mark.unit

_CTX = "dadaia-workspace"


def _presence_path(ws: Path, ctx: str, session_id: str) -> Path:
    return ws / ".dadaia" / "states" / "presence" / ctx / f"{session_id}.json"


def _read_presence(ws: Path, ctx: str, session_id: str) -> dict[str, object]:
    return json.loads(_presence_path(ws, ctx, session_id).read_text(encoding="utf-8"))


def _write_raw_presence(
    ws: Path,
    ctx: str,
    session_id: str,
    *,
    heartbeat_age_s: float = 0.0,
    runtime: str = "claude",
    pid: int = 4242,
    corrupt: bool = False,
) -> Path:
    path = _presence_path(ws, ctx, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if corrupt:
        path.write_text("{not-json", encoding="utf-8")
        return path
    now = datetime.now(tz=UTC) - timedelta(seconds=heartbeat_age_s)
    record = {
        "session_id": session_id,
        "runtime": runtime,
        "pid": pid,
        "started_at": now.isoformat(),
        "last_seen_at": now.isoformat(),
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# upsert — never raises, even on unwritable directories (presence must never fail work).
# --------------------------------------------------------------------------- #


def test_upsert_writes_a_record_with_the_documented_shape(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-1", runtime="claude", pid=1234)
    record = _read_presence(tmp_path, _CTX, "sess-1")
    assert record["session_id"] == "sess-1"
    assert record["runtime"] == "claude"
    assert record["pid"] == 1234
    assert isinstance(record["started_at"], str) and record["started_at"]
    assert isinstance(record["last_seen_at"], str) and record["last_seen_at"]


def test_upsert_is_idempotent_and_refreshes_last_seen_at(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-1", runtime="claude", pid=1234)
    first = _read_presence(tmp_path, _CTX, "sess-1")
    presence.upsert(tmp_path, _CTX, "sess-1", runtime="claude", pid=1234)
    second = _read_presence(tmp_path, _CTX, "sess-1")
    # started_at is stable across re-upserts; last_seen_at is refreshed (both ISO strings —
    # equality is legal on a fast clock, so we assert monotonic non-decrease, not strict >).
    assert first["started_at"] == second["started_at"]
    assert second["last_seen_at"] >= first["last_seen_at"]


def test_upsert_never_raises_when_presence_dir_is_unwritable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The core swallow-all-errors contract: presence I/O failure must not fail a write."""
    presence_root = tmp_path / ".dadaia" / "states" / "presence"
    presence_root.mkdir(parents=True)
    presence_root.chmod(stat.S_IREAD | stat.S_IEXEC)  # read+exec only, no write
    try:
        if os.geteuid() == 0:
            pytest.skip("root bypasses directory permission enforcement")
    except AttributeError:
        pass  # Windows: no geteuid; permission model differs, rely on monkeypatch below
    try:
        # Must not raise regardless of the underlying OSError.
        presence.upsert(tmp_path, _CTX, "sess-locked-out", runtime="claude", pid=1)
    finally:
        presence_root.chmod(stat.S_IRWXU)


def test_upsert_never_raises_on_injected_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Belt-and-suspenders: force ``os.replace`` to explode; upsert must still not raise."""

    def _boom(*_a: object, **_k: object) -> None:
        raise OSError("simulated disk failure")

    monkeypatch.setattr(presence.os, "replace", _boom)
    presence.upsert(tmp_path, _CTX, "sess-boom", runtime="claude", pid=1)  # must not raise


# --------------------------------------------------------------------------- #
# others_alive — excludes self, excludes stale, skips corrupt, opportunistic GC.
# --------------------------------------------------------------------------- #


def test_others_alive_excludes_self(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-me", runtime="claude", pid=1)
    others = presence.others_alive(tmp_path, _CTX, "sess-me")
    assert others == []


def test_others_alive_returns_fresh_sibling_records(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-me", runtime="claude", pid=1)
    presence.upsert(tmp_path, _CTX, "sess-other", runtime="codex", pid=2)
    others = presence.others_alive(tmp_path, _CTX, "sess-me")
    assert [o.session_id for o in others] == ["sess-other"]
    assert others[0].runtime == "codex"


def test_others_alive_excludes_stale_heartbeats(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-me", runtime="claude", pid=1)
    _write_raw_presence(
        tmp_path,
        _CTX,
        "sess-stale",
        heartbeat_age_s=kernel_tunables.LEASE_TTL_SECONDS + 60,
    )
    others = presence.others_alive(tmp_path, _CTX, "sess-me")
    assert others == []


def test_others_alive_boundary_fresh_just_under_ttl_counts(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-me", runtime="claude", pid=1)
    _write_raw_presence(
        tmp_path,
        _CTX,
        "sess-fresh",
        heartbeat_age_s=kernel_tunables.LEASE_TTL_SECONDS - 5,
    )
    others = presence.others_alive(tmp_path, _CTX, "sess-me")
    assert [o.session_id for o in others] == ["sess-fresh"]


def test_others_alive_skips_corrupt_records(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-me", runtime="claude", pid=1)
    _write_raw_presence(tmp_path, _CTX, "sess-corrupt", corrupt=True)
    others = presence.others_alive(tmp_path, _CTX, "sess-me")
    assert others == []


def test_others_alive_opportunistically_gcs_stale_sibling(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-me", runtime="claude", pid=1)
    stale_path = _write_raw_presence(
        tmp_path,
        _CTX,
        "sess-stale",
        heartbeat_age_s=kernel_tunables.LEASE_TTL_SECONDS + 60,
    )
    presence.others_alive(tmp_path, _CTX, "sess-me")
    assert not stale_path.exists(), "stale sibling must be swept opportunistically"


def test_others_alive_never_raises_on_missing_context_dir(tmp_path: Path) -> None:
    assert presence.others_alive(tmp_path, "no-such-context", "sess-me") == []


# --------------------------------------------------------------------------- #
# renew — touches heartbeats of every record the session owns; never raises.
# --------------------------------------------------------------------------- #


def test_renew_touches_heartbeat_of_owned_records_across_contexts(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-1", runtime="claude", pid=1)
    presence.upsert(tmp_path, "other-ctx", "sess-1", runtime="claude", pid=1)
    before_a = _read_presence(tmp_path, _CTX, "sess-1")["last_seen_at"]
    before_b = _read_presence(tmp_path, "other-ctx", "sess-1")["last_seen_at"]

    presence.renew(tmp_path, "sess-1")

    after_a = _read_presence(tmp_path, _CTX, "sess-1")["last_seen_at"]
    after_b = _read_presence(tmp_path, "other-ctx", "sess-1")["last_seen_at"]
    assert after_a >= before_a
    assert after_b >= before_b


def test_renew_never_touches_foreign_records(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-foreign", runtime="claude", pid=1)
    before = _read_presence(tmp_path, _CTX, "sess-foreign")
    presence.renew(tmp_path, "sess-me")  # a session that owns nothing
    after = _read_presence(tmp_path, _CTX, "sess-foreign")
    assert before == after


def test_renew_never_raises_when_nothing_owned(tmp_path: Path) -> None:
    presence.renew(tmp_path, "sess-nobody")  # must not raise


# --------------------------------------------------------------------------- #
# clear — deletes own records, idempotent, never touches foreign records.
# --------------------------------------------------------------------------- #


def test_clear_removes_own_records(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-1", runtime="claude", pid=1)
    assert _presence_path(tmp_path, _CTX, "sess-1").exists()
    presence.clear(tmp_path, "sess-1")
    assert not _presence_path(tmp_path, _CTX, "sess-1").exists()


def test_clear_is_idempotent(tmp_path: Path) -> None:
    presence.clear(tmp_path, "sess-never-existed")  # must not raise
    presence.upsert(tmp_path, _CTX, "sess-1", runtime="claude", pid=1)
    presence.clear(tmp_path, "sess-1")
    presence.clear(tmp_path, "sess-1")  # second clear is a safe no-op


def test_clear_scoped_to_ctx_leaves_other_contexts_intact(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-1", runtime="claude", pid=1)
    presence.upsert(tmp_path, "other-ctx", "sess-1", runtime="claude", pid=1)
    presence.clear(tmp_path, "sess-1", ctx=_CTX)
    assert not _presence_path(tmp_path, _CTX, "sess-1").exists()
    assert _presence_path(tmp_path, "other-ctx", "sess-1").exists()


def test_clear_never_touches_foreign_records(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-foreign", runtime="claude", pid=1)
    presence.clear(tmp_path, "sess-me")
    assert _presence_path(tmp_path, _CTX, "sess-foreign").exists()


# --------------------------------------------------------------------------- #
# sweep — workspace-wide GC of stale records (doctor path).
# --------------------------------------------------------------------------- #


def test_sweep_removes_stale_records_workspace_wide(tmp_path: Path) -> None:
    presence.upsert(tmp_path, _CTX, "sess-fresh", runtime="claude", pid=1)
    _write_raw_presence(
        tmp_path,
        _CTX,
        "sess-stale-a",
        heartbeat_age_s=kernel_tunables.LEASE_TTL_SECONDS + 100,
    )
    _write_raw_presence(
        tmp_path,
        "other-ctx",
        "sess-stale-b",
        heartbeat_age_s=kernel_tunables.LEASE_TTL_SECONDS + 100,
    )
    removed = presence.sweep(tmp_path)
    assert set(removed) == {"sess-stale-a", "sess-stale-b"}
    assert _presence_path(tmp_path, _CTX, "sess-fresh").exists()
    assert not _presence_path(tmp_path, _CTX, "sess-stale-a").exists()
    assert not _presence_path(tmp_path, "other-ctx", "sess-stale-b").exists()


def test_sweep_removes_corrupt_records(tmp_path: Path) -> None:
    _write_raw_presence(tmp_path, _CTX, "sess-corrupt", corrupt=True)
    removed = presence.sweep(tmp_path)
    assert "sess-corrupt" in removed
    assert not _presence_path(tmp_path, _CTX, "sess-corrupt").exists()


def test_sweep_never_raises_on_missing_presence_root(tmp_path: Path) -> None:
    assert presence.sweep(tmp_path) == []
