"""Intent: CONTRACT — 0.4.6 AC5 (FR4/D13: the SessionStart lane is the one reaper); size: SMALL.

Every harness runtime config carries exactly one SessionStart command that deletes —
``dadaia doctor --fix --expired-only --quiet`` — as a CLI process (P-12: never a
``dadaia_workspace.hooks.*`` module). The entry is dadaia-owned by the same marker the
settings merge and the doctor use, so a re-install replaces it instead of stacking a second
reaper beside it (the shape that made ``tmp gc`` at SessionStart a rumour and never a fact).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.runtime_config import (
    claude_settings,
    codex_hook_wrapper_contents,
    codex_hooks,
    dadaia_owned_claude_settings,
    kimi_hook_shims,
    kimi_hooks_block,
    merge_claude_settings,
)

pytestmark = pytest.mark.unit

_REAPER_TAIL = "doctor --fix --expired-only --quiet"


def _commands(entries: object) -> list[tuple[str, str]]:
    """``(matcher, command)`` per hook across one event's entry list."""
    assert isinstance(entries, list)
    found: list[tuple[str, str]] = []
    for entry in entries:
        assert isinstance(entry, dict)
        for hook in entry["hooks"]:
            found.append((str(entry.get("matcher", "")), str(hook["command"])))
    return found


def test_claude_session_start_runs_the_reaper_once(tmp_path: Path) -> None:
    hooks = claude_settings(tmp_path)["hooks"]
    assert isinstance(hooks, dict)
    session_start = _commands(hooks["SessionStart"])
    reapers = [(m, c) for m, c in session_start if c.endswith(_REAPER_TAIL)]
    assert len(reapers) == 1, session_start
    matcher, command = reapers[0]
    assert matcher == "startup|resume"
    assert " -m dadaia_workspace " in command, "the reaper is the CLI, not a hook module"
    others = [c for _, c in session_start if not c.endswith(_REAPER_TAIL)]
    assert others and all("dadaia_workspace.hooks.ctx_inject" in c for c in others)
    for event, entries in hooks.items():
        for _, command in _commands(entries):
            assert "--fix" not in command or command.endswith(_REAPER_TAIL), (event, command)


def test_codex_session_start_runs_the_reaper_once(tmp_path: Path) -> None:
    hooks = codex_hooks(tmp_path)["hooks"]
    assert isinstance(hooks, dict)
    session_start = _commands(hooks["SessionStart"])
    assert {m for m, _ in session_start} == {"startup|resume"}
    wrappers = codex_hook_wrapper_contents()
    bodies = {command: wrappers[Path(command).name] for _, command in session_start}
    reapers = [c for c, body in bodies.items() if body.rstrip().endswith(_REAPER_TAIL)]
    assert len(reapers) == 1, bodies
    reaper_body = bodies[reapers[0]]
    assert " -m dadaia_workspace doctor " in reaper_body
    assert "dadaia_workspace.hooks." not in reaper_body
    for command, body in bodies.items():
        if command != reapers[0]:
            assert "dadaia_workspace.hooks.ctx_inject" in body


def test_kimi_session_start_runs_the_reaper_once(tmp_path: Path) -> None:
    """Kimi Code exposes ``SessionStart`` in the same hook-event enum as the ``PostCompact``
    the compact shim already consumes; its rule runs the reaper shim and nothing else."""
    rules = tomllib.loads(kimi_hooks_block(tmp_path))["hooks"]
    session_start = [r for r in rules if r["event"] == "SessionStart"]
    assert len(session_start) == 1, rules
    shims = kimi_hook_shims()
    reaper_body = shims[Path(session_start[0]["command"]).name]
    assert f" -m dadaia_workspace {_REAPER_TAIL}" in reaper_body
    assert "dadaia_workspace.hooks." not in reaper_body
    assert reaper_body.rstrip().endswith("exit 0")
    others = [
        body for name, body in shims.items() if name != Path(session_start[0]["command"]).name
    ]
    assert others and all("--fix" not in body for body in others)


def test_reaper_entry_is_dadaia_owned_so_merge_is_idempotent(tmp_path: Path) -> None:
    canonical = claude_settings(tmp_path)
    assert dadaia_owned_claude_settings(canonical) == {"hooks": canonical["hooks"]}
    assert merge_claude_settings(canonical, tmp_path) == canonical
