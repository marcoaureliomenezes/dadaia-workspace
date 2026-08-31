"""Presence-only pre-commit advisory tests for the NO-LOCKS doctrine.

Intent: CONTRACT — v0.1.76 FR3 (NO-LOCKS WARN-only); v0.5.1 K7 (injected
``others_alive`` — the real ``spec_context.presence.others_alive`` is wired straight
through here, exactly as the CLI composition root wires it, proving the injection
seam works with zero adapter).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.features.chokepoints import pre_commit_decision
from dadaia_workspace.features.chokepoints.branch_policy import context_slug_for_path
from dadaia_workspace.features.spec_context import presence

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


def _decision(workspace: Path, ctx: str | None = _CTX, *, env_sid: str | None = "caller"):
    return pre_commit_decision(
        workspace,
        ctx,
        env_sid=env_sid,
        others_alive=presence.others_alive,
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
    def forbidden_others_alive(_workspace: Path, _ctx: str, _sid: str) -> list[object]:
        raise AssertionError("others_alive must never run for a non-context path")

    decision = pre_commit_decision(
        tmp_path,
        None,
        env_sid=None,
        others_alive=forbidden_others_alive,  # type: ignore[arg-type]
    )
    assert decision.allowed
    assert decision.warn is None


@pytest.mark.parametrize("env_sid", [None, ""], ids=["none", "empty-string"])
def test_missing_env_sid_falls_back_to_the_anonymous_own_sid(
    tmp_path: Path, env_sid: str | None
) -> None:
    """The injected ``others_alive`` still receives a non-empty own-sid string even
    when the caller supplies no ``DADAIA_SESSION_ID`` — mirrors the pre-K7 fallback."""
    seen: list[str] = []

    def _spy(_workspace: Path, _ctx: str, sid: str) -> list[object]:
        seen.append(sid)
        return []

    decision = pre_commit_decision(tmp_path, _CTX, env_sid=env_sid, others_alive=_spy)
    assert decision.allowed
    assert seen == ["pre-commit-anonymous"]


def test_context_slug_for_path(tmp_path: Path) -> None:
    repo = tmp_path / "repos" / "my-service"
    repo.mkdir(parents=True)
    assert context_slug_for_path(tmp_path, repo) == "my-service"
    assert context_slug_for_path(tmp_path, tmp_path) is None
    nested = repo / "src"
    nested.mkdir()
    assert context_slug_for_path(tmp_path, nested) is None


# ── bundled-ledger advisory (F015/F036, 20260827-canon-v6-first-audit) ──────────────


def test_bundled_ledger_advisory_warns_when_ledger_staged_with_other_specs_paths() -> None:
    from dadaia_workspace.features.chokepoints import bundled_ledger_advisory

    warn = bundled_ledger_advisory(
        ["specs/bugs/BUGS.jsonl", "specs/releases/0.5.2/TASKS.md", "dadaia_workspace/x.py"]
    )
    assert warn is not None
    assert "BUGS.jsonl" in warn
    assert "allowed" in warn  # NO-LOCKS: advisory only, the commit proceeds.


def test_bundled_ledger_advisory_silent_for_shape1_ledger_alone() -> None:
    from dadaia_workspace.features.chokepoints import bundled_ledger_advisory

    assert bundled_ledger_advisory(["specs/bugs/BUGS.jsonl"]) is None


def test_bundled_ledger_advisory_silent_for_shape3_code_plus_ledger() -> None:
    from dadaia_workspace.features.chokepoints import bundled_ledger_advisory

    staged = [
        "specs/bugs/BUGS.jsonl",
        "dadaia_workspace/core/x.py",
        "tests/unit/core/test_x.py",
    ]
    assert bundled_ledger_advisory(staged) is None


def test_bundled_ledger_advisory_silent_without_the_ledger() -> None:
    from dadaia_workspace.features.chokepoints import bundled_ledger_advisory

    assert bundled_ledger_advisory(["specs/releases/0.5.2/TASKS.md"]) is None


def test_bundled_ledger_advisory_tolerates_backslash_paths() -> None:
    from dadaia_workspace.features.chokepoints import bundled_ledger_advisory

    warn = bundled_ledger_advisory(["specs\\bugs\\BUGS.jsonl", "specs\\memory\\QUALITY.md"])
    assert warn is not None
