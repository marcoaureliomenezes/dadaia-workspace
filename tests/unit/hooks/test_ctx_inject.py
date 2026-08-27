"""Harness-real behavior tests for dadaia_workspace.hooks.ctx_inject.

These drive ``ctx_inject`` exactly as a real harness does: a subprocess spawned with
:func:`claude_hook_env` / :func:`codex_hook_env` (pinned-minimal env, no hand-planted
``DADAIA_*`` session/persona/mode vars) and the prompt payload piped to stdin. The session
id flows through the stdin ``session_id`` field, the only channel a real harness provides;
the output contract (``DADAIA_HOOK_OUTPUT`` / ``DADAIA_HOOK_EVENT``) is passed through the
*subprocess* env via the fixture's ``extra`` — the harness-wiring channel — never an
in-process ``setenv``.

Bind-driven injection (FR-W2-01 / FR-W2-02, v0.1.14; bound_at trigger, T-50-03)
--------------------------------------------------------------------------------
The first-ALIVE fallback is DELETED from injection. An UNBOUND session now yields generic
preflight (``[no bound context]`` + dispatcher preflight + ALIVE list) with NO context
memory. Context NAME resolution delegates to the single authority (T-50-03, SPEC v0.5.0
FR1): this session's own self-keyed session record → ``DADAIA_CONTEXT`` env → this
session's own live harness-native record → the repo containing cwd. The bind-epoch marker
subsystem is NO LONGER consulted by the injection path — a session bound only via a
marker (no harness id, no ``DADAIA_CONTEXT``) no longer resolves a context (the accepted
FR1 coupling); T-50-04 deletes the marker-attribution algorithm and its harness-pid
resolver outright (both were already uncalled from the injection path).

The INJECTION TRIGGER is this session's own session record ``bound_at`` (written by
``dadaia context bind``) compared against the sentinel's mtime — not the bind-epoch marker
mtime. A same-context re-bind now re-injects (new pin, T-50-03).

CRIT: bind-driven injection survives below. The sentinel filename byte-parity test is
DELETED — the digest-GC tests (test_ctx_inject_digest.py) construct the same
``ctx-inject-fired-<sid>`` names and would break on a rename, so the filename contract is
already pinned implicitly.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.spec_context import session_identity
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess


def _ws(tmp_path: Path, slug: str = "ctx", *, with_memory: bool = True) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": slug, "state": "alive"}]}),
        encoding="utf-8",
    )
    specs = tmp_path / "repos" / slug / "specs"
    specs.mkdir(parents=True)
    if with_memory:
        mem = specs / "memory"
        mem.mkdir()
        (mem / "TECHSTACK.md").write_text("# tech\nPython 3.12\n", encoding="utf-8")
        (mem / "product").mkdir()
        (mem / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    return tmp_path


def _add_context(tmp_path: Path, slug: str, *, with_memory: bool = True) -> None:
    """Add a second ALIVE context + its memory to an already-built workspace."""
    states = tmp_path / ".dadaia" / "states"
    data = json.loads((states / "spec_contexts.json").read_text(encoding="utf-8"))
    data["contexts"].append({"repo_slug": slug, "state": "alive"})
    (states / "spec_contexts.json").write_text(json.dumps(data), encoding="utf-8")
    specs = tmp_path / "repos" / slug / "specs"
    specs.mkdir(parents=True)
    if with_memory:
        mem = specs / "memory"
        mem.mkdir()
        (mem / "TECHSTACK.md").write_text(f"# tech {slug}\nNode 20\n", encoding="utf-8")
        (mem / "product").mkdir()
        (mem / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")


def _bind_session(tmp_path: Path, session_id: str, context: str) -> None:
    """Simulate ``dadaia context bind <context>`` for *session_id* (T-50-03).

    Writes/refreshes the self-keyed session record with ``context`` and a ``bound_at``
    ISO timestamp of "now" — the same field ``cli/commands/context.py:bind`` persists on
    every successful bind, including a same-context re-bind (which refreshes it). The
    injection trigger (``ctx_inject._session_bound_at``) compares this against the
    sentinel's mtime, so calling this AFTER a prior sentinel stamp and BEFORE the next
    ``_run`` deterministically produces a ``bound_at`` newer than that sentinel — real
    wall-clock ordering across sequential, single-threaded calls, no synthetic offset
    needed.
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


def _run(
    tmp_path: Path,
    session_id: str,
    *,
    extra: dict[str, str] | None = None,
) -> str:
    """Invoke ctx_inject as a real subprocess; return its stdout.

    The session id is delivered the harness-real way: the stdin ``session_id`` field, with a
    clean env that carries no native session-id var (``claude_hook_env`` then pops it so the
    stdin field wins resolution). ``extra`` supplies harness-control output-contract vars.
    ``DADAIA_CONTEXT`` is popped so context resolution comes only from the bound session
    record (a developer shell exporting it must not leak into these tmp-workspace runs).
    """
    env = claude_hook_env(tmp_path, extra=extra)
    env.pop("CLAUDE_CODE_SESSION_ID", None)  # force resolution from the stdin field
    env.pop("DADAIA_CONTEXT", None)  # context comes only from the bound session record
    payload: dict[str, object] = {"session_id": session_id}
    result = run_hook_subprocess("ctx_inject", payload, env)
    assert result.returncode == 0, result.stderr
    return result.stdout


# --- FR-W2-01: unbound / no-context ⇒ generic preflight, NO context memory ----


def _setup_unbound_session_no_memory(tp: Path) -> None:
    _ws(tp)


def _setup_unbound_session_lists_alive_contexts(tp: Path) -> None:
    _ws(tp, slug="alpha")
    _add_context(tp, "beta")


def _setup_no_alive_context_still_generic(tp: Path) -> None:
    (tp / ".dadaia" / "states").mkdir(parents=True)
    (tp / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": "x", "state": "dead"}]}),
        encoding="utf-8",
    )


def _assert_unbound_no_memory(out: str) -> bool:
    return (
        "[no bound context]" in out
        and "dispatcher preflight" not in out
        and "end memory bootstrap" not in out
        and "Python 3.12" not in out
    )


def _assert_lists_alive_contexts(out: str) -> bool:
    return "ALIVE contexts" in out and "- alpha" in out and "- beta" in out


def _assert_no_alive_context_still_generic(out: str) -> bool:
    return "[no bound context]" in out and "end memory bootstrap" not in out


def _setup_foreign_session_bind_never_leaks(tp: Path) -> None:
    """FR-W2-02 re-proof under the T-50-03 bound_at trigger.

    A DIFFERENT session ("other-sess") is bound to "ctx" (a real self-keyed session
    record, not a marker). THIS test's session ("fresh", no record of its own, no
    DADAIA_CONTEXT) must never resolve — or inject — that foreign binding. Name
    resolution's self-keyed leg is scoped by session id by construction, so this also
    proves there is no cross-session leak through the single authority.
    """
    _ws(tp)
    _bind_session(tp, "other-sess", "ctx")


@pytest.mark.parametrize(
    ("name", "setup_fn", "session_id", "assert_fn"),
    [
        (
            "unbound_session_no_memory",
            _setup_unbound_session_no_memory,
            "s1",
            _assert_unbound_no_memory,
        ),
        (
            "unbound_session_lists_alive_contexts",
            _setup_unbound_session_lists_alive_contexts,
            "s-list",
            _assert_lists_alive_contexts,
        ),
        (
            "no_alive_context_still_generic",
            _setup_no_alive_context_still_generic,
            "s",
            _assert_no_alive_context_still_generic,
        ),
        (
            "foreign_session_bind_never_leaks_into_fresh_session",
            _setup_foreign_session_bind_never_leaks,
            "fresh",
            _assert_unbound_no_memory,
        ),
    ],
)
def test_no_bind_generic_preflight_table(
    tmp_path: Path, name: str, setup_fn: Any, session_id: str, assert_fn: Any
) -> None:
    setup_fn(tmp_path)
    out = _run(tmp_path, session_id)
    assert assert_fn(out)


# --- FR-W2-01 priority-2: self-keyed session record (bound context) wins ------


def test_session_record_binds_context_over_first_alive(tmp_path: Path) -> None:
    # REGRESSION repro for bug `ctx-inject-ignores-session-bind-first-alive-proxy`
    # (T-014-10): a DIFFERENT context (beta) is listed FIRST-ALIVE in the registry, but the
    # hook session's self-keyed session record binds it to alpha. The resolution chain's
    # priority-2 leg (_session_bound_context) must deliver alpha — NEVER the first-ALIVE
    # proxy beta (whose injection path is DELETED). This exercises the session-record leg
    # that the rest of the suite covers only by absence (read_session is None elsewhere).
    _ws(tmp_path, slug="beta")  # beta is the FIRST-ALIVE entry in the registry
    _add_context(tmp_path, "alpha")  # alpha second; its memory says "Node 20"
    sid = "bound-sid"
    # The hook session id (stdin session_id field) carries its OWN bound record → alpha.
    session_identity.write_session(tmp_path, sid, {"id": sid, "context": "alpha"})
    out = _run(tmp_path, sid)
    assert "[alpha]" in out
    assert "end memory bootstrap" in out
    assert "Node 20" in out  # alpha's memory, not beta's
    # beta (first-ALIVE) must NEVER be injected.
    assert "[beta]" not in out


# --- DADAIA_CONTEXT env override still injects memory -------------------------


def test_env_override_injects_context_memory(tmp_path: Path) -> None:
    _ws(tmp_path)
    env = claude_hook_env(tmp_path, extra={"DADAIA_CONTEXT": "ctx"})
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    result = run_hook_subprocess("ctx_inject", {"session_id": "envsid"}, env)
    assert result.returncode == 0, result.stderr
    assert "[ctx]" in result.stdout
    assert "end memory bootstrap" in result.stdout
    assert "Python 3.12" in result.stdout


# --- T-50-03: bound_at drives the injection trigger ---------------------------


def test_bind_via_session_record_drives_injection_then_rebind_and_repeat_prompt(
    tmp_path: Path,
) -> None:
    """The injection trigger is this session's own record ``bound_at`` vs the sentinel
    (T-50-03, SPEC v0.5.0 FR1 coupling 1) — not a bind-epoch marker.

    Covers: injection fires once per bind and not on a re-prompt; a rebind to a DIFFERENT
    context re-injects; a repeat prompt with no new bind stays silent.
    """
    _ws(tmp_path)
    # First prompt: unbound ⇒ generic, stamps the sentinel.
    first = _run(tmp_path, "sess")
    assert "[no bound context]" in first

    # A bind (self-keyed session record, bound_at = now) ⇒ next prompt injects the context.
    _bind_session(tmp_path, "sess", "ctx")
    second = _run(tmp_path, "sess")
    assert "[ctx]" in second
    assert "end memory bootstrap" in second
    assert "Python 3.12" in second

    # Repeat prompt, no new bind ⇒ silent.
    assert _run(tmp_path, "sess") == ""

    # Re-bind to a DIFFERENT context ⇒ re-injects (the resolved name changed).
    ws2 = tmp_path.parent / (tmp_path.name + "-rebind")
    _ws(ws2, slug="alpha")
    _add_context(ws2, "beta")
    # First prompt establishes the sentinel.
    _run(ws2, "rb")
    _bind_session(ws2, "rb", "alpha")
    out_a = _run(ws2, "rb")
    assert "[alpha]" in out_a
    _bind_session(ws2, "rb", "beta")
    out_b = _run(ws2, "rb")
    assert "[beta]" in out_b
    assert "Node 20" in out_b
    # A repeat prompt with NO new bind ⇒ silent.
    assert _run(ws2, "rb") == ""


def test_same_context_rebind_reinjects(tmp_path: Path) -> None:
    """New pin (T-50-03, SPEC v0.5.0 FR1 coupling 1): a SAME-CONTEXT re-bind now
    re-injects — a re-bind is how a mode/release change reaches a live session, which
    the OLD ``recorded_slug == context`` guard alone could never deliver.
    """
    _ws(tmp_path)
    sid = "same-ctx-sess"
    assert "[no bound context]" in _run(tmp_path, sid)

    _bind_session(tmp_path, sid, "ctx")
    first_inject = _run(tmp_path, sid)
    assert "[ctx]" in first_inject

    # Repeat prompt, no new bind ⇒ silent (baseline: still true).
    assert _run(tmp_path, sid) == ""

    # SAME-CONTEXT re-bind: a fresh bound_at re-injects even though the resolved name is
    # unchanged.
    _bind_session(tmp_path, sid, "ctx")
    reinjected = _run(tmp_path, sid)
    assert "[ctx]" in reinjected
    assert "end memory bootstrap" in reinjected

    # And a subsequent repeat prompt (no further bind) goes silent again.
    assert _run(tmp_path, sid) == ""


# --- output-contract envelopes (unchanged contract, generic-preflight payload) ---


@pytest.mark.parametrize(
    ("name", "extra", "session_id", "expect_event"),
    [
        (
            "codex_json_envelope",
            {"DADAIA_HOOK_OUTPUT": "codex-json", "DADAIA_HOOK_EVENT": "SessionStart"},
            "s2",
            "SessionStart",
        ),
        (
            "json_output_default_event",
            {"DADAIA_HOOK_OUTPUT": "json"},
            "s3",
            "UserPromptSubmit",
        ),
    ],
)
def test_output_contract_envelopes(
    tmp_path: Path, name: str, extra: dict[str, str], session_id: str, expect_event: str
) -> None:
    _ws(tmp_path)
    out = _run(tmp_path, session_id, extra=extra)
    env = json.loads(out)
    assert env["hookSpecificOutput"]["hookEventName"] == expect_event
    if name == "codex_json_envelope":
        assert "[no bound context]" in env["hookSpecificOutput"]["additionalContext"]


# --- FR30 (T-044-60, A30.1): dispatcher preflight restatement is deleted ------


def test_bound_session_carries_no_dispatcher_preflight_and_no_context_list(
    tmp_path: Path,
) -> None:
    """A30.1: a BOUND session's injected prefix restates neither the dispatcher
    preflight (a restatement of ``DADAIA.md`` §1/§2) nor the ALIVE-context list —
    only the context header and the lean memory prefix (A30.3, untouched) survive."""
    _ws(tmp_path)
    sid = "fr30-bound"
    _bind_session(tmp_path, sid, "ctx")
    out = _run(tmp_path, sid)
    assert "[ctx]" in out
    assert "end memory bootstrap" in out
    assert "Python 3.12" in out
    assert "dispatcher preflight" not in out
    assert "ALIVE contexts" not in out


def test_unbound_session_still_lists_alive_contexts_no_dispatcher_preflight(
    tmp_path: Path,
) -> None:
    """A30.1: an UNBOUND session still names the ALIVE contexts (unchanged — the
    ALIVE list is useful only when unbound), even though the dispatcher preflight
    text is gone from every emission path, bound or not."""
    _ws(tmp_path, slug="alpha")
    _add_context(tmp_path, "beta")
    out = _run(tmp_path, "fr30-unbound")
    assert "[no bound context]" in out
    assert "ALIVE contexts" in out
    assert "- alpha" in out
    assert "- beta" in out
    assert "dispatcher preflight" not in out


def test_env_context_beats_own_session_record(tmp_path: Path) -> None:
    """F-03 (v0.5.0 six-axis review): rung 1 ``DADAIA_CONTEXT`` beats rung 2 (the
    session binding) in EVERY consumer — the gate already resolves env-first, so an
    inject that preferred its own record would attribute one context and inject
    another on the same prompt."""
    _ws(tmp_path)
    # Register a second ALIVE context so the record's binding survives the
    # deleted-context guard and the env override is proven against a LIVE alternative.
    states = tmp_path / ".dadaia" / "states" / "spec_contexts.json"
    states.write_text(
        json.dumps(
            {
                "contexts": [
                    {"repo_slug": "ctx", "state": "alive"},
                    {"repo_slug": "other", "state": "alive"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "repos" / "other" / "specs").mkdir(parents=True)
    _bind_session(tmp_path, "ordersid", "other")
    env = claude_hook_env(tmp_path, extra={"DADAIA_CONTEXT": "ctx"})
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    result = run_hook_subprocess("ctx_inject", {"session_id": "ordersid"}, env)
    assert result.returncode == 0, result.stderr
    assert "[ctx]" in result.stdout, "rung 1 env must win over the bound record"
