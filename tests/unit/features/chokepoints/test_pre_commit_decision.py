"""Presence-only pre-commit advisory tests for the NO-LOCKS doctrine."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.protocols.process_ancestry import Ancestry
from dadaia_workspace.features.chokepoints import pre_commit_decision
from dadaia_workspace.features.chokepoints.service import context_slug_for_path

_CTX = "demo-ctx"


def _presence(workspace: Path, session_id: str) -> None:
    path = workspace / ".dadaia" / "states" / "presence" / _CTX / f"{session_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "runtime": "codex",
                "pid": 4321,
                "started_at": now,
                "last_seen_at": now,
            }
        ),
        encoding="utf-8",
    )


def _decision(workspace: Path, *, env_sid: str | None = "caller"):
    def forbidden_probe(_pid: int) -> bool:
        raise AssertionError("retired pid probe must not run")

    def forbidden_ancestry(_ancestor: int, _descendant: int) -> Ancestry:
        raise AssertionError("retired ancestry probe must not run")

    return pre_commit_decision(
        workspace,
        _CTX,
        caller_pid=999,
        env_sid=env_sid,
        pid_probe=forbidden_probe,
        ancestry=forbidden_ancestry,
    )


def test_no_presence_always_allows_without_warning(tmp_path: Path) -> None:
    decision = _decision(tmp_path)
    assert decision.allowed
    assert decision.warn is None


def test_own_presence_is_excluded(tmp_path: Path) -> None:
    _presence(tmp_path, "caller")
    decision = _decision(tmp_path)
    assert decision.allowed
    assert decision.warn is None


def test_foreign_presence_allows_with_one_advisory(tmp_path: Path) -> None:
    _presence(tmp_path, "other-session")
    decision = _decision(tmp_path)
    assert decision.allowed
    assert decision.warn is not None
    assert "other-session" in decision.warn
    assert "NO-LOCKS DOCTRINE" in decision.warn
    for forbidden in ("rebind", "relaunch", "lock steal"):
        assert forbidden not in decision.warn.lower()


def test_non_context_path_always_allows(tmp_path: Path) -> None:
    decision = pre_commit_decision(
        tmp_path,
        None,
        caller_pid=999,
        env_sid=None,
        pid_probe=None,
        ancestry=lambda _a, _b: Ancestry.UNKNOWN,
    )
    assert decision.allowed
    assert decision.warn is None


def test_context_slug_for_path(tmp_path: Path) -> None:
    repo = tmp_path / "repos" / "my-service"
    repo.mkdir(parents=True)
    assert context_slug_for_path(tmp_path, repo) == "my-service"
    assert context_slug_for_path(tmp_path, tmp_path) is None
    nested = repo / "src"
    nested.mkdir()
    assert context_slug_for_path(tmp_path, nested) is None
