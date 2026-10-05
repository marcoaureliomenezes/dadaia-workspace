"""AC6.4 amended, ADR 0048 (reviewer H3 repro ws13): the pre-push gate
reads the gitflow from committed data — HEAD's constitution, else the newest one on a
remote-tracking ref — never the working tree. Neither -> default + one warning:
e2e/test_push_gate_check.py::test_an_absent_gitflow_block_warns_and_falls_back_to_the_default.
Size: MEDIUM (real git repos on disk)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.core.gitflow import Gitflow

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
    assert ci._gate_inputs(repo, "")[0] == Gitflow("trunk", "next", "work/")
    assert "WARNING" not in capsys.readouterr().err


def test_the_gate_names_the_live_release_work_branch(repo: Path) -> None:
    """sa-live-work-branch-named-three-ways#B41-3: no live release -> work/0.1.0. sa-live-work-branch-named-three-ways#B41-2: live 0.5.0 -> work/0.5.0."""
    assert ci._gate_inputs(repo, "")[1].work == "work/0.1.0"
    (repo / "specs/releases/0.5.0").mkdir(parents=True)
    (repo / "specs/releases/0.5.0/_RELEASE.json").write_text("{}", encoding="utf-8")
    assert ci._gate_inputs(repo, "")[1].work == "work/0.5.0"


def test_heads_constitution_wins_over_the_working_tree(repo: Path) -> None:
    _git(repo, "checkout", "-q", "trunk")
    (repo / "specs" / "constitution.md").write_text("# an uncommitted edit\n", encoding="utf-8")
    assert ci._gate_inputs(repo, "")[0] == Gitflow("trunk", "next", "work/")


def test_an_absent_specs_tree_is_reported_as_absent_with_the_specs_init_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    app = tmp_path / "app"
    _git(tmp_path, "init", "-q", "-b", "trunk", str(app))
    _git(app, "commit", "-q", "--allow-empty", "-m", "birth")
    ci._gate_inputs(app, "")
    err = capsys.readouterr().err
    assert "no specs/constitution.md" in err
    assert "fix: .dadaia/.venv/bin/dadaia specs init --context app" in err


def test_a_committed_constitution_without_a_block_keeps_the_no_block_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    app = tmp_path / "app"
    _git(tmp_path, "init", "-q", "-b", "trunk", str(app))
    (app / "specs").mkdir()
    (app / "specs" / "constitution.md").write_text("# no frontmatter\n", encoding="utf-8")
    _git(app, "add", "specs")
    _git(app, "commit", "-q", "-m", "constitution")
    ci._gate_inputs(app, "")
    err = capsys.readouterr().err
    assert f"{app / 'specs' / 'constitution.md'}: no gitflow block" in err
    assert "specs init" not in err
