"""Characterization of context injection at its harness boundary."""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import PLATFORM
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess


@pytest.mark.medium
@pytest.mark.slow(reason="starts the real hook subprocess")
def test_unbound_session_emits_preflight_once_and_stamps_exact_sentinel(tmp_path: Path) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}), encoding="utf-8"
    )
    env = claude_hook_env(tmp_path, session_id="characterization-session")

    result = run_hook_subprocess("ctx_inject", {"session_id": "ignored-payload-id"}, env)

    cli = (
        tmp_path
        / ".dadaia"
        / ".venv"
        / PLATFORM.venv_scripts_dir
        / f"dadaia{PLATFORM.venv_exe_suffix}"
    )
    cli_word = str(cli).replace("\\", "/") if PLATFORM.windows else shlex.quote(str(cli))
    assert result.returncode == 0
    assert result.stdout == (
        "[no bound context]\n"
        "Next (command step context): no ALIVE Spec Context — create one\n"
        "fix: Operator action: run "
        f"{cli_word} context create with a context name and --main-repo set to the main repo's "
        "clone URL\n"
    )
    assert result.stderr == ""
    sentinel = tmp_path / ".dadaia" / "tmp" / "hooks" / "ctx-inject-fired-characterization-session"
    assert sentinel.read_bytes() == b""
