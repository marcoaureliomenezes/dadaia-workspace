"""v0.2.9 follow-up — bug context-delete-leaves-stale-session-bind.

Consumer repro (0.4.1 candidate): bind a context, ``dead`` it, ``delete`` it — the
session bind kept pointing at the removed context, and the next bind-resolved command
(``bugs status``) failed on the missing specs dir. Fix: the resolver's existence check
(a bind to a deleted context resolves as unbound).

T-50-04 (SPEC v0.5.0 FR1): the eval-flow (``DADAIA_SESSION_ID``) and bind-epoch-marker
cases this file used to pin die with the mechanisms they exercised
(``_session_context``'s ``DADAIA_SESSION_ID`` channel, ``_persisted_bind_context``, and
the marker ``context delete`` used to clean up). What survives is the harness-native
channel's own deleted-context guard, re-pointed at :func:`_live_session_context` — the
rung 2 the single authority (T-50-01) now uses.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.core.specs_resolver import _live_session_context

pytestmark = pytest.mark.unit


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
    (tmp_path / "repos" / slug / "specs").mkdir(parents=True)
    return tmp_path


def _delete_registry_entry(tmp_path: Path) -> None:
    registry = tmp_path / ".dadaia" / "states" / "spec_contexts.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["contexts"] = []
    registry.write_text(json.dumps(data), encoding="utf-8")


def test_harness_channel_bind_to_deleted_context_resolves_unbound(tmp_path: Path) -> None:
    """The harness-native channel never resolves a stale pointer (the bug)."""
    _mk_ws(tmp_path)
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
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
    assert _live_session_context(tmp_path) is None  # no harness id set: nothing resolves yet


def test_live_session_context_stops_resolving_once_context_is_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A LIVE harness-keyed record survives a context delete out from under it: the next
    resolution sees NO context — never a stale pointer."""
    _mk_ws(tmp_path)
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
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
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-1")
    assert _live_session_context(tmp_path) == "reinject"

    _delete_registry_entry(tmp_path)
    assert _live_session_context(tmp_path) is None
