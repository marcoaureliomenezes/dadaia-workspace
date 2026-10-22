"""The pre-push gate's gitflow input over a committed constitution.

With no committed constitution it reports the absent specs tree with the ``specs init`` fix;
with a committed constitution that has no gitflow block it warns and offers no ``specs init`` fix.
Size: MEDIUM (real git repos on disk)."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.core.gitflow import Gitflow
from tests.helpers.oslib import run, write_text

_CUSTOM = "---\nspecs_pattern_version: 7\ngitflow: {principal: trunk, integration: next, work: work/}\n---\n"


def _git(repo: Path, *args: str) -> None:
    run(["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *args], cwd=repo, check=True)


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
    write_text(repo / "specs" / "constitution.md", _CUSTOM)
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
    """The repo's one local work branch is the work branch, whatever release is live; with none,
    a live 0.5.0 names work/0.5.0."""
    assert ci._gate_inputs(repo, "")[1].work == "work/0.1.1"
    (repo / "specs/releases/0.5.0").mkdir(parents=True)
    write_text(repo / "specs/releases/0.5.0/_RELEASE.json", "{}")
    assert ci._gate_inputs(repo, "")[1].work == "work/0.1.1"
    _git(repo, "checkout", "-q", "trunk")
    _git(repo, "branch", "-D", "work/0.1.1")
    assert ci._gate_inputs(repo, "")[1].work == "work/0.5.0"


def test_two_work_branches_name_the_one_the_rule_keeps_not_the_pushed_branch(repo: Path) -> None:
    _git(repo, "branch", "work/0.1.2")
    _git(repo, "switch", "-q", "-c", "foo")
    assert ci._gate_inputs(repo, "foo")[1].work == "work/0.1.2"


def test_several_live_releases_block_the_gate_with_the_refusals_own_fix(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _git(repo, "switch", "-q", "-c", "foo")
    _git(repo, "branch", "-D", "work/0.1.1")
    for release in ("0.5.0", "0.6.0"):
        (repo / "specs/releases" / release).mkdir(parents=True)
        write_text(repo / "specs/releases" / release / "_RELEASE.json", "{}")

    with pytest.raises(typer.Exit):
        ci._gate_inputs(repo, "foo")

    assert capsys.readouterr().err.splitlines()[-1] == (
        f"fix: Agent action: keep one of 0.5.0, 0.6.0 live under {repo / 'specs/releases'};"
        " ship or move out the others"
    )


def test_heads_constitution_wins_over_the_working_tree(repo: Path) -> None:
    _git(repo, "checkout", "-q", "trunk")
    write_text(repo / "specs" / "constitution.md", "# an uncommitted edit\n")
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
    from dadaia_workspace.infrastructure.git_subprocess import gitflow_fix

    assert "no committed specs/constitution.md" in err
    fixes = [line for line in err.splitlines() if line.startswith(("fix: ", "hint: "))]
    assert fixes == [f"fix: {gitflow_fix(app / 'specs')}"]
    assert fixes[0].startswith("fix: Agent action: ")


def test_a_committed_constitution_without_a_block_keeps_the_no_block_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    app = tmp_path / "app"
    _git(tmp_path, "init", "-q", "-b", "trunk", str(app))
    (app / "specs").mkdir()
    write_text(app / "specs" / "constitution.md", "# no frontmatter\n")
    _git(app, "add", "specs")
    _git(app, "commit", "-q", "-m", "constitution")
    ci._gate_inputs(app, "")
    err = capsys.readouterr().err
    assert f"{app / 'specs' / 'constitution.md'}: no gitflow block" in err
    assert "specs init" not in err
