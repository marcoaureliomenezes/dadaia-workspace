"""Unit tests for dadaia_workspace.hooks.sdd_post_gate (R2a, FR-R2-01/02).

These are *in-process* unit tests of the hook's internals and the resolution-chain /
fail-open contract. They import the module directly, which is legitimate under the
zero-baseline harness-env contract (``tests/contract/test_harness_env_contract.py``):
that contract carries no per-file baseline data structure — it flags only the precise
harness-fiction pattern, importing a hook behavior module **and** patching ``sys.stdin``
in-process to drive its ``main()``. These tests drive ``main()`` by fault-injecting the
production ``_common.read_stdin_json`` symbol (``monkeypatch.setattr``) and never patch
``sys.stdin``, so the contract does not flag them. The harness-real *behavior* of the
hook — invoked as a subprocess with a ``claude_hook_env()`` and no hand-planted
``DADAIA_*`` — is proven in ``tests/unit/hooks/test_sdd_post_gate_behavior.py`` (which also
owns the stronger no-cross-renewal / held-vs-foreign coverage).

``DADAIA_SESSION_ID`` appears here only as the *operator override* leg of the resolution
chain (``resolve_session_id`` honors it first); the harness never sets it.

Mandatory parity preserved from rc-4:
  (a) session-record renewal via os.replace (atomic on Windows too) — owned by
      test_common.py's atomic_write_text roundtrip (shared primitive, single owner);
  (b) [A-Za-z0-9_-] session-id strip (CWE-22) — via resolve_session_id, CRIT, kept
      standalone below (redaction e2e half — lands in lock-events);
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


def _age_heartbeat(workspace: Path, ctx: str, *, seconds: int = 30) -> None:
    rec = lease.read_record(workspace, ctx)
    assert rec is not None
    rec["heartbeat"] = (datetime.now(tz=UTC) - timedelta(seconds=seconds)).isoformat()
    lease._write_record(lease._record_path(workspace, ctx), rec)


# --- Resolution chain x renewal: stdin payload / env override / no-session-file --------


@pytest.mark.parametrize(
    ("name", "session_id", "set_env_override", "stdin_payload_fn", "seed_session_file"),
    [
        # No DADAIA_SESSION_ID / native env var: id comes from the stdin payload.
        ("stdin_only", "stdin-sess", False, lambda sid: {"session_id": sid}, False),
        # DADAIA_SESSION_ID override wins over the stdin session_id (resolve_session_id
        # order).
        (
            "env_overrides_stdin",
            "override-sess",
            True,
            lambda sid: {"session_id": "stdin-loser"},
            False,
        ),
        # DADAIA_SESSION_ID is the operator-override leg of the chain; with an empty
        # stdin payload it alone resolves the holder and renews the lease.
        ("env_only_no_stdin", "ovr-only", True, lambda sid: {}, False),
        # The old `if not os.environ.get("DADAIA_SESSION_ID"): return` guard is dead —
        # no DADAIA_SESSION_ID still renews via the native/stdin resolution.
        (
            "no_dadaia_sid_still_renews",
            "native-sess",
            False,
            lambda sid: {"session_id": sid},
            False,
        ),
        # FR-R2-01: no sessions/<id>.json on disk; the lease must still renew (renewal
        # runs outside the session-file guard).
        (
            "renews_without_session_file",
            "holder-no-file",
            False,
            lambda sid: {"session_id": sid},
            False,
        ),
    ],
)
def test_sid_resolution_renewal_table(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
    session_id: str,
    set_env_override: bool,
    stdin_payload_fn: object,
    seed_session_file: bool,
) -> None:
    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    if set_env_override:
        monkeypatch.setenv("DADAIA_SESSION_ID", session_id)
    _seed_lease(tmp_path, "ctx", session_id)
    _age_heartbeat(tmp_path, "ctx")
    old = _lease_heartbeat(tmp_path, "ctx")
    if name == "renews_without_session_file":
        assert not (tmp_path / ".dadaia" / "sessions" / f"{session_id}.json").exists()

    monkeypatch.setattr(_common, "read_stdin_json", lambda: stdin_payload_fn(session_id))  # type: ignore[operator]
    assert sdd_post_gate.main() == 0
    assert _lease_heartbeat(tmp_path, "ctx") != old


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


def _setup_corrupt_session_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    (tmp_path / ".dadaia" / "sessions" / "bad.json").write_text("{not json", encoding="utf-8")
    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "bad"})


def _setup_missing_session_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "ghost"})


def _setup_workspace_unresolvable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_no_workspace() -> Path:
        raise RuntimeError("no workspace")

    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": "x"})
    monkeypatch.setattr(sdd_post_gate, "_resolve_workspace", _raise_no_workspace)


def _setup_empty_session_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _scrub_session_env(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {})


@pytest.mark.parametrize(
    ("name", "setup_fn"),
    [
        ("corrupt_session_file", _setup_corrupt_session_file),
        ("missing_session_file", _setup_missing_session_file),
        ("workspace_unresolvable", _setup_workspace_unresolvable),
        ("empty_session_id_is_noop", _setup_empty_session_id),
    ],
)
def test_fail_open_table(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, setup_fn: object
) -> None:
    setup_fn(tmp_path, monkeypatch)  # type: ignore[operator]
    assert sdd_post_gate.main() == 0
