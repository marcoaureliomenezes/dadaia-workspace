"""The gate resolves the target BEFORE classifying: a write through an innocuous-looking
symlink (a file or a directory) into `.dadaia/sessions/` classifies PROTECTED and blocks —
classifying the link's own name would ALLOW. Real `sdd_gate` subprocess; POSIX symlinks.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.name == "nt", reason="POSIX symlinks"),
]


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_a_symlink_into_protected_sessions_classifies_protected(tmp_path: Path, kind: str) -> None:
    (tmp_path / "repos" / "app" / "specs").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir()
    (sessions / "claude-sess.json").write_text("{}\n", encoding="utf-8")
    link = tmp_path / "repos" / "app" / ("notes.md" if kind == "file" else "shortcut")
    link.symlink_to(sessions / "claude-sess.json" if kind == "file" else sessions)
    target = link if kind == "file" else link / "other.json"
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "s"}

    result = run_hook_subprocess("sdd_gate", payload, claude_hook_env(tmp_path))

    envelope = result.block_envelope()
    assert result.returncode == 0 and envelope is not None and "SEC-01" in envelope["reason"]
