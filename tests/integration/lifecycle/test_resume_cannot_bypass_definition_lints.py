"""Resuming past the draft step must not skip the artifact lints.

Bugs ``r13-release-plan-validation-bypassed-on-resume`` and
``r13-release-pytest-hygiene-bypassed-on-resume`` (consumer-side validator, R13/R-20):
``--resume-from definition_review`` accepted a PLAN with no Validation section and a
TASKS.md whose pytest command omits ``-p no:cacheprovider``.

The cause is where the gates were attached: to ``definition_draft``, the step that
PRODUCES the artifacts. Resuming skips production but still performs APPROVAL — so the
content became binding without ever being checked. A gate a resume can step over is not a
gate; approval is the moment the content starts to matter, so that is where it has to hold.

Driven through the real CLI rather than a stubbed workflow. The first attempt at this test
stubbed ``_on_step_accepted``'s collaborators and kept needing more private attributes —
the signal that it was testing the wrong level. The hole exists on the command line, so it
is proven on the command line.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.integration

_runner = CliRunner()
_CTX = "lintctx"
_REPO = "lintrepo"
_RELEASE = "v0.1.0"


@pytest.fixture
def released(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A workspace carrying an approved release, ready to be resumed."""
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    repo = tmp_path / "repos" / _REPO
    repo.mkdir(parents=True)
    for args in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["commit", "-q", "--allow-empty", "-m", "init"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DADAIA_SESSION_ID", "lint-session")

    created = _runner.invoke(app, ["context", "create", _CTX, "--repo", _REPO, "--url", str(repo)])
    assert created.exit_code == 0, created.output
    assert _runner.invoke(app, ["context", "alive", _CTX]).exit_code == 0
    backlog = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog-definition",
            "--context",
            _CTX,
            "--release-id",
            _RELEASE,
            "--run-id",
            "bd",
            "--harness",
            "fake",
            "--demand",
            "x",
        ],  # fmt: skip
    )
    assert backlog.exit_code == 0, backlog.output
    release = _runner.invoke(
        app,
        [
            "lifecycle",
            "release-definition",
            "--context",
            _CTX,
            "--release-id",
            _RELEASE,
            "--run-id",
            "rd",
            "--harness",
            "fake",
            "--backlog-run-id",
            "bd",
        ],  # fmt: skip
    )
    assert release.exit_code == 0, release.output
    return tmp_path


def _resume(run_id: str = "rd"):
    return _runner.invoke(
        app,
        [
            "lifecycle",
            "release-definition",
            "--context",
            _CTX,
            "--release-id",
            _RELEASE,
            "--run-id",
            run_id,
            "--harness",
            "fake",
            "--backlog-run-id",
            "bd",
            "--resume-from",
            "definition_review",
        ],  # fmt: skip
    )


def _artifact(workspace: Path, name: str) -> Path:
    return workspace / "repos" / _REPO / "specs" / "releases" / _RELEASE / name


def test_resume_refuses_a_tasks_file_with_an_unhygienic_pytest_command(released: Path) -> None:
    _artifact(released, "TASKS.md").write_text(
        "# TASKS\n\n- [ ] T-1 - run `pytest tests/x.py`\n", encoding="utf-8"
    )

    result = _resume()

    assert result.exit_code != 0, (
        "resuming from definition_review approved a TASKS.md the draft-step lint rejects — "
        f"the gate was skippable. Output:\n{result.output}"
    )
    assert "cacheprovider" in result.output, result.output


def test_a_clean_resume_still_succeeds(released: Path) -> None:
    """Guard: closing the hole must not make every resume fail."""
    result = _resume()
    assert result.exit_code == 0, result.output
