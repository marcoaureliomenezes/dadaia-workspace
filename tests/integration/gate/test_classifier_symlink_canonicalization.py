"""T-010-03 / WS-R1 (AC-R1-03 / FR-R1-07): symlink→MEMORY canonicalization regression.

Named for bug ``gate-fpath-not-canonicalized-before-classifier`` (Python surface; the bash
surface is retired in T-010-13). The Python gate (`hooks/sdd_gate.py:101`) calls
``fpath.resolve()`` BEFORE relativizing and classifying, so a write whose *target path* is
an UNGATED-looking symlink that actually points into ``specs/memory/`` must classify MEMORY
(and therefore obey the PE phase lock), not slip through as UNGATED/ALLOW.

These tests invoke the real ``sdd_gate`` hook as a subprocess via the sanctioned
``run_hook_subprocess`` harness helper — the only channel that exercises the resolve→classify
path the way a runtime actually spawns the hook. (POSIX symlinks; skipped where unavailable.)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = pytest.mark.integration


def _make_workspace(tmp_path: Path, slug: str = "dadaia-workspace", phase: str = "SPEC") -> Path:
    rel = tmp_path / "repos" / slug / "specs" / "releases"
    rel.mkdir(parents=True)
    (rel / "ACTIVE.md").write_text(f"release: v0.1.10\nphase: {phase}\n", encoding="utf-8")
    (tmp_path / "repos" / slug / "specs" / "memory").mkdir(parents=True)
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    return tmp_path


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:  # pragma: no cover - platform guard
        pytest.skip(f"symlinks unsupported on this platform: {exc}")


def test_symlink_into_in_repo_memory_classifies_memory_block_and_definition_allows(
    tmp_path: Path,
) -> None:
    """An UNGATED-named symlink pointing into ``repos/<slug>/specs/memory/`` ⇒ MEMORY block.

    Outside DEFINITION/CLOSURE the MEMORY class blocks the write. If canonicalization were
    skipped the symlink's own name (``notes.md`` at repo root) would classify UNGATED ⇒
    silent ALLOW — the exact bug. We assert the BLOCK envelope to prove resolve-before-
    classify.

    Control (second half, DEFINITION phase): the same symlink is still MEMORY-classified
    but ALLOWed — proving the BLOCK above is the MEMORY phase rule firing on the
    *resolved* path, not an accidental block of the symlink itself.
    """
    slug = "dadaia-workspace"
    ws = _make_workspace(tmp_path, slug=slug, phase="SPEC")

    real_memory = ws / "repos" / slug / "specs" / "memory" / "architecture.md"
    real_memory.write_text("# memory atom\n", encoding="utf-8")

    # The write TARGET is an ungated-looking symlink at the repo root that resolves into memory.
    link = ws / "repos" / slug / "notes.md"
    _symlink_or_skip(link, real_memory)

    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(link)},
        "session_id": "claude-sess-symlink",
    }
    result = run_hook_subprocess("sdd_gate", payload, claude_hook_env(ws))

    assert result.returncode == 0
    envelope = result.block_envelope()
    assert envelope is not None, (
        "symlink into specs/memory/ must resolve-then-classify MEMORY and BLOCK outside "
        "DEFINITION/CLOSURE — an ALLOW (empty stdout) means canonicalization was skipped "
        "(gate-fpath-not-canonicalized-before-classifier)"
    )
    assert "RULE A" in envelope["reason"]

    # Control: DEFINITION phase, same symlink shape, different workspace.
    ws_def = _make_workspace(tmp_path / "definition-control", slug=slug, phase="DEFINITION")
    real_memory_def = ws_def / "repos" / slug / "specs" / "memory" / "architecture.md"
    real_memory_def.write_text("# memory atom\n", encoding="utf-8")
    link_def = ws_def / "repos" / slug / "notes.md"
    _symlink_or_skip(link_def, real_memory_def)

    payload_def = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(link_def)},
        "session_id": "claude-sess-symlink-def",
    }
    result_def = run_hook_subprocess("sdd_gate", payload_def, claude_hook_env(ws_def))

    assert result_def.returncode == 0
    assert result_def.block_envelope() is None, "MEMORY write in DEFINITION phase must ALLOW"


@pytest.mark.skipif(os.name == "nt", reason="dir symlink perms differ on Windows CI; covered above")
def test_symlink_directory_into_memory_classifies_memory(tmp_path: Path) -> None:
    """A symlinked *directory* into specs/memory also resolves before classification."""
    slug = "sample-engine"
    ws = _make_workspace(tmp_path, slug=slug, phase="SPEC")
    mem_dir = ws / "repos" / slug / "specs" / "memory"

    link_dir = ws / "repos" / slug / "shortcut"
    _symlink_or_skip(link_dir, mem_dir)
    (mem_dir / "TECHSTACK.md").write_text("x\n", encoding="utf-8")

    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(link_dir / "TECHSTACK.md")},
        "session_id": "claude-sess-dirlink",
    }
    result = run_hook_subprocess("sdd_gate", payload, claude_hook_env(ws))
    assert result.returncode == 0
    envelope = result.block_envelope()
    assert envelope is not None and "RULE A" in envelope["reason"]
