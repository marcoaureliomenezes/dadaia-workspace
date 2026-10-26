"""`dadaia doctor` reports the derived onboarding step and refuses a ghost context.

Size: MEDIUM (integration: a real initialized workspace, a real git checkout as the level-2 repo).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core import clock, workspace_layout
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.session_store import (
    new_binding_record,
    session_record_path,
    write_session,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.helpers.oslib import make_executable, run, write_text

_runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES[:1])
    venv_bin = tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True, exist_ok=True)
    entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    write_text(entry, "#!/bin/sh\n")
    make_executable(entry)
    monkeypatch.chdir(tmp_path)
    for var in ("DADAIA_CONTEXT", "DADAIA_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _register_specless_context(root: Path, *names: str) -> None:
    contexts = []
    for name in names:
        repo = root / "repos" / name
        repo.mkdir(parents=True)
        run(["git", "init", "-q", str(repo)], check=True)
        for target, source in workspace_layout.INSTALLED_GIT_HOOKS:  # what `create` installs
            shipped = (workspace_layout.public_scripts_dir() / source).read_bytes()
            (repo / ".git" / "hooks" / target).write_bytes(shipped)
        contexts.append(
            {
                "name": name,
                "state": "alive",
                "repo_slug": name,
                "repo_url": f"file:///nowhere/{name}.git",
                "created_at": "2026-01-01T00:00:00Z",
                "alive_since": "2026-01-01T00:00:00Z",
                "dead_since": None,
                "current_branch": None,
            }
        )
    write_text(
        root / ".dadaia" / "states" / "spec_contexts.json",
        json.dumps({"schema_version": "2", "contexts": contexts}),
    )


@pytest.mark.slow(reason="git init subprocess")
@pytest.mark.parametrize(
    ("contexts", "argv", "text", "code"),
    [
        pytest.param((), ["doctor"], "ONBOARDING info Next (command step context):", None, id="R2-zero-contexts-is-not-silent"),
        pytest.param(("app",), ["doctor", "--context", "app"], "specs init --context app", 0, id="AC3.1-specless-context-is-level-two"),
        pytest.param(("a", "b"), ["doctor", "--context", "b"], "specs init --context b", None, id="G1-the-doctored-context-names-its-own-step"),
        pytest.param((), ["doctor", "--context", "ghost"], "Error: Context 'ghost' not found.", 1, id="AC6.3-ghost-context-exits-one"),
    ],
)  # fmt: skip
def test_doctor_names_the_onboarding_step_of_the_context_it_judges(
    workspace: Path, contexts: tuple[str, ...], argv: list[str], text: str, code: int | None
) -> None:
    """The next step is one finding whose fix names the workspace CLI; a
    ghost context never falls back to a specs tree."""
    if contexts:
        _register_specless_context(workspace, *contexts)
    result = _runner.invoke(app, argv)
    assert text in result.output, result.output
    assert code is None or result.exit_code == code, result.output
    assert "SPEC-DOC" not in result.output
    assert code != 1 or result.output.count("fix: ") == 1, result.output  # a refusal: one fix line
    assert f"{fix_line(workspace)} " in result.output


@pytest.mark.slow(reason="git init subprocess")
@pytest.mark.parametrize(
    ("live", "fix"),
    [
        pytest.param(False, "fix: Operator action: relaunch the session at the workspace root", id="ungoverned-names-the-relaunch"),
        pytest.param(True, "", id="governed-unbound-binds"),
        pytest.param(None, "doctor --fix", id="unreadable-record-names-doctors-fix"),
    ],
)  # fmt: skip
def test_doctor_names_the_bind_only_to_a_session_bind_accepts(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, live: bool | None, fix: str
) -> None:
    """A subagent-harness session with no live record cannot bind: the step's fix is the
    relaunch; with a live record, that session binds."""
    if live is None:
        fix = f"fix: {fix_line(workspace, 'doctor', '--fix')}"
    fix = fix or f"fix: {fix_line(workspace, 'context', 'bind', 'app')}"
    _register_specless_context(workspace, "app")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1")
    if live is None:
        write_text(session_record_path(workspace, "sess-1", create=True), "{not json")
    if live:
        write_session(
            workspace,
            "sess-1",
            new_binding_record(
                session_id="sess-1",
                context=None,
                runtime="claude",
                pid=os.getpid(),
                now=clock.now_iso(),
            ),
        )

    result = _runner.invoke(app, ["doctor", "--context", "app"])

    assert "step bind" in result.output, result.output
    assert fix in result.output, result.output
    assert ("context bind app" in result.output) == bool(live), result.output
    assert ("relaunch the session" in result.output) == (live is False), result.output
