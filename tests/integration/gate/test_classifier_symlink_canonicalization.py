"""Intent: CONTRACT — bug ``gate-fpath-not-canonicalized-before-classifier``; size: MEDIUM.

The gate calls ``fpath.resolve()`` BEFORE relativizing and classifying, so a write whose
target path is an innocuous-looking symlink that actually points at a PROTECTED path must
classify PROTECTED, not slip through on the symlink's own name.

Retargeted at 0.4.7 FR1: the MEMORY class and its phase rule are deleted, so the
canonicalization regression is now proven against the class that survives and still
fail-CLOSES — ``.dadaia/sessions/``.

These tests invoke the real ``sdd_gate`` hook as a subprocess via the sanctioned
``run_hook_subprocess`` harness helper — the only channel that exercises the
resolve→classify path the way a runtime actually spawns the hook. (POSIX symlinks;
skipped where unavailable.)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = pytest.mark.integration


def _make_workspace(tmp_path: Path, slug: str = "dadaia-workspace") -> Path:
    (tmp_path / "repos" / slug / "specs").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    return tmp_path


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:  # pragma: no cover - platform guard
        pytest.skip(f"symlinks unsupported on this platform: {exc}")


def test_symlink_into_protected_sessions_classifies_protected(tmp_path: Path) -> None:
    """A MUTATING-looking symlink resolving into ``.dadaia/sessions/`` must BLOCK.

    Skipping canonicalization would classify the link's own name (``notes.md`` at a repo
    root) MUTATING and silently ALLOW — the exact bug.
    """
    slug = "dadaia-workspace"
    ws = _make_workspace(tmp_path, slug=slug)
    record = ws / ".dadaia" / "sessions" / "claude-sess.json"
    record.write_text("{}\n", encoding="utf-8")

    link = ws / "repos" / slug / "notes.md"
    _symlink_or_skip(link, record)

    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(link)},
        "session_id": "claude-sess-symlink",
    }
    result = run_hook_subprocess("sdd_gate", payload, claude_hook_env(ws))

    assert result.returncode == 0
    envelope = result.block_envelope()
    assert envelope is not None, (
        "a symlink into .dadaia/sessions/ must resolve-then-classify PROTECTED — an ALLOW "
        "means canonicalization was skipped (gate-fpath-not-canonicalized-before-classifier)"
    )
    assert "SEC-01" in envelope["reason"]


@pytest.mark.skipif(os.name == "nt", reason="dir symlink perms differ on Windows CI; covered above")
def test_symlink_directory_into_protected_sessions_classifies_protected(tmp_path: Path) -> None:
    """A symlinked *directory* into ``.dadaia/sessions/`` also resolves before classification."""
    slug = "sample-engine"
    ws = _make_workspace(tmp_path, slug=slug)
    sessions = ws / ".dadaia" / "sessions"

    link_dir = ws / "repos" / slug / "shortcut"
    _symlink_or_skip(link_dir, sessions)

    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(link_dir / "other.json")},
        "session_id": "claude-sess-dirlink",
    }
    result = run_hook_subprocess("sdd_gate", payload, claude_hook_env(ws))
    assert result.returncode == 0
    envelope = result.block_envelope()
    assert envelope is not None and "SEC-01" in envelope["reason"]
