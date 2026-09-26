"""Intent: CONTRACT — AC6.4 amended, ADR 0048 (reviewer H3 repro ws13): the pre-push gate
reads the gitflow from committed data — HEAD's constitution, else the newest one on a
remote-tracking ref — never the working tree, and warns only when neither exists.
Size: MEDIUM (real git repos on disk)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.core.gitflow import DEFAULT, Gitflow

pytestmark = pytest.mark.integration

_CUSTOM = "---\nspecs_pattern_version: 7\ngitflow: {principal: trunk, integration: next, work: work/}\n---\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """ws13: trunk (contentless root) is published, then trunk gains the custom
    constitution on origin; ``work/0.1.1`` is cut from the contentless root."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    origin, repo = tmp_path / "origin.git", tmp_path / "app"
    _git(tmp_path, "init", "-q", "--bare", "-b", "trunk", str(origin))
    _git(tmp_path, "init", "-q", "-b", "trunk", str(repo))
    _git(repo, "commit", "-q", "--allow-empty", "-m", "birth")
    _git(repo, "branch", "work/0.1.1")
    (repo / "specs").mkdir()
    (repo / "specs" / "constitution.md").write_text(_CUSTOM, encoding="utf-8")
    _git(repo, "add", "specs")
    _git(repo, "commit", "-q", "-m", "constitution")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-q", "--no-verify", "origin", "trunk")
    _git(repo, "checkout", "-q", "work/0.1.1")
    return repo


def test_a_branch_without_specs_reads_the_newest_published_constitution(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert ci._gate_inputs(repo)[0] == Gitflow("trunk", "next", "work/")
    assert "WARNING" not in capsys.readouterr().err


def test_heads_constitution_wins_over_the_working_tree(repo: Path) -> None:
    _git(repo, "checkout", "-q", "trunk")
    (repo / "specs" / "constitution.md").write_text("# an uncommitted edit\n", encoding="utf-8")
    assert ci._gate_inputs(repo)[0] == Gitflow("trunk", "next", "work/")


def test_no_committed_constitution_is_the_default_with_one_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    bare = tmp_path / "bare"
    _git(tmp_path, "init", "-q", str(bare))
    (bare / "specs").mkdir()
    (bare / "specs" / "constitution.md").write_text(_CUSTOM, encoding="utf-8")  # untracked
    assert ci._gate_inputs(bare)[0] == DEFAULT
    assert capsys.readouterr().err.count("WARNING") == 1
