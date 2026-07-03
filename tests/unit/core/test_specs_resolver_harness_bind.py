"""v0.1.55 FR4 (bug ``bugs-append-ignores-persisted-bind``): harness-native bind channel.

Root cause (review-confirmed): a codex ``dadaia bugs append`` is **not** a process-descendant
of the ``dadaia context bind`` session, so its ancestry chain is DISJOINT from the bind-epoch
marker's chain — ``_persisted_bind_context`` misses (membership fails) and ``resolve_specs_dir``
falls through to ``typer.BadParameter``.

The fix persists a session record keyed by the harness-native session id
(``CODEX_SESSION_ID`` / ``CLAUDE_CODE_SESSION_ID``) at ``bind``, and extends
``_session_context`` to resolve via that id when ``DADAIA_SESSION_ID`` is absent — **ahead of**
the ancestry path and **only when the referenced session record is LIVE** (heartbeat-fresh),
so a stale/inherited harness id can never cross-attribute to a foreign bound context.

These tests model the non-descendant case DETERMINISTICALLY — a bind-epoch marker with chain
``[A1, A2]`` resolved with a disjoint ``ancestry_pids`` frozenset ``{B1, B2}`` — with **no
spawned processes**: they seed the marker, seed the harness-keyed session record, and set the
harness env directly.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import typer

from dadaia_workspace.core import specs_resolver

# A marker chain and a resolving ancestry that share NO pid — the exact codex non-descendant
# shape (bind ran under one harness shell tree, `bugs append` under a disjoint one).
_MARKER_CHAIN = [70001, 70002]
_DISJOINT_ANCESTRY = frozenset({80001, 80002})
_HARNESS_ID = "codex-sess-fr4abcd"


@pytest.fixture(autouse=True)
def _clean_harness_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize every session-id / context env var so each test sets exactly what it needs.

    ``CLAUDE_CODE_SESSION_ID`` is deleted too: it is inherited by the test runner from the
    live Claude Code session, and (being resolved before ``CODEX_SESSION_ID``) would otherwise
    shadow the codex id these tests model.
    """
    for var in (
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
    ):
        monkeypatch.delenv(var, raising=False)


def _mk_ws(tmp_path: Path, *, slug: str = "proj") -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": [{"repo_slug": slug, "state": "alive"}]}),
        encoding="utf-8",
    )
    (states / "bind_epoch").mkdir()
    (tmp_path / "repos" / slug / "specs").mkdir(parents=True)
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    return tmp_path


def _stamp_marker(ws: Path, slug: str, chain: list[int]) -> None:
    (ws / ".dadaia" / "states" / "bind_epoch" / slug).write_text(
        "".join(f"{p}\n" for p in chain), encoding="utf-8"
    )


def _write_harness_record(
    ws: Path, harness_id: str, ctx: str, *, age_seconds: int = 0, ttl: int = 300
) -> None:
    """Seed ``sessions/<harness_id>.json`` as ``bind`` would, with a controllable heartbeat age."""
    last_seen = (datetime.now(tz=UTC) - timedelta(seconds=age_seconds)).isoformat()
    (ws / ".dadaia" / "sessions" / f"{harness_id}.json").write_text(
        json.dumps(
            {
                "session_id": harness_id,
                "context": ctx,
                "mode": "READ",
                "last_seen_at": last_seen,
                "ttl_seconds": ttl,
                # The transient bind-CLI pid is dead by construction (ADR-8); liveness rides
                # last_seen_at, so a real-but-not-this-process pid must not vet resolution.
                "pid": 424242,
            }
        ),
        encoding="utf-8",
    )


# --- (i) non-descendant resolve via the harness-id channel (RED pre-fix) ---------


def test_disjoint_ancestry_resolves_via_live_harness_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(i) GREEN: disjoint ancestry (marker unattributable) + a LIVE harness-keyed session
    record ⇒ the bound context resolves via the harness channel.

    RED pre-fix: with no harness channel the disjoint ancestry falls through to BadParameter.
    """
    ws = _mk_ws(tmp_path, slug="proj")
    _stamp_marker(ws, "proj", _MARKER_CHAIN)
    _write_harness_record(ws, _HARNESS_ID, "proj", age_seconds=0)
    monkeypatch.setenv("CODEX_SESSION_ID", _HARNESS_ID)
    monkeypatch.chdir(ws)

    resolved = specs_resolver.resolve_specs_dir(None, ancestry_pids=_DISJOINT_ANCESTRY)
    assert resolved == (ws / "repos" / "proj" / "specs").resolve()


def test_session_context_reads_harness_record_when_no_dadaia_session_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The channel lives in ``_session_context``: it returns the bound context of the live
    harness-keyed record (drives the SAME channel the fix wires — not a slope test)."""
    ws = _mk_ws(tmp_path, slug="proj")
    _write_harness_record(ws, _HARNESS_ID, "proj", age_seconds=0)
    monkeypatch.setenv("CODEX_SESSION_ID", _HARNESS_ID)
    assert specs_resolver._session_context(ws) == "proj"


# --- (ii) concurrent multi-session safety — never cross-attribute -----------------


def test_two_markers_disjoint_chains_never_cross_attribute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(ii) Two bind-epoch markers with disjoint chains; the ancestry matches EXACTLY one ⇒
    that one resolves and the other is never cross-attributed (concurrent-session safety)."""
    ws = _mk_ws(tmp_path, slug="ctxa")
    (ws / "repos" / "ctxb" / "specs").mkdir(parents=True)
    _stamp_marker(ws, "ctxa", [90001, 90002])
    _stamp_marker(ws, "ctxb", [91001, 91002])
    # Ancestry shares a pid with ctxa's chain ONLY.
    assert specs_resolver._persisted_bind_context(ws, frozenset({12345, 90002})) == "ctxa"
    # Ancestry disjoint from both ⇒ neither is attributed (no blind fallback).
    assert specs_resolver._persisted_bind_context(ws, frozenset({999, 998})) is None


# --- (iii) descendant / same-shell case still resolves (ancestry path unchanged) --


def test_descendant_ancestry_still_resolves_via_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(iii) A descendant (ancestry sharing a pid with the marker chain) still resolves via the
    unchanged ancestry-membership path — no harness record needed."""
    ws = _mk_ws(tmp_path, slug="proj")
    _stamp_marker(ws, "proj", [70001, 70002, 70003])
    monkeypatch.chdir(ws)
    resolved = specs_resolver.resolve_specs_dir(None, ancestry_pids=frozenset({999, 70002}))
    assert resolved == (ws / "repos" / "proj" / "specs").resolve()


# --- (iv) stale / inherited harness id must NOT resolve to a foreign context ------


def test_stale_harness_record_does_not_resolve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(iv) A STALE (heartbeat-old) harness-keyed record must NOT resolve — an inherited/stale
    harness id can never cross-attribute to a foreign bound context. Falls through to the
    actionable BadParameter (never a blind first-ALIVE fallback)."""
    ws = _mk_ws(tmp_path, slug="proj")
    _stamp_marker(ws, "proj", _MARKER_CHAIN)  # disjoint from the resolving ancestry below
    # Heartbeat far older than the TTL ⇒ the staleness guard rejects it.
    _write_harness_record(ws, _HARNESS_ID, "proj", age_seconds=4000, ttl=300)
    monkeypatch.setenv("CODEX_SESSION_ID", _HARNESS_ID)
    monkeypatch.chdir(ws)

    assert specs_resolver._session_context(ws) is None
    with pytest.raises(typer.BadParameter):
        specs_resolver.resolve_specs_dir(None, ancestry_pids=_DISJOINT_ANCESTRY)


def test_absent_harness_record_does_not_resolve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A harness id whose session record does not exist (never bound) ⇒ no resolution."""
    ws = _mk_ws(tmp_path, slug="proj")
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-never-bound")
    assert specs_resolver._session_context(ws) is None


def test_dadaia_session_id_still_wins_over_harness_channel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The eval-flow ``DADAIA_SESSION_ID`` path is unchanged and takes precedence; the
    harness channel only engages when ``DADAIA_SESSION_ID`` is absent."""
    ws = _mk_ws(tmp_path, slug="proj")
    (ws / "repos" / "other" / "specs").mkdir(parents=True)
    # Eval-flow record (no liveness gate) → ctx=other; harness record → ctx=proj.
    (ws / ".dadaia" / "sessions" / "sess_eval01.json").write_text(
        json.dumps({"session_id": "sess_eval01", "context": "other"}), encoding="utf-8"
    )
    _write_harness_record(ws, _HARNESS_ID, "proj", age_seconds=0)
    monkeypatch.setenv("DADAIA_SESSION_ID", "sess_eval01")
    monkeypatch.setenv("CODEX_SESSION_ID", _HARNESS_ID)
    assert specs_resolver._session_context(ws) == "other"
