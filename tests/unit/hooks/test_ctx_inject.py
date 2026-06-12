"""Harness-real behavior tests for dadaia_workspace.hooks.ctx_inject.

These drive ``ctx_inject`` exactly as a real harness does: a subprocess spawned with
:func:`claude_hook_env` / :func:`codex_hook_env` (pinned-minimal env, no hand-planted
``DADAIA_*`` session/persona/mode vars) and the prompt payload piped to stdin. The session
id flows through the stdin ``session_id`` field, the only channel a real harness provides;
the output contract (``DADAIA_HOOK_OUTPUT`` / ``DADAIA_HOOK_EVENT``) is passed through the
*subprocess* env via the fixture's ``extra`` — the harness-wiring channel — never an
in-process ``setenv``.

Bind-driven injection (FR-W2-01 / FR-W2-02, v0.1.14)
----------------------------------------------------
The first-ALIVE fallback is DELETED from injection. An UNBOUND session now yields generic
preflight (``[no bound context]`` + dispatcher preflight + ALIVE list) with NO context
memory. Context memory is injected only when a context is RESOLVED through the chain:
``DADAIA_CONTEXT`` env → self-keyed session record → newest bind-epoch marker newer than
the sentinel. A pre-existing marker never binds a fresh session.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

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
        (mem / "tech-stack.md").write_text("# tech\nPython 3.12\n", encoding="utf-8")
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
        (mem / "tech-stack.md").write_text(f"# tech {slug}\nNode 20\n", encoding="utf-8")
        (mem / "product").mkdir()
        (mem / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")


def _stamp_bind_epoch(tmp_path: Path, slug: str, *, mtime: float | None = None) -> Path:
    """Write a bind-epoch marker for ``slug`` (optionally with an explicit mtime)."""
    epoch_dir = tmp_path / ".dadaia" / "states" / "bind_epoch"
    epoch_dir.mkdir(parents=True, exist_ok=True)
    marker = epoch_dir / slug
    marker.touch()
    if mtime is not None:
        os.utime(marker, (mtime, mtime))
    return marker


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
    ``DADAIA_CONTEXT`` is popped so context resolution comes only from the bind-epoch /
    session chain (a developer shell exporting it must not leak into these tmp-workspace runs).
    """
    env = claude_hook_env(tmp_path, extra=extra)
    env.pop("CLAUDE_CODE_SESSION_ID", None)  # force resolution from the stdin field
    env.pop("DADAIA_CONTEXT", None)  # context comes only from the bind / marker chain
    result = run_hook_subprocess("ctx_inject", {"session_id": session_id}, env)
    assert result.returncode == 0, result.stderr
    return result.stdout


# --- FR-W2-01: unbound session ⇒ generic preflight, NO context memory ---------


def test_unbound_session_emits_generic_preflight_no_memory(tmp_path: Path) -> None:
    _ws(tmp_path)
    out = _run(tmp_path, "s1")
    assert "[no bound context]" in out
    assert "dispatcher preflight" in out
    # NO context memory whatsoever.
    assert "end memory bootstrap" not in out
    assert "Python 3.12" not in out


def test_unbound_session_lists_alive_contexts(tmp_path: Path) -> None:
    _ws(tmp_path, slug="alpha")
    _add_context(tmp_path, "beta")
    out = _run(tmp_path, "s-list")
    assert "ALIVE contexts" in out
    assert "- alpha" in out
    assert "- beta" in out


def test_preexisting_marker_does_not_bind_fresh_session(tmp_path: Path) -> None:
    # STALE-MARKER NEGATIVE (architect MEDIUM): a marker that predates the (absent) sentinel
    # must NOT inject memory into a fresh session — only generic preflight.
    _ws(tmp_path)
    _stamp_bind_epoch(tmp_path, "ctx", mtime=time.time() - 500)
    out = _run(tmp_path, "fresh")
    assert "[no bound context]" in out
    assert "end memory bootstrap" not in out


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


# --- FR-W2-02: bind-epoch marker drives re-injection -------------------------


def test_bind_marker_newer_than_sentinel_injects_memory(tmp_path: Path) -> None:
    _ws(tmp_path)
    # First prompt: unbound ⇒ generic, stamps the sentinel.
    first = _run(tmp_path, "sess")
    assert "[no bound context]" in first
    # A bind stamps a marker NEWER than the sentinel ⇒ next prompt injects the context.
    sentinel = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-sess"
    _stamp_bind_epoch(tmp_path, "ctx", mtime=sentinel.stat().st_mtime + 5)
    second = _run(tmp_path, "sess")
    assert "[ctx]" in second
    assert "end memory bootstrap" in second
    assert "Python 3.12" in second


def test_rebind_to_other_context_reinjects(tmp_path: Path) -> None:
    _ws(tmp_path, slug="alpha")
    _add_context(tmp_path, "beta")
    sentinel = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-rb"
    # First prompt establishes the sentinel (a marker qualifies only against an EXISTING one).
    _run(tmp_path, "rb")
    # Bind alpha newer than the sentinel ⇒ inject alpha.
    _stamp_bind_epoch(tmp_path, "alpha", mtime=sentinel.stat().st_mtime + 5)
    out_a = _run(tmp_path, "rb")
    assert "[alpha]" in out_a
    # Re-bind beta with a still-newer marker ⇒ re-inject beta.
    _stamp_bind_epoch(tmp_path, "beta", mtime=sentinel.stat().st_mtime + 5)
    out_b = _run(tmp_path, "rb")
    assert "[beta]" in out_b
    assert "Node 20" in out_b


def test_repeat_prompt_same_context_is_silent(tmp_path: Path) -> None:
    _ws(tmp_path)
    sentinel = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-quiet"
    # Establish the sentinel, then bind ctx newer than it.
    _run(tmp_path, "quiet")
    _stamp_bind_epoch(tmp_path, "ctx", mtime=sentinel.stat().st_mtime + 5)
    first = _run(tmp_path, "quiet")
    assert "[ctx]" in first
    # A repeat prompt with NO newer marker ⇒ silent.
    second = _run(tmp_path, "quiet")
    assert second == ""


def test_sentinel_path_byte_identical_to_shell(tmp_path: Path) -> None:
    _ws(tmp_path)
    _run(tmp_path, "abc123")
    expected = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-abc123"
    assert expected.exists()


# --- output-contract envelopes (unchanged contract, generic-preflight payload) ---


def test_codex_json_envelope(tmp_path: Path) -> None:
    _ws(tmp_path)
    out = _run(
        tmp_path,
        "s2",
        extra={"DADAIA_HOOK_OUTPUT": "codex-json", "DADAIA_HOOK_EVENT": "SessionStart"},
    )
    env = json.loads(out)
    assert env["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "[no bound context]" in env["hookSpecificOutput"]["additionalContext"]


def test_json_output_default_event(tmp_path: Path) -> None:
    _ws(tmp_path)
    out = _run(tmp_path, "s3", extra={"DADAIA_HOOK_OUTPUT": "json"})
    env = json.loads(out)
    assert env["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


def test_no_alive_context_emits_generic_preflight(tmp_path: Path) -> None:
    # No ALIVE context: still generic preflight (no memory, no ALIVE list), never crash.
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": "x", "state": "dead"}]}), encoding="utf-8"
    )
    out = _run(tmp_path, "s")
    assert "[no bound context]" in out
    assert "end memory bootstrap" not in out
