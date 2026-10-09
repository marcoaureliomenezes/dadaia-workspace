"""Characterization of the root-whitelist hook at its harness boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess


@pytest.mark.medium
@pytest.mark.slow(reason="starts the real hook subprocess")
def test_existing_root_entry_is_allowed_without_mutating_it(tmp_path: Path) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}), encoding="utf-8"
    )
    target = tmp_path / "operator-note.txt"
    target.write_bytes(b"operator-owned\n")

    result = run_hook_subprocess(
        "root_whitelist",
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        claude_hook_env(tmp_path),
    )

    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    assert target.read_bytes() == b"operator-owned\n"
