"""Intent: CONTRACT — bug ci-preflight-unusable-outside-the-source-repo: `ci preflight` is
bound to the source tree (it lints `dadaia_workspace/`, reads `setup.cfg`); a consumer repo
gets one refusal, never a fake lint failure, and the source repo is still recognized.
sa-doctor-job-not-a-required-check#B4: a tracked `.claude/settings.json` fails it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

pytestmark = pytest.mark.integration

_runner = CliRunner()


def _git_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=60)


def test_preflight_refuses_in_a_consumer_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repo that is not the source tree gets ONE clear refusal, not a fake lint failure."""
    consumer = tmp_path / "consumer"
    _git_repo(consumer)
    (consumer / "app.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.chdir(consumer)

    result = _runner.invoke(app, ["ci", "preflight"])

    assert result.exit_code != 0
    assert "ruff format --check" not in result.output + str(result.exception or "")


def test_preflight_still_runs_inside_the_source_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """The guard must not disable the gate where it is supposed to work.

    Asserted by resolving the guard against the real source tree rather than by running
    the (minutes-long) gate itself — the point is that the source repo is recognized.
    """
    from dadaia_workspace.infrastructure.workspace_guardrail import _is_source_repo_root

    source_root = Path(__file__).resolve().parents[3]
    assert (source_root / "pyproject.toml").is_file(), source_root
    assert _is_source_repo_root(source_root) is True


def test_preflight_fails_on_a_tracked_harness_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-doctor-job-not-a-required-check#B4: a library tree tracking .claude/settings.json
    fails `dadaia ci preflight`, naming the repo hygiene check."""
    source_root = Path(__file__).resolve().parents[3]
    lib = tmp_path / "lib"
    (lib / "dadaia_workspace" / "public").mkdir(parents=True)
    (lib / ".github" / "scripts").mkdir(parents=True)
    (lib / ".claude").mkdir()
    script = ".github/scripts/check_no_repo_local_claude.sh"
    (lib / script).write_bytes((source_root / script).read_bytes())
    (lib / "pyproject.toml").write_text('[tool.poetry]\nname = "dadaia-workspace"\n', "utf-8")
    (lib / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
    _git_repo(lib)
    subprocess.run(["git", "-C", str(lib), "add", "-A"], check=True)
    monkeypatch.chdir(lib)

    result = _runner.invoke(app, ["ci", "preflight", "--quick", "--no-fail-fast"])

    assert result.exit_code == 1
    assert "[FAIL] repo hygiene" in result.output
