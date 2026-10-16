"""The gate resolves the target BEFORE classifying: a write through an innocuous-looking
symlink (a file or a directory) into `.dadaia/sessions/` classifies PROTECTED and blocks —
classifying the link's own name would ALLOW. Real `sdd_gate` subprocess; POSIX symlinks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess
from tests.helpers.oslib import link as os_link
from tests.helpers.oslib import write_text


@pytest.mark.parametrize("kind", ["file", "directory"])
@pytest.mark.medium
def test_a_symlink_into_protected_sessions_classifies_protected(tmp_path: Path, kind: str) -> None:
    (tmp_path / "repos" / "app" / "specs").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    write_text(tmp_path / ".dadaia" / "states" / "spec_contexts.json", "{}")
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir()
    write_text(sessions / "claude-sess.json", "{}\n")
    link = tmp_path / "repos" / "app" / ("notes.md" if kind == "file" else "shortcut")
    if not os_link(
        str(sessions / "claude-sess.json" if kind == "file" else sessions),
        link,
        is_dir=kind == "directory",
    ):
        pytest.skip("this host refuses symlinks")
    target = link if kind == "file" else link / "other.json"
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "s"}

    result = run_hook_subprocess("sdd_gate", payload, claude_hook_env(tmp_path))

    envelope = result.block_envelope()
    assert result.returncode == 0 and envelope is not None and "SEC-01" in envelope["reason"]
