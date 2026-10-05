"""0.4.6 AC8 (FR7, bug doctor-root1-flags-env-that-dadaia-md-9-declares-canonical)
and AC7 (FR6, the ``.dadaiaignore`` reader); size: SMALL.

Harness-real behavior tests for dadaia_workspace.hooks.root_whitelist.

These drive ``root_whitelist`` as a real Claude Code harness does: a subprocess spawned with
:func:`claude_hook_env` and a ``PreToolUse`` payload piped to stdin. The gate signals ALLOW
with empty stdout and BLOCK with a ``{"decision":"block",...}`` envelope; both are asserted
on the subprocess result, never by importing ``main()`` in-process.

Rewritten from the old in-process ``root_whitelist.main()`` + ``sys.stdin`` simulation (the
pattern the harness-env contract bans). The gate resolves the workspace root from the
write target and the session cwd, as in production (sa-seven-workspace-root-rules#S3).

CRIT: root-whitelist is a deterministic enforcement policy — every current input survives
below as a named parametrized row, including the W1-6 first-path-component block.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.workspace_layout import DADAIAIGNORE
from dadaia_workspace.core.workspace_resolver import FENCE_ENV
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess
from tests.fixtures.stores import context_store

#: Context names differ from their repo slugs: ``repos/`` and ``worktrees/`` admit slugs only.
REGISTRY = json.dumps({"contexts": [
    {"name": "alpha", "state": "ALIVE", "repo_slug": "main-r", "associated_repos": [{"slug": "assoc-r"}]},
    {"name": "gone", "state": "DEAD", "repo_slug": "dead-r"},
]})  # fmt: skip


def _ws(tmp_path: Path, registry: str = REGISTRY) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(registry, encoding="utf-8")
    return tmp_path


def _run(tmp_path: Path, payload: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    """Invoke root_whitelist as a subprocess; return (stdout, parsed block envelope)."""
    env = claude_hook_env(tmp_path)
    result = run_hook_subprocess("root_whitelist", payload, env)
    assert result.returncode == 0, result.stderr
    return result.stdout, result.block_envelope()


def test_block_message_lists_every_whitelisted_entry(tmp_path: Path) -> None:
    """sa-gate-allows-root-entries-the-reaper-moves#E1, #E7: the block names every root
    entry the law admits, and neither its text nor its fix points the agent at the
    operator's exceptions file (DEC-1 (a))."""
    _out, block = _run(
        _ws(tmp_path),
        {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "junk.txt")}},
    )
    assert block is not None
    reason = block["reason"]
    assert (
        ".agents/ .claude/ .codex/ .cursor/ .dadaia/ .devin/ .git/ .github/ repos/ worktrees/ "
        ".dadaiaignore .gitignore AGENTS.md prompt.md"
    ) in reason
    assert "instance_exceptions" not in reason


@pytest.mark.parametrize("name", [".gitignore", "AGENTS.md", "prompt.md"])
def test_law_declared_root_files_are_canon_for_the_hook_and_the_doctor(
    tmp_path: Path, name: str
) -> None:
    """sa-gate-allows-root-entries-the-reaper-moves#E8, #E6: the hook and the doctor derive
    from ``ROOT_ALLOWED_FILES``, so one row admits a file to both. ``.env`` left it (ADR 0146
    (1): credentials live outside the workspace); the block message above no longer names it."""
    from dadaia_workspace.features.spec_context.doctor import DoctorService, FindingVerdict

    ws = _ws(tmp_path)
    out, block = _run(tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(ws / name)}})
    assert (out, block) == ("", None)

    (ws / name).write_text("", encoding="utf-8")
    findings = DoctorService(
        context_store(ws / ".dadaia" / "states"), GitSubprocessClient(), ws
    ).scan()
    assert {f.path: f.verdict for f in findings if f.code.startswith("WS-root-")}[name] is (
        FindingVerdict.CANON
    )


@pytest.mark.parametrize(
    ("target", "ignore", "registry", "allowed"),
    [
        pytest.param("junk.txt", "", REGISTRY, False, id="root-stray"),
        pytest.param("shot.png", "*.png\n", REGISTRY, True, id="root-globbed"),
        pytest.param(".opencode/agents/foo.md", "", REGISTRY, False, id="root-stray-nested"),
        pytest.param(".playwright-mcp/x.log", ".playwright-mcp/\n", REGISTRY, True, id="root-globbed-dir"),
        pytest.param(".dadaia/junk.txt", "*.txt\n", REGISTRY, False, id="dadaia-stray"),
        pytest.param(".dadaia/junk.txt", ".dadaia/*.txt\n", REGISTRY, True, id="dadaia-globbed"),
        pytest.param(".dadaia/tmp/agent/20260701/s.json", "", REGISTRY, True, id="dadaia-zone"),
        pytest.param("repos/alpha/f.py", "", REGISTRY, False, id="repos-stray-context-name"),
        pytest.param("repos/alpha/f.py", "repos/alpha\n", REGISTRY, True, id="repos-globbed"),
        pytest.param("repos/assoc-r/f.py", "", REGISTRY, True, id="repos-associated"),
        pytest.param("repos/dead-r/f.py", "", REGISTRY, True, id="repos-dead-context"),
        pytest.param("repos/any/f.py", "", "{", True, id="repos-unreadable-registry"),
        pytest.param("worktrees/any/n/f.py", "", "[]", True, id="worktrees-wrong-shaped-registry"),
        pytest.param("worktrees/dead-r/x/f.py", "", REGISTRY, False, id="worktrees-stray-dead"),
        pytest.param("worktrees/dead-r/x/f.py", "worktrees/dead-r\n", REGISTRY, True, id="worktrees-globbed"),
        pytest.param("worktrees/assoc-r/0.5.0-rc1-j2/f.py", "", REGISTRY, True, id="worktrees-associated"),
        pytest.param("worktrees/AGENTS.md", "", REGISTRY, True, id="worktrees-law"),
        pytest.param(".claude/agents/unledgered.md", "", REGISTRY, True, id="harness-dir-unjudged"),
    ],
)  # fmt: skip
def test_four_places_table(
    tmp_path: Path, target: str, ignore: str, registry: str, allowed: bool
) -> None:
    """sa-gate-allows-root-entries-the-reaper-moves#E1 (stray blocked), #E2 (globbed allowed),
    #E8 (law-admitted entries allowed) and T-050-116 (ADR 0132), which narrows #E8: a write
    under an unregistered ``repos/<x>/`` — the retired ``subdir_write`` row — now blocks
    (``repos-stray-context-name``). The root, ``.dadaia/``, ``repos/`` and ``worktrees/`` each block
    a stray entry and admit a globbed one; ``repos/`` admits every repo slug of every context
    (DEAD included), ``worktrees/`` those of ALIVE ones, and an unreadable registry admits all."""
    ws = _ws(tmp_path, registry)
    (ws / DADAIAIGNORE).write_text(ignore, encoding="utf-8")
    out, block = _run(
        tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(ws / target)}}
    )
    assert (block is None) is allowed
    if block is not None:
        assert "ROOT WHITELIST GATE" in block["reason"]
        assert target in block["reason"]


def test_a_fenced_root_stays_protected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC1.3 (fenced-roots-env-disables-the-gate): the fence says "never act on", never
    "nothing protects"."""
    ws = _ws(tmp_path)
    monkeypatch.setenv(FENCE_ENV, os.pathsep.join((os.environ[FENCE_ENV], str(ws))))
    _out, block = _run(
        tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(ws / "junk.txt")}}
    )
    assert block is not None and "junk.txt" in block["reason"]


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        pytest.param("Read", {"path": "x"}, id="non_write_tool"),
        pytest.param("Write", {}, id="unparseable_path_fails_open"),
    ],
)
def test_fail_open_table(tmp_path: Path, tool_name: str, tool_input: dict[str, Any]) -> None:
    """Nothing to judge is an allow, never a block."""
    _ws(tmp_path)
    out, block = _run(tmp_path, {"tool_name": tool_name, "tool_input": tool_input})
    assert (out, block) == ("", None)


@pytest.mark.parametrize(
    ("extra", "segment"),
    [
        ({}, "main-thread"),
        ({"agent_id": "a1", "agent_type": "dd-software-engineer"}, "dd-software-engineer"),
        *(({"agent_type": bad}, "main-thread") for bad in ("../x", "a/b", "", "..", 3, None)),
    ],
)
def test_the_fix_creates_the_agents_own_temp_dir(
    tmp_path: Path, extra: dict[str, object], segment: str
) -> None:
    """AC4.4 (fix-lines-are-not-one-runnable-command): the fix makes the
    agent's own `.dadaia/tmp/<agent>/<YYYYMMDD>/`, never the existing `tmp/` (a no-op); a
    subagent payload's `agent_type` names it, only as a plain name (CWE-22)."""
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "junk.txt")}}
    days = [datetime.now(UTC).strftime("%Y%m%d")]  # the call may cross UTC midnight
    _out, block = _run(_ws(tmp_path), {**payload, **extra})
    days.append(datetime.now(UTC).strftime("%Y%m%d"))
    assert block is not None
    fix = block["reason"].rsplit("fix: ", 1)[1]
    tmp = tmp_path.resolve() / ".dadaia" / "tmp" / segment  # the hook prints it resolved, POSIX
    assert any((tmp / day).as_posix() in fix for day in days)
