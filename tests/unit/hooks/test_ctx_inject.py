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

CRIT: bind-driven injection + cross-session context-steal prevention (pid/ancestry
attribution). Injection-without-bind and steal-via-newer-foreign-marker negatives survive
verbatim below. The sentinel filename byte-parity test is DELETED — the digest-GC tests
(test_ctx_inject_digest.py) construct the same ``ctx-inject-fired-<sid>`` names and would
break on a rename, so the filename contract is already pinned implicitly.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.spec_context import session_identity
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

# Two distinct, clearly-synthetic harness pids used to drive W1-7 session attribution. A
# bind-epoch marker is honored only when its recorded pid matches the pid the hook resolves
# for THIS session; the hook resolves it from the stdin ``harness_pid`` payload field (the
# sanctioned test channel — see ``sdd_gate._resolve_holder_pid``), so passing a known pid
# and stamping the marker with the same/different value lets a single test process simulate
# two concurrent harness sessions with different pids. The values need only be positive and
# distinct — ctx_inject compares them for equality, it never probes them for liveness.
_PID_A = 990001
_PID_B = 990002


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


def _stamp_bind_epoch(
    tmp_path: Path,
    slug: str,
    *,
    mtime: float | None = None,
    pid: int | None = None,
    chain: list[int] | None = None,
) -> Path:
    """Write a bind-epoch marker for ``slug`` (optionally with an explicit mtime).

    W1-7/W1-8 session attribution: the marker CONTENT is the bind process's nearest-first
    ancestry pid chain, one decimal pid per line (the shape
    ``session_identity.write_bind_epoch`` produces). ``chain`` writes a multi-line ancestry
    chain [shell, harness, …]; ``pid`` writes a single-line (legacy) marker; ``pid=None``
    and ``chain=None`` write a legacy EMPTY marker — the pre-W1-7 shape, unattributable and
    never honored for injection. The hook honors a marker when this session's harness pid is
    a MEMBER of the recorded chain. An explicit ``mtime`` is applied after the content is
    written so the epoch ordering is deterministic.
    """
    epoch_dir = tmp_path / ".dadaia" / "states" / "bind_epoch"
    epoch_dir.mkdir(parents=True, exist_ok=True)
    marker = epoch_dir / slug
    if chain is not None:
        marker.write_text("".join(f"{p}\n" for p in chain), encoding="utf-8")
    elif pid is None:
        marker.touch()  # legacy EMPTY marker — no attribution
    else:
        marker.write_text(f"{pid}\n", encoding="utf-8")
    if mtime is not None:
        os.utime(marker, (mtime, mtime))
    return marker


def _run(
    tmp_path: Path,
    session_id: str,
    *,
    extra: dict[str, str] | None = None,
    harness_pid: int | None = None,
) -> str:
    """Invoke ctx_inject as a real subprocess; return its stdout.

    The session id is delivered the harness-real way: the stdin ``session_id`` field, with a
    clean env that carries no native session-id var (``claude_hook_env`` then pops it so the
    stdin field wins resolution). ``extra`` supplies harness-control output-contract vars.
    ``DADAIA_CONTEXT`` is popped so context resolution comes only from the bind-epoch /
    session chain (a developer shell exporting it must not leak into these tmp-workspace runs).

    ``harness_pid`` (W1-7) is threaded into the stdin payload as the ``harness_pid`` field —
    the sanctioned channel the hook resolves its owning harness pid from
    (``sdd_gate._resolve_holder_pid``). Supplying it lets a test pin the pid the hook uses to
    attribute bind-epoch markers, so one test process can simulate two concurrent sessions
    with distinct pids. Omitted ⇒ the payload carries no pid and the hook falls back to
    ``os.getppid()`` (the parent pytest process), the same-parent case the e2e exercises.
    """
    env = claude_hook_env(tmp_path, extra=extra)
    env.pop("CLAUDE_CODE_SESSION_ID", None)  # force resolution from the stdin field
    env.pop("DADAIA_CONTEXT", None)  # context comes only from the bind / marker chain
    payload: dict[str, object] = {"session_id": session_id}
    if harness_pid is not None:
        payload["harness_pid"] = harness_pid
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
        and "dispatcher preflight" in out
        and "end memory bootstrap" not in out
        and "Python 3.12" not in out
    )


def _assert_lists_alive_contexts(out: str) -> bool:
    return "ALIVE contexts" in out and "- alpha" in out and "- beta" in out


def _assert_no_alive_context_still_generic(out: str) -> bool:
    return "[no bound context]" in out and "end memory bootstrap" not in out


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
    ],
)
def test_no_bind_generic_preflight_table(
    tmp_path: Path, name: str, setup_fn: Any, session_id: str, assert_fn: Any
) -> None:
    setup_fn(tmp_path)
    out = _run(tmp_path, session_id)
    assert assert_fn(out)


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
    first = _run(tmp_path, "sess", harness_pid=_PID_A)
    assert "[no bound context]" in first
    # A bind stamps a marker NEWER than the sentinel AND attributed to this session's harness
    # pid ⇒ next prompt injects the context (W1-7).
    sentinel = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-sess"
    _stamp_bind_epoch(tmp_path, "ctx", mtime=sentinel.stat().st_mtime + 5, pid=_PID_A)
    second = _run(tmp_path, "sess", harness_pid=_PID_A)
    assert "[ctx]" in second
    assert "end memory bootstrap" in second
    assert "Python 3.12" in second


def test_rebind_and_repeat_prompt(tmp_path: Path) -> None:
    # W1-7 acceptance (c): a same-pid re-bind to ANOTHER context re-injects, and a repeat
    # prompt with no new marker stays silent.
    _ws(tmp_path, slug="alpha")
    _add_context(tmp_path, "beta")
    sentinel = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-rb"
    # First prompt establishes the sentinel (a marker qualifies only against an EXISTING one).
    _run(tmp_path, "rb", harness_pid=_PID_A)
    # Bind alpha newer than the sentinel, attributed to this session ⇒ inject alpha.
    _stamp_bind_epoch(tmp_path, "alpha", mtime=sentinel.stat().st_mtime + 5, pid=_PID_A)
    out_a = _run(tmp_path, "rb", harness_pid=_PID_A)
    assert "[alpha]" in out_a
    # Re-bind beta with a still-newer marker, same harness pid ⇒ re-inject beta.
    _stamp_bind_epoch(tmp_path, "beta", mtime=sentinel.stat().st_mtime + 5, pid=_PID_A)
    out_b = _run(tmp_path, "rb", harness_pid=_PID_A)
    assert "[beta]" in out_b
    assert "Node 20" in out_b
    # A repeat prompt with NO newer marker ⇒ silent.
    out_repeat = _run(tmp_path, "rb", harness_pid=_PID_A)
    assert out_repeat == ""


# --- W1-7 (T-47-16): bind-epoch session attribution ---------------------------


def test_legacy_empty_marker_never_injects_context(tmp_path: Path) -> None:
    """A legacy EMPTY (un-attributed) bind-epoch marker is never honored for injection.

    Pre-W1-7 markers carry no harness pid (empty file). Such a marker is unattributable, so
    the hook ignores it and stays on generic preflight — NEVER injecting a context. This
    keeps backward compatibility with old markers while closing the cross-session steal, and
    tolerates the empty content without crashing.
    """
    _ws(tmp_path)
    sentinel = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-legacy"
    # Establish the sentinel (generic preflight).
    first = _run(tmp_path, "legacy", harness_pid=_PID_A)
    assert "[no bound context]" in first
    # A legacy EMPTY marker newer than the sentinel is unattributable ⇒ ignored: no context.
    _stamp_bind_epoch(tmp_path, "ctx", mtime=sentinel.stat().st_mtime + 5)  # pid=None
    out = _run(tmp_path, "legacy", harness_pid=_PID_A)
    assert "[ctx]" not in out
    assert "end memory bootstrap" not in out


def test_marker_ancestry_chain_membership_injects(tmp_path: Path) -> None:
    """W1-8 (v0.1.47): the hook harness pid deep in a marker's ancestry chain still injects.

    The marker records the bind process's chain [ephemeral shell, harness, …]. The ephemeral
    bind shell (first entry) has since died, but this session's hook resolves the SAME
    long-lived harness pid — the SECOND entry — so membership matches and the context is
    injected. This is the exact ephemeral-shell case the single-pid-equality design missed.
    """
    _ws(tmp_path)
    sentinel = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-chain"
    _run(tmp_path, "chain", harness_pid=_PID_A)  # establish the sentinel (generic preflight)
    # Chain: [dead ephemeral shell, harness == _PID_A (2nd entry), grandparent]. The hook's
    # harness pid is NOT the first entry — it must still match via membership.
    _stamp_bind_epoch(
        tmp_path,
        "ctx",
        mtime=sentinel.stat().st_mtime + 5,
        chain=[555001, _PID_A, 700000],
    )
    out = _run(tmp_path, "chain", harness_pid=_PID_A)
    assert "[ctx]" in out
    assert "end memory bootstrap" in out
    assert "Python 3.12" in out


def test_marker_ancestry_chain_disjoint_pid_never_injects(tmp_path: Path) -> None:
    """A chain that does NOT contain this session's harness pid is never honored."""
    _ws(tmp_path)
    sentinel = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-dj"
    _run(tmp_path, "dj", harness_pid=_PID_A)
    # Chain belongs entirely to another session (no _PID_A anywhere) ⇒ ignored.
    _stamp_bind_epoch(
        tmp_path,
        "ctx",
        mtime=sentinel.stat().st_mtime + 5,
        chain=[555002, _PID_B, 700001],
    )
    out = _run(tmp_path, "dj", harness_pid=_PID_A)
    assert "[ctx]" not in out
    assert "end memory bootstrap" not in out


def test_two_session_marker_attribution_never_steals(tmp_path: Path) -> None:
    """W1-7 core: marker A (pid X) + a NEWER marker B (pid Y) never cross sessions.

    Regression for bug ``ctx-inject-newest-bind-epoch-steals-other-sessions-context``. A
    hook resolving pid X injects context A even though B's marker is strictly newer; a hook
    resolving pid Y injects context B. Neither session ever receives the other's context.
    """
    _ws(tmp_path, slug="alpha")  # context A
    _add_context(tmp_path, "beta")  # context B

    # Session X establishes its own sentinel, then A is attributed to X and a strictly-NEWER
    # B is attributed to Y.
    sx = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-sx"
    _run(tmp_path, "sx", harness_pid=_PID_A)
    base_x = sx.stat().st_mtime
    _stamp_bind_epoch(tmp_path, "alpha", mtime=base_x + 5, pid=_PID_A)
    _stamp_bind_epoch(tmp_path, "beta", mtime=base_x + 10, pid=_PID_B)  # newer, foreign pid
    out_x = _run(tmp_path, "sx", harness_pid=_PID_A)
    assert "[alpha]" in out_x
    assert "[beta]" not in out_x  # the newer, foreign-pid marker is never stolen

    # Symmetric: session Y (its own sentinel, pid Y) injects beta, never alpha. Re-stamp both
    # markers newer than Y's just-created sentinel, same attribution.
    sy = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-sy"
    _run(tmp_path, "sy", harness_pid=_PID_B)
    base_y = sy.stat().st_mtime
    _stamp_bind_epoch(tmp_path, "alpha", mtime=base_y + 5, pid=_PID_A)
    _stamp_bind_epoch(tmp_path, "beta", mtime=base_y + 10, pid=_PID_B)
    out_y = _run(tmp_path, "sy", harness_pid=_PID_B)
    assert "[beta]" in out_y
    assert "[alpha]" not in out_y


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
