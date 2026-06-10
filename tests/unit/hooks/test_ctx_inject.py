"""Harness-real behavior tests for dadaia_workspace.hooks.ctx_inject.

These drive ``ctx_inject`` exactly as a real harness does: a subprocess spawned with
:func:`claude_hook_env` / :func:`codex_hook_env` (pinned-minimal env, no hand-planted
``DADAIA_*`` session/persona/mode vars) and the prompt payload piped to stdin. The session
id flows through the stdin ``session_id`` field, the only channel a real harness provides;
the output contract (``DADAIA_HOOK_OUTPUT`` / ``DADAIA_HOOK_EVENT``) is passed through the
*subprocess* env via the fixture's ``extra`` — the harness-wiring channel — never an
in-process ``setenv``.

Rewritten from the old in-process ``ctx_inject.main()`` + ``sys.stdin`` simulation (the
pattern the harness-env contract bans): driving the hook through ``run_hook_subprocess``
proves the once-per-session sentinel, the auto-context resolution, and the codex/json
output envelopes fire under real spawn conditions, not a simulated environment.

Mandatory parity: a second invocation in the same session emits nothing (the once-per-
session sentinel guards the ENTIRE payload; sentinel path byte-identical to the shell one).
"""

from __future__ import annotations

import json
from pathlib import Path

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
    ``DADAIA_CONTEXT`` is popped so context resolution comes only from the seeded registry
    (a developer shell exporting it must not leak into these tmp-workspace runs).
    """
    env = claude_hook_env(tmp_path, extra=extra)
    env.pop("CLAUDE_CODE_SESSION_ID", None)  # force resolution from the stdin field
    env.pop("DADAIA_CONTEXT", None)  # context comes only from the seeded registry
    result = run_hook_subprocess("ctx_inject", {"session_id": session_id}, env)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_first_injection_emits_context_and_memory(tmp_path: Path) -> None:
    _ws(tmp_path)
    out = _run(tmp_path, "s1")
    assert "[ctx]" in out
    assert "dispatcher preflight" in out
    assert "tech-stack" in out or "Python 3.12" in out
    assert "end memory bootstrap" in out


def test_second_invocation_emits_nothing(tmp_path: Path) -> None:
    # PARITY: the once-per-session sentinel suppresses the ENTIRE payload on re-invocation.
    _ws(tmp_path)
    first = _run(tmp_path, "same")
    assert first.strip()  # non-empty
    second = _run(tmp_path, "same")
    assert second == ""  # nothing on the second call


def test_sentinel_path_byte_identical_to_shell(tmp_path: Path) -> None:
    _ws(tmp_path)
    _run(tmp_path, "abc123")
    expected = tmp_path / ".dadaia" / "tmp" / "ctx-inject-fired-abc123"
    assert expected.exists()


def test_codex_json_envelope(tmp_path: Path) -> None:
    _ws(tmp_path)
    out = _run(
        tmp_path,
        "s2",
        extra={"DADAIA_HOOK_OUTPUT": "codex-json", "DADAIA_HOOK_EVENT": "SessionStart"},
    )
    env = json.loads(out)
    assert env["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "[ctx]" in env["hookSpecificOutput"]["additionalContext"]


def test_json_output_default_event(tmp_path: Path) -> None:
    _ws(tmp_path)
    out = _run(tmp_path, "s3", extra={"DADAIA_HOOK_OUTPUT": "json"})
    env = json.loads(out)
    assert env["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


def test_no_alive_context_emits_empty(tmp_path: Path) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": "x", "state": "dead"}]}), encoding="utf-8"
    )
    out = _run(tmp_path, "s")
    assert out == ""


def test_runtime_ptr_written(tmp_path: Path) -> None:
    _ws(tmp_path)
    _run(tmp_path, "ptrsess")
    ptr = tmp_path / ".dadaia" / "sessions" / "runtime" / "ptrsess.ptr"
    assert ptr.exists()
    assert ptr.read_text(encoding="utf-8") == "ptrsess"
