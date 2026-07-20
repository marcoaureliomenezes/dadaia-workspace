"""v0.2.9 follow-up — bug context-delete-leaves-stale-session-bind.

Hermes repro (0.4.1 candidate): bind a context, ``dead`` it, ``delete`` it — the
session bind kept pointing at the removed context, and the next bind-resolved command
(``bugs status``) failed on the missing specs dir. Fixes: the resolver's existence
check (a bind to a deleted context resolves as unbound) and ``context delete``
removing the context's bind-epoch marker.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.specs_resolver import (
    _persisted_bind_context,
    _session_context,
    resolve_bound_context_name,
)
from dadaia_workspace.features.spec_context.service import SpecContextService

pytestmark = pytest.mark.unit

_PID = 990007


def _mk_ws(tmp_path: Path, slug: str = "reinject") -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": slug,
                        "repo_slug": slug,
                        "repo_url": "https://example.test/x.git",
                        "state": "alive",
                        "created_at": "2026-07-19T00:00:00Z",
                        "alive_since": "2026-07-19T00:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (states / "bind_epoch").mkdir()
    (tmp_path / "repos" / slug / "specs").mkdir(parents=True)
    return tmp_path


def _delete_registry_entry(tmp_path: Path) -> None:
    registry = tmp_path / ".dadaia" / "states" / "spec_contexts.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["contexts"] = []
    registry.write_text(json.dumps(data), encoding="utf-8")


def _write_session_record(tmp_path: Path, session_id: str, context: str) -> None:
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / f"{session_id}.json").write_text(
        json.dumps({"session_id": session_id, "context": context, "mode": "read"}),
        encoding="utf-8",
    )


def test_eval_flow_bind_to_deleted_context_resolves_unbound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The eval flow's no-gate exemption covers heartbeat-TTL staleness, never context
    existence: a bind to a DELETED context resolves unbound on every channel."""
    _mk_ws(tmp_path)
    _write_session_record(tmp_path, "sess-del", "reinject")
    monkeypatch.setenv("DADAIA_SESSION_ID", "sess-del")
    assert _session_context(tmp_path) == "reinject"

    _delete_registry_entry(tmp_path)
    assert _session_context(tmp_path) is None


def test_harness_channel_bind_to_deleted_context_resolves_unbound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The implicit harness channel never resolves a stale pointer (the bug)."""
    _mk_ws(tmp_path)
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    from datetime import UTC, datetime

    (sessions / "codex-1.json").write_text(
        json.dumps(
            {
                "session_id": "codex-1",
                "context": "reinject",
                "mode": "read",
                "last_seen_at": datetime.now(tz=UTC).isoformat(),
                "ttl_seconds": 300,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-1")
    assert _session_context(tmp_path) == "reinject"

    _delete_registry_entry(tmp_path)
    assert _session_context(tmp_path) is None


def test_marker_bind_to_deleted_context_resolves_unbound(tmp_path: Path) -> None:
    _mk_ws(tmp_path)
    marker = tmp_path / ".dadaia" / "states" / "bind_epoch" / "reinject"
    marker.write_text(f"{_PID}\n", encoding="utf-8")
    assert _persisted_bind_context(tmp_path, frozenset({_PID})) == "reinject"

    _delete_registry_entry(tmp_path)
    assert _persisted_bind_context(tmp_path, frozenset({_PID})) is None


def test_resolve_specs_dir_after_delete_gives_clean_unbound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hermes case: after dead+delete, a bind-resolved command sees NO context —
    the clean 'bind one or pass --specs-dir' path, never a missing-specs-dir failure."""
    _mk_ws(tmp_path)
    _write_session_record(tmp_path, "sess-del2", "reinject")
    monkeypatch.setenv("DADAIA_SESSION_ID", "sess-del2")
    monkeypatch.chdir(tmp_path / "repos" / "reinject")
    _delete_registry_entry(tmp_path)

    assert resolve_bound_context_name() is None


def test_registry_read_error_fails_open(tmp_path: Path) -> None:
    """A corrupt registry must NOT invalidate every live bind (fail-open)."""
    _mk_ws(tmp_path)
    marker = tmp_path / ".dadaia" / "states" / "bind_epoch" / "reinject"
    marker.write_text(f"{_PID}\n", encoding="utf-8")
    registry = tmp_path / ".dadaia" / "states" / "spec_contexts.json"
    registry.write_text("{not json", encoding="utf-8")
    assert _persisted_bind_context(tmp_path, frozenset({_PID})) == "reinject"


def test_context_delete_removes_the_bind_epoch_marker(tmp_path: Path) -> None:
    _mk_ws(tmp_path)
    marker = tmp_path / ".dadaia" / "states" / "bind_epoch" / "reinject"
    marker.write_text(f"{_PID}\n", encoding="utf-8")

    # The context must be dead first (alive contexts refuse deletion).
    registry = tmp_path / ".dadaia" / "states" / "spec_contexts.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["contexts"][0]["state"] = "dead"
    data["contexts"][0]["dead_since"] = "2026-07-19T01:00:00Z"
    registry.write_text(json.dumps(data), encoding="utf-8")

    from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
    from tests.fakes import FakeGitClient

    svc = SpecContextService(
        JsonContextStore(states_dir=tmp_path / ".dadaia" / "states"),
        FakeGitClient(),
        tmp_path,
    )
    svc.delete("reinject")

    assert not marker.exists()
    assert _persisted_bind_context(tmp_path, frozenset({_PID})) is None
