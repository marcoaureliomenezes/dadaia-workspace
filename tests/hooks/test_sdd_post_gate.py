"""A PostToolUse writer never rewrites SDD markdown: task markers, Status tokens and body content
stay byte-identical.

Drives every product-owned writer that runs around a file-tool write over one fixture of
``specs/releases/**/*.md``: the pre-gate, the post-gate and the ctx-inject hook. Each reads or
writes only its own state; none writes a release artifact.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dadaia_workspace.core.spec_status import STATUS_LINE
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

_MARKER_RE = re.compile(r"^- \[([ xX-])\]", re.MULTILINE)

_FIXTURE_TASKS_MD = """\
# TASKS — Release v1.0.0 — fixture

**Status:** In review
**Release ID:** v1.0.0
**Owner:** product-engineer

---

## Segment `S1`

- [ ] T-1 — first fixture task
- [ ] T-2 — second fixture task
- [ ] T-3 — third fixture task
"""


def _markers(text: str) -> list[str]:
    return _MARKER_RE.findall(text)


def _status_tokens(text: str) -> list[str]:
    return [m.strip() for m in STATUS_LINE.findall(text)]


def _paragraph_count(text: str) -> int:
    return len([p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()])


def _assert_sdd_invariants_preserved(before: str, after: str) -> None:
    """Pins the bug's own contract: markers, Status tokens, and body-paragraph count are
    semantic SDD state — a linter may normalize whitespace only. No writer census below
    performs even that today, so byte-identity is asserted as the current, stricter bar;
    the three named invariants are asserted separately so a future *legitimate*
    whitespace-only normalizer fails only the byte-identity line, never this test's
    semantic checks."""
    assert _markers(after) == _markers(before), (
        "task marker(s) mutated",
        _markers(before),
        _markers(after),
    )
    assert _status_tokens(after) == _status_tokens(before), (
        "Status token mutated",
        _status_tokens(before),
        _status_tokens(after),
    )
    assert _paragraph_count(after) == _paragraph_count(before), (
        "body paragraph count changed — content injected or duplicated",
        _paragraph_count(before),
        _paragraph_count(after),
    )
    assert after == before, "writer mutated file bytes"


def _seed_release_tasks_md(specs_dir: Path, release_id: str = "v1.0.0") -> Path:
    release_dir = specs_dir / "releases" / release_id / "rc-1"
    release_dir.mkdir(parents=True, exist_ok=True)
    path = release_dir / "TASKS.md"
    path.write_text(_FIXTURE_TASKS_MD, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------------------
# 1. The 3 wired hooks — the only code that runs automatically around a file-tool write.
# ---------------------------------------------------------------------------------------


def _mk_hook_workspace(tmp_path: Path, ctx: str = "dummy-ctx") -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": ctx, "state": "alive"}]}),
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.medium
def test_pre_gate_hook_never_mutates_tasks_md_between_read_and_edit(tmp_path: Path) -> None:
    ws = _mk_hook_workspace(tmp_path)
    specs_dir = ws / "worktrees" / "dummy-ctx" / "0.5.0-rc1/j1" / "specs"
    target = _seed_release_tasks_md(specs_dir)
    before = target.read_text(encoding="utf-8")

    env = claude_hook_env(ws, session_id="pre-gate-sess", extra={"DADAIA_CONTEXT": "dummy-ctx"})
    result = run_hook_subprocess(
        "pre_gate",
        {
            "session_id": "pre-gate-sess",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(target),
                "old_string": "first fixture task",
                "new_string": "first fixture task (edited)",
            },
        },
        env,
    )
    assert result.returncode == 0, result.stderr
    assert result.block_envelope() is None, "the gate must ALLOW a plain in-scope Edit"

    after = target.read_text(encoding="utf-8")
    _assert_sdd_invariants_preserved(before, after)


@pytest.mark.medium
def test_sdd_post_gate_hook_never_mutates_tasks_md_content(tmp_path: Path) -> None:
    ws = _mk_hook_workspace(tmp_path)
    specs_dir = ws / "repos" / "dummy-ctx" / "specs"
    target = _seed_release_tasks_md(specs_dir)
    before = target.read_text(encoding="utf-8")

    env = claude_hook_env(ws, session_id="post-gate-sess", extra={"DADAIA_CONTEXT": "dummy-ctx"})
    result = run_hook_subprocess(
        "sdd_post_gate",
        {
            "session_id": "post-gate-sess",
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target)},
        },
        env,
    )
    assert result.returncode == 0, result.stderr

    after = target.read_text(encoding="utf-8")
    _assert_sdd_invariants_preserved(before, after)


@pytest.mark.medium
def test_ctx_inject_hook_never_mutates_tasks_md_content(tmp_path: Path) -> None:
    ws = _mk_hook_workspace(tmp_path)
    specs_dir = ws / "repos" / "dummy-ctx" / "specs"
    target = _seed_release_tasks_md(specs_dir)
    mem = specs_dir / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "TECHSTACK.md").write_text("# tech\nPython 3.12\n", encoding="utf-8")
    (mem / "product").mkdir(exist_ok=True)
    (mem / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    before = target.read_text(encoding="utf-8")

    env = claude_hook_env(ws, extra={"DADAIA_CONTEXT": "dummy-ctx"})
    env.pop("CLAUDE_CODE_SESSION_ID", None)  # force resolution via the stdin field
    result = run_hook_subprocess("ctx_inject", {"session_id": "ctx-inject-sess"}, env)
    assert result.returncode == 0, result.stderr

    after = target.read_text(encoding="utf-8")
    _assert_sdd_invariants_preserved(before, after)


# ---------------------------------------------------------------------------------------
# 3. CLI-verb scaffolders/repairers explicitly named in the task's census.
# ---------------------------------------------------------------------------------------
