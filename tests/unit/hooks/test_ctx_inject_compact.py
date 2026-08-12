"""v0.2.8 T4 — ctx_inject compact-epoch: PostCompact marker + re-injection.

Drives ``ctx_inject`` as a real subprocess (the harness-real fixture) through the full
kimi-code compaction flow: ``UserPromptSubmit`` injections, the ``PostCompact`` event
(stamps ``ctx-compact-<sid>`` AND re-emits the bootstrap on stdout — the observable
contract; Kimi discards PostCompact stdout), and the next-prompt re-injection that
fires exactly once. Also covers the unbound-session variant (generic preflight).

T-50-03 (SPEC v0.5.0 FR1 coupling 1): a NORMAL (``UserPromptSubmit``) bind is simulated
via :func:`_bind_session` (a self-keyed session record with a ``bound_at`` timestamp —
the same field ``dadaia context bind`` persists), not a bind-epoch marker: the marker
subsystem is no longer consulted by the injection path (T-50-04 deletes it outright). The
PostCompact and SessionStart(compact|clear) event blocks are UNCHANGED by this task —
they resolve context unconditionally (no sentinel/``bound_at`` gating) and emit every
time they fire, per ``CONSUMER_VALIDATION_RECIPE.md:376``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import session_identity
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = pytest.mark.unit

_PID_A = 990001


def _ws(tmp_path: Path, slug: str = "ctx") -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": slug, "state": "alive"}]}),
        encoding="utf-8",
    )
    mem = tmp_path / "repos" / slug / "specs" / "memory"
    mem.mkdir(parents=True)
    (mem / "tech-stack.md").write_text("# tech\nPython 3.12\n", encoding="utf-8")
    (mem / "product").mkdir()
    (mem / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    return tmp_path


def _bind_session(tmp_path: Path, session_id: str, context: str) -> None:
    """Simulate a NORMAL ``dadaia context bind <context>`` for *session_id* (T-50-03).

    Writes/refreshes the self-keyed session record with ``context`` and a ``bound_at``
    ISO timestamp of "now" — the field the injection trigger (T-50-03) compares against
    the sentinel's mtime.
    """
    session_identity.write_session(
        tmp_path,
        session_id,
        {
            "session_id": session_id,
            "context": context,
            "mode": "read",
            "bound_at": datetime.now(tz=UTC).isoformat(),
        },
    )


def _run(tmp_path: Path, session_id: str, *, event: str | None = None) -> str:
    extra = {"DADAIA_HOOK_EVENT": event} if event else None
    env = claude_hook_env(tmp_path, extra=extra)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    result = run_hook_subprocess(
        "ctx_inject", {"session_id": session_id, "harness_pid": _PID_A}, env
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _compact_marker(tmp_path: Path, session_id: str) -> Path:
    return tmp_path / ".dadaia" / "tmp" / f"ctx-compact-{session_id}"


def test_post_compact_stamps_marker_and_reemits_observably(tmp_path: Path) -> None:
    """PostCompact: marker written + generic preflight re-emitted (unbound session)."""
    _ws(tmp_path)
    out = _run(tmp_path, "sess-1", event="PostCompact")
    assert _compact_marker(tmp_path, "sess-1").is_file()
    # Observable contract: PostCompact re-emits (never silence).
    assert "[no bound context]" in out


def test_bound_session_reinjects_once_after_compact(tmp_path: Path) -> None:
    _ws(tmp_path)
    sid = "sess-2"

    # Fresh session: generic preflight (sentinel stamped), then bind, then injection.
    assert "[no bound context]" in _run(tmp_path, sid)
    _bind_session(tmp_path, sid, "ctx")
    assert "[ctx]" in _run(tmp_path, sid)
    # Repeat prompt: silent.
    assert _run(tmp_path, sid) == ""

    # Compaction: marker + observable re-emission of the bound context's bootstrap…
    out = _run(tmp_path, sid, event="PostCompact")
    assert "[ctx]" in out
    assert "dispatcher preflight" in out
    # …but the sentinel was NOT restamped: the NEXT prompt re-injects (the deterministic
    # path — Kimi discards PostCompact stdout, so the model really gets it here).
    out = _run(tmp_path, sid)
    assert "[ctx]" in out
    # And after that: silent again (exactly-once discipline).
    assert _run(tmp_path, sid) == ""


def test_unbound_session_reemits_generic_preflight_after_compact(tmp_path: Path) -> None:
    _ws(tmp_path)
    sid = "sess-3"

    assert "[no bound context]" in _run(tmp_path, sid)
    assert _run(tmp_path, sid) == ""

    assert "[no bound context]" in _run(tmp_path, sid, event="PostCompact")
    assert "[no bound context]" in _run(tmp_path, sid)
    assert _run(tmp_path, sid) == ""


def test_compact_without_self_keyed_record_or_env_does_not_bind(tmp_path: Path) -> None:
    """A PostCompact event on a session with no self-keyed record and no ``DADAIA_CONTEXT``
    must not inject context memory."""
    _ws(tmp_path)
    sid = "sess-4"
    assert "[no bound context]" in _run(tmp_path, sid, event="PostCompact")
    # Fresh session: still only the generic preflight (no session record, no env var).
    assert "[no bound context]" in _run(tmp_path, sid)


def test_post_compact_resolves_bound_context_from_session_record(tmp_path: Path) -> None:
    """Consumer round-3 bug (kimi-postcompact-omits-bound-context-bootstrap): a bind with
    NO prior prompt leaves no sentinel file, but the session record names the bound
    context — PostCompact must emit THAT context's bootstrap, not the generic preflight.
    """
    _ws(tmp_path)
    sid = "sess-5"
    # Bind flow: the session record exists (bind CLI wrote it), no sentinel, no marker.
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / f"{sid}.json").write_text(
        json.dumps({"session_id": sid, "context": "ctx", "mode": "implementation"}),
        encoding="utf-8",
    )
    out = _run(tmp_path, sid, event="PostCompact")
    assert "[ctx]" in out
    assert "dispatcher preflight" in out
    assert _compact_marker(tmp_path, sid).is_file()
    # And the next prompt (first real prompt) resolves the same context and injects.
    assert "[ctx]" in _run(tmp_path, sid)


# --------------------------------------------------------------------------- #
# Claude Code SessionStart re-injection (bug claude-compact-reinjection-missing)
# --------------------------------------------------------------------------- #


def _run_session_start(tmp_path: Path, session_id: str, source: str) -> str:
    """Drive ctx_inject with a Claude Code SessionStart payload (no env event var)."""
    env = claude_hook_env(tmp_path)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    payload = {
        "session_id": session_id,
        "harness_pid": _PID_A,
        "hook_event_name": "SessionStart",
        "source": source,
    }
    result = run_hook_subprocess("ctx_inject", payload, env)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_claude_session_start_compact_reinjects_and_restamps(tmp_path: Path) -> None:
    """Bug claude-compact-reinjection-missing: SessionStart(compact) re-injects NOW.

    Claude Code consumes SessionStart stdout as injected context (unlike Kimi's
    discard-stdout PostCompact), so the bootstrap re-emits at the event itself and the
    sentinel is restamped immediately — the NEXT prompt stays silent (no double
    injection) and no kimi compact marker is left behind.
    """
    _ws(tmp_path)
    sid = "sess-cc1"
    assert "[no bound context]" in _run(tmp_path, sid)
    _bind_session(tmp_path, sid, "ctx")
    assert "[ctx]" in _run(tmp_path, sid)
    assert _run(tmp_path, sid) == ""

    out = _run_session_start(tmp_path, sid, "compact")
    assert "[ctx]" in out
    assert "dispatcher preflight" in out
    assert not _compact_marker(tmp_path, sid).exists()
    # Sentinel restamped at the event: the following prompt is silent again.
    assert _run(tmp_path, sid) == ""


def test_claude_session_start_clear_reinjects_bound_context(tmp_path: Path) -> None:
    """SessionStart(clear): a still-bound session gets its bootstrap back at once (the
    bind survives /clear — only the conversation was wiped), and the restamped sentinel
    keeps the following prompt silent. An unbound wiped session gets the generic
    preflight back the same way."""
    _ws(tmp_path)
    sid = "sess-cc2"
    assert "[no bound context]" in _run(tmp_path, sid)
    _bind_session(tmp_path, sid, "ctx")
    assert "[ctx]" in _run(tmp_path, sid)
    assert _run(tmp_path, sid) == ""

    out = _run_session_start(tmp_path, sid, "clear")
    assert "[ctx]" in out
    assert _run(tmp_path, sid) == ""

    sid2 = "sess-cc2b"
    assert "[no bound context]" in _run_session_start(tmp_path, sid2, "clear")
    assert _run(tmp_path, sid2) == ""


def test_claude_session_start_other_sources_follow_normal_flow(tmp_path: Path) -> None:
    """A SessionStart source outside {compact, clear} is NOT a re-inject trigger — a
    bound repeat session stays silent exactly like a repeat prompt."""
    _ws(tmp_path)
    sid = "sess-cc3"
    assert "[no bound context]" in _run(tmp_path, sid)
    _bind_session(tmp_path, sid, "ctx")
    assert "[ctx]" in _run(tmp_path, sid)
    assert _run_session_start(tmp_path, sid, "startup") == ""
