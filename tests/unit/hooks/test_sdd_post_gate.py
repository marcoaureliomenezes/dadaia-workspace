"""Unit tests for dadaia_workspace.hooks.sdd_post_gate (R2a, FR-R2-01/02).

These are *in-process* unit tests of the hook's internals and the resolution-chain /
fail-open contract. They import the module directly (the hook-import contract baselines
this file at ``tests/contract/test_harness_env_contract.py`` precisely because in-process
internal unit tests of small helpers are legitimate). The harness-real *behavior* of the
hook — invoked as a subprocess with a ``claude_hook_env()`` and no hand-planted
``DADAIA_*`` — is proven in ``tests/unit/hooks/test_sdd_post_gate_behavior.py``.

``DADAIA_SESSION_ID`` appears here only as the *operator override* leg of the resolution
chain (``resolve_session_id`` honors it first); the harness never sets it.

Mandatory parity preserved from rc-4:
  (a) session-record renewal via os.replace (atomic on Windows too);
  (b) [A-Za-z0-9_-] session-id strip (CWE-22) — via resolve_session_id;
  (c) fail-open: any error -> exit 0, never a crash/block.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease
from dadaia_workspace.hooks import _common, sdd_post_gate


def _scrub_session_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every session-id env var the *operator shell* might leak into this process.

    A real harness never sets ``DADAIA_SESSION_ID``; the native vars (``CLAUDE_CODE_…``)
    are present in a developer's shell and would shadow the stdin ``session_id`` we drive
    these unit tests with. Scrubbing them models the resolution chain honestly.
    """
    for var in (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "OPENCODE_SESSION_ID",
    ):
        monkeypatch.delenv(var, raising=False)


def _seed_session_record(workspace: Path, sess_id: str) -> Path:
    sessions = workspace / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    path = sessions / f"{sess_id}.json"
    path.write_text(
        json.dumps(
            {
                "context": "ctx",
                "release": "rel-1",
                "runtime": "claude",
                "pid": 42,
                "last_seen_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    return path


def _seed_lease(workspace: Path, ctx: str, sess_id: str) -> None:
    """Acquire a fresh (non-stale) lease for ``ctx`` held by ``sess_id``."""
    status, _rec = lease.acquire(workspace, ctx, sess_id, "rel-1", "implementation")
    assert status in {"ACQUIRED", "RENEWED"}


def _lease_heartbeat(workspace: Path, ctx: str) -> str:
    rec = lease.read_record(workspace, ctx)
    assert rec is not None
    return str(rec["heartbeat"])


# --- Resolution chain: stdin payload, env override only --------------------------------


def test_session_id_resolved_from_stdin_renews_lease(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # No DADAIA_SESSION_ID / native env var: id comes from the stdin payload.
    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    _seed_lease(tmp_path, "ctx", "stdin-sess")
    before = _lease_heartbeat(tmp_path, "ctx")

    # Drive the lease to an OLD-but-live heartbeat so renewal is observable.
    rec = lease.read_record(tmp_path, "ctx")
    assert rec is not None
    rec["heartbeat"] = (datetime.now(tz=UTC) - timedelta(seconds=30)).isoformat()
    lease._write_record(lease._record_path(tmp_path, "ctx"), rec)
    old = _lease_heartbeat(tmp_path, "ctx")

    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "stdin-sess"})
    assert sdd_post_gate.main() == 0
    after = _lease_heartbeat(tmp_path, "ctx")
    assert after != old
    assert before  # sanity


def test_env_var_overrides_stdin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # DADAIA_SESSION_ID override wins over the stdin session_id (resolve_session_id order).
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DADAIA_SESSION_ID", "override-sess")
    _seed_lease(tmp_path, "ctx", "override-sess")
    rec = lease.read_record(tmp_path, "ctx")
    assert rec is not None
    rec["heartbeat"] = (datetime.now(tz=UTC) - timedelta(seconds=30)).isoformat()
    lease._write_record(lease._record_path(tmp_path, "ctx"), rec)
    old = _lease_heartbeat(tmp_path, "ctx")

    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "stdin-loser"})
    assert sdd_post_gate.main() == 0
    assert _lease_heartbeat(tmp_path, "ctx") != old


# --- The retired no-op guard is gone: no DADAIA_SESSION_ID still does work --------------


def test_override_env_renews_when_stdin_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # DADAIA_SESSION_ID is the operator-override leg of the chain; with an empty stdin
    # payload it alone resolves the holder and renews the lease.
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DADAIA_SESSION_ID", "ovr-only")
    _seed_lease(tmp_path, "ctx", "ovr-only")
    rec = lease.read_record(tmp_path, "ctx")
    assert rec is not None
    rec["heartbeat"] = (datetime.now(tz=UTC) - timedelta(seconds=30)).isoformat()
    lease._write_record(lease._record_path(tmp_path, "ctx"), rec)
    old = _lease_heartbeat(tmp_path, "ctx")

    monkeypatch.setattr(_common, "read_stdin_json", lambda: {})
    assert sdd_post_gate.main() == 0
    assert _lease_heartbeat(tmp_path, "ctx") != old


def test_no_dadaia_session_id_still_renews(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # The old `if not os.environ.get("DADAIA_SESSION_ID"): return` guard is dead.
    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    _seed_lease(tmp_path, "ctx", "native-sess")
    rec = lease.read_record(tmp_path, "ctx")
    assert rec is not None
    rec["heartbeat"] = (datetime.now(tz=UTC) - timedelta(seconds=30)).isoformat()
    lease._write_record(lease._record_path(tmp_path, "ctx"), rec)
    old = _lease_heartbeat(tmp_path, "ctx")

    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "native-sess"})
    assert sdd_post_gate.main() == 0
    assert _lease_heartbeat(tmp_path, "ctx") != old


def test_empty_session_id_is_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {})
    assert sdd_post_gate.main() == 0


# --- Renewal context: held lease, not first-ALIVE; foreign not renewed -----------------


def test_only_held_lease_renewed_not_foreign(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DADAIA_SESSION_ID", "mine")
    # mine holds ctx-a; a different session holds ctx-b.
    _seed_lease(tmp_path, "ctx-a", "mine")
    _seed_lease(tmp_path, "ctx-b", "other")
    for ctx in ("ctx-a", "ctx-b"):
        rec = lease.read_record(tmp_path, ctx)
        assert rec is not None
        rec["heartbeat"] = (datetime.now(tz=UTC) - timedelta(seconds=30)).isoformat()
        lease._write_record(lease._record_path(tmp_path, ctx), rec)
    old_a = _lease_heartbeat(tmp_path, "ctx-a")
    old_b = _lease_heartbeat(tmp_path, "ctx-b")

    monkeypatch.setattr(_common, "read_stdin_json", lambda: {})
    assert sdd_post_gate.main() == 0

    assert _lease_heartbeat(tmp_path, "ctx-a") != old_a  # mine renewed
    assert _lease_heartbeat(tmp_path, "ctx-b") == old_b  # foreign untouched


def test_no_lease_held_exits_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DADAIA_SESSION_ID", "lonely")
    # A lease exists but is held by someone else; this session holds nothing.
    _seed_lease(tmp_path, "ctx", "someone-else")
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {})
    assert sdd_post_gate.main() == 0


# --- Renew runs outside the session-file guard -----------------------------------------


def test_lease_renews_without_session_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # No sessions/<id>.json on disk; the lease must still renew (FR-R2-01).
    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    _seed_lease(tmp_path, "ctx", "holder-no-file")
    rec = lease.read_record(tmp_path, "ctx")
    assert rec is not None
    rec["heartbeat"] = (datetime.now(tz=UTC) - timedelta(seconds=30)).isoformat()
    lease._write_record(lease._record_path(tmp_path, "ctx"), rec)
    old = _lease_heartbeat(tmp_path, "ctx")
    assert not (tmp_path / ".dadaia" / "sessions" / "holder-no-file.json").exists()

    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "holder-no-file"})
    assert sdd_post_gate.main() == 0
    assert _lease_heartbeat(tmp_path, "ctx") != old


# --- Parity (a): session-record refresh is atomic via os.replace -----------------------


def test_session_record_refresh_uses_os_replace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import os as _os
    from os import PathLike

    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    _seed_session_record(tmp_path, "repl-1")

    calls: list[tuple[str, str]] = []
    real_replace = _os.replace

    def spy(
        src: str | PathLike[str],
        dst: str | PathLike[str],
    ) -> None:
        calls.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(_os, "replace", spy)
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "repl-1"})
    assert sdd_post_gate.main() == 0
    assert len(calls) == 1
    assert list((tmp_path / ".dadaia" / "sessions").glob("*.tmp")) == []
    data = json.loads(
        (tmp_path / ".dadaia" / "sessions" / "repl-1.json").read_text(encoding="utf-8")
    )
    assert data["last_seen_at"] != "2026-01-01T00:00:00+00:00"


# --- Parity (b): session-id strip (CWE-22) via resolve_session_id ----------------------


def test_session_id_strip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sanitized = "etcpasswd"
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DADAIA_SESSION_ID", "../../etc/passwd")
    _seed_session_record(tmp_path, sanitized)
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {})
    assert sdd_post_gate.main() == 0
    record = json.loads(
        (tmp_path / ".dadaia" / "logs" / "lock-events.jsonl").read_text(encoding="utf-8").strip()
    )
    assert record["session_id"] == sanitized


# --- Parity (c): fail-open on every error path -----------------------------------------


def test_corrupt_session_file_fails_open(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "bad.json").write_text("{not json", encoding="utf-8")
    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "bad"})
    assert sdd_post_gate.main() == 0


def test_missing_session_file_is_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "ghost"})
    assert sdd_post_gate.main() == 0


def test_workspace_unresolvable_fails_open(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "x"})

    def boom() -> Path:
        raise RuntimeError("no workspace")

    monkeypatch.setattr(sdd_post_gate, "_resolve_workspace", boom)
    assert sdd_post_gate.main() == 0
