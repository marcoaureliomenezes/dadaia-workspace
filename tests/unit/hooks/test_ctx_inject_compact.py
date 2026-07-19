"""v0.2.8 T4 — ctx_inject compact-epoch: PostCompact marker + re-injection.

Drives ``ctx_inject`` as a real subprocess (the harness-real fixture) through the full
kimi-code compaction flow: ``UserPromptSubmit`` injections, the ``PostCompact`` event
(stamps ``ctx-compact-<sid>`` AND re-emits the bootstrap on stdout — the observable
contract; Kimi discards PostCompact stdout), and the next-prompt re-injection that
fires exactly once. Also covers the unbound-session variant (generic preflight).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def _stamp_bind_epoch(tmp_path: Path, slug: str, *, pid: int) -> Path:
    epoch_dir = tmp_path / ".dadaia" / "states" / "bind_epoch"
    epoch_dir.mkdir(parents=True, exist_ok=True)
    marker = epoch_dir / slug
    marker.write_text(f"{pid}\n", encoding="utf-8")
    return marker


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
    _stamp_bind_epoch(tmp_path, "ctx", pid=_PID_A)
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


def test_compact_marker_without_sentinel_does_not_bind(tmp_path: Path) -> None:
    """A compact marker on a fresh session (no sentinel) must not inject context memory."""
    _ws(tmp_path)
    sid = "sess-4"
    _stamp_bind_epoch(tmp_path, "ctx", pid=_PID_A)
    assert "[no bound context]" in _run(tmp_path, sid, event="PostCompact")
    # Fresh session: still only the generic preflight (bind-epoch never binds fresh sid).
    assert "[no bound context]" in _run(tmp_path, sid)
