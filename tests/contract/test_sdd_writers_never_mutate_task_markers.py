"""Intent: CONTRACT — bug sdd-artifact-linter-mutates-task-markers (T-044-03).

A "post-write linter" was reported (re-filed from a consumer repo's ledger) to mutate
``[ ]``/``[-]``/``[x]`` task markers, ``**Status:**`` tokens, and body content of
``specs/releases/**/*.md`` between an agent's ``Read`` and its next ``Edit``. The bug's
own ``expected`` clause: a linter on SDD markdown may normalize whitespace ONLY — it must
never mutate markers, Status tokens, or inject/duplicate body content.

T-044-03's honest reproduction attempt (real subprocess invocation of every wired hook
against a fixture ``TASKS.md``, plus direct calls to every explicit CLI-verb writer named
in the task) found NO code path in this package that reproduces the symptom — R-3: the
report was misfiled from a consumer repo whose ledger carried its own (since-removed or
never-shared) formatter. This test is the evidenced-negative's RED-capable pin: it runs
every product-owned SDD-markdown writer this package ships over one fixture and asserts
markers, Status tokens, and body-paragraph count survive byte-identical. A future writer
that starts touching ``specs/releases/**/*.md`` content automatically breaks this test on
its very first run.

Census (file:line, T-044-03):

1. The 3 hooks this package wires into every harness — the only code that runs
   automatically around a file-tool write (verified against the projected
   ``.claude/settings.json`` / ``.codex/hooks.json`` instance, both wrapping the same
   Python modules):
   - ``dadaia_workspace/hooks/pre_gate.py`` (PreToolUse) — emits an allow/block envelope
     only (``hooks/_common.py:176-208`` ``emit_allow``/``emit_block``); it never rewrites
     ``tool_input``, so it cannot touch the bytes a subsequent Edit/Write applies.
   - ``dadaia_workspace/hooks/sdd_post_gate.py`` (PostToolUse) — writes only to
     ``.dadaia/logs/``, ``.dadaia/states/``, and ``.dadaia/sessions/`` (presence renewal,
     reconciler flags, stale-record reap); it never opens a ``specs/releases/**`` path.
   - ``dadaia_workspace/hooks/ctx_inject.py`` (SessionStart/UserPromptSubmit) — writes
     only sentinel/compact markers under ``.dadaia/tmp/`` (``ctx_inject.py:378,435``); it
     reads memory atoms, never writes release artifacts.
2. ``dadaia_workspace/features/migrate/registry.py:44-73`` (``REGISTRY``) — every
   migration step is scoped to ``specs/foundation``/``specs/SPEC.md`` (``tree_v2.py``),
   ``specs/bugs/**`` (``bugs_jsonl.py``, ``bugs_single_file.py``), or
   ``specs/memory/**`` frontmatter, byte-preserving the rest (``agent_tier_frontmatter.py``,
   ``retired_frontmatter_keys.py``) — never ``specs/releases/**``.
3. ``dadaia_workspace/features/spec_artifacts/new_artifacts.py:111-148``
   (``release_new``) is a no-clobber scaffold: ``FileExistsError`` on an existing release
   dir, never a touch of its content.
4. ``dadaia_workspace/core/specs_repair.py:73-90`` (``remove_placeholder_atoms``) is
   scoped to ``specs_dir/memory/**`` only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dadaia_workspace.core import specs_repair
from dadaia_workspace.features.migrate import registry as migrate_registry
from dadaia_workspace.features.spec_artifacts import new_artifacts
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

_MARKER_RE = re.compile(r"^- \[([ xX-])\]", re.MULTILINE)
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+)$", re.MULTILINE)

_FIXTURE_TASKS_MD = """\
# TASKS — Release v1.0.0 — fixture

**Status:** Em revisão
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
    return [m.strip() for m in _STATUS_RE.findall(text)]


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
    release_dir = specs_dir / "releases" / release_id
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


def test_pre_gate_hook_never_mutates_tasks_md_between_read_and_edit(tmp_path: Path) -> None:
    ws = _mk_hook_workspace(tmp_path)
    specs_dir = ws / "repos" / "dummy-ctx" / "specs"
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
# 2. The migration-step registry — explicit `specs upgrade`-invoked writers, never
#    auto-fired, but a legitimate "product-owned SDD-markdown writer" per the task's
#    census scope.
# ---------------------------------------------------------------------------------------


def test_migration_registry_chain_never_touches_release_artifacts(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    target = _seed_release_tasks_md(specs_dir)
    before = target.read_text(encoding="utf-8")

    migrate_registry.run_chain(specs_dir, 0, migrate_registry.latest_version(), dry_run=False)

    after = target.read_text(encoding="utf-8")
    _assert_sdd_invariants_preserved(before, after)


# ---------------------------------------------------------------------------------------
# 3. CLI-verb scaffolders/repairers explicitly named in the task's census.
# ---------------------------------------------------------------------------------------


def test_release_new_refuses_to_clobber_an_existing_release_tasks_md(tmp_path: Path) -> None:
    # AS-13/T-050-06A: bare "1.0.0" is the current, mintable axis (a "v"-prefixed id
    # is refused at mint before this no-clobber check is ever reached).
    specs_dir = tmp_path / "specs"
    target = _seed_release_tasks_md(specs_dir, release_id="1.0.0")
    before = target.read_text(encoding="utf-8")

    with pytest.raises(FileExistsError):
        new_artifacts.release_new(specs_dir, "1.0.0")

    after = target.read_text(encoding="utf-8")
    _assert_sdd_invariants_preserved(before, after)


def test_specs_repair_placeholder_removal_never_touches_releases(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    target = _seed_release_tasks_md(specs_dir)
    before = target.read_text(encoding="utf-8")

    removed = specs_repair.remove_placeholder_atoms(specs_dir, dry_run=False)

    after = target.read_text(encoding="utf-8")
    _assert_sdd_invariants_preserved(before, after)
    assert target not in removed
