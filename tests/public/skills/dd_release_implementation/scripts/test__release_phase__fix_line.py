"""The release phase fixes are spelled over their words: a blank in the path stays one word, and
no fix holds a shell substitution."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import command, run

_PHASE = load_owner("dd-release-implementation", "_release_phase")


def test_the_worktree_list_fix_quotes_a_root_with_a_blank(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        _PHASE, "run", lambda argv, **_: subprocess.CompletedProcess(argv, 1, "", "")
    )
    root = tmp_path / "a b"
    root.mkdir()
    with pytest.raises(_PHASE.Refusal) as refused:
        _PHASE._worktree_rows(root)
    owner = Path(_PHASE.__file__).resolve().parents[2] / "dd-gitflow-default/scripts/worktree.py"
    assert refused.value.fix == command(sys.executable, str(owner), "list")


def test_a_missing_spec_is_written_by_its_agent_and_a_draft_is_approved_by_the_operator(
    tmp_path: Path,
) -> None:
    live = SimpleNamespace(release_id="1.0.0", release_dir=tmp_path, candidate=tmp_path / "rc-1")
    (tmp_path / "rc-1").mkdir()
    with pytest.raises(_PHASE.Refusal) as missing:
        _PHASE._refuse_unapproved_docs(live)
    spec = (tmp_path / "rc-1" / "SPEC.md").resolve()
    assert missing.value.fix == (
        f"Agent action: write {spec} (its writer per specs/AGENTS.md §4) and put it to the operator for approval"
    )
    spec.write_text("**Status:** Draft\n", encoding="utf-8")
    with pytest.raises(_PHASE.Refusal) as draft:
        _PHASE._refuse_unapproved_docs(live)
    assert draft.value.fix == f"Operator action: set '**Status:** Approved' in {spec}"


def test_an_unspawnable_worktree_owner_refuses_with_its_one_fix_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(argv[0])

    monkeypatch.setattr(_PHASE, "run", missing)
    with pytest.raises(_PHASE.Refusal) as refused:
        _PHASE._worktree_rows(tmp_path)
    owner = Path(_PHASE.__file__).resolve().parents[2] / "dd-gitflow-default/scripts/worktree.py"
    assert refused.value.fix == command(sys.executable, str(owner), "list")


@pytest.fixture
def closing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The `specs/` of repo `r` inside a tmp workspace, no fenced root."""
    monkeypatch.delenv("DADAIA_FENCED_ROOTS", raising=False)
    (tmp_path / ".dadaia/states").mkdir(parents=True)
    (tmp_path / ".dadaia/states/spec_contexts.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repos/r"
    (repo / "specs").mkdir(parents=True)
    run(["git", "init", "-q", str(repo)], check=True)
    return repo / "specs"


def _row(path: str, **facts: object) -> dict[str, object]:
    return {
        "repo": "r",
        "path": path,
        "state": "open",
        "kind": "task",
        "exit": "",
        "fix": "",
        **facts,
    }


@pytest.mark.parametrize(("leaf", "kind", "held"), [("own", "rc", 0), ("wt-rc", "task", 1)])
def test_the_closure_spares_a_wt_rc_row_by_its_kind_not_by_its_leaf_name(
    closing: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, leaf: str, kind: str, held: int
) -> None:
    rows = [_row(str(tmp_path / "w" / leaf), kind=kind)]
    monkeypatch.setattr(_PHASE, "_worktree_rows", lambda _root: rows)
    if not held:
        assert _PHASE._refuse_open_worktrees(closing.resolve()) is None
    else:
        with pytest.raises(_PHASE.Refusal, match=r"repos/r still holds 1 open wt/\* worktree"):
            _PHASE._refuse_open_worktrees(closing.resolve())


def test_the_closure_names_the_repo_by_the_main_checkout_helper(
    closing: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_PHASE._git, "main_checkout", lambda _repo: tmp_path / "elsewhere/zrepo")
    monkeypatch.setattr(
        _PHASE, "_worktree_rows", lambda _root: [_row(str(tmp_path / "w/t"), repo="zrepo")]
    )
    with pytest.raises(_PHASE.Refusal, match=r"repos/zrepo still holds 1 open wt/\* worktree"):
        _PHASE._refuse_open_worktrees(closing.resolve())


@pytest.mark.parametrize(
    ("facts", "line"),
    [
        (
            {"kind": "task", "state": "ready", "exit": "worktree.py merge /w/t", "fix": "x"},
            "worktree.py merge /w/t",
        ),
        (
            {"kind": "main", "state": "open", "exit": "worktree.py merge /w/m", "fix": ""},
            "worktree.py merge /w/m",
        ),
        (
            {"kind": "paused", "state": "paused", "exit": "worktree.py resume /w/t", "fix": ""},
            "worktree.py resume /w/t",
        ),
        (
            {
                "kind": "hotfix",
                "state": "orphan",
                "exit": "git branch -d wt/x",
                "fix": "git branch -d wt/x",
            },
            "git branch -d wt/x",
        ),
    ],
)
def test_the_closure_prints_the_owner_exit_else_the_owner_fix(
    closing: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, facts: dict[str, str], line: str
) -> None:
    row = _row(str(tmp_path / "worktrees/r/stray"), **facts)
    monkeypatch.setattr(_PHASE, "_worktree_rows", lambda _root: [row])
    with pytest.raises(_PHASE.Refusal) as refused:
        _PHASE._refuse_open_worktrees(closing.resolve())
    assert refused.value.fix == line


@pytest.mark.parametrize("state", ["foreign", "unregistered", "orphan"])
def test_the_closure_holds_a_row_with_no_grammar_kind(
    closing: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    row = _row(str(tmp_path / "worktrees/r/stray"), kind=None, state=state, fix="land it")
    monkeypatch.setattr(_PHASE, "_worktree_rows", lambda _root: [row])
    with pytest.raises(_PHASE.Refusal, match=r"repos/r still holds 1 open wt/\* worktree") as held:
        _PHASE._refuse_open_worktrees(closing.resolve())
    assert held.value.fix == "land it"


@pytest.mark.parametrize("kind", [None, "task"])
def test_the_closure_spares_the_row_of_the_tree_it_runs_from(
    closing: Path, monkeypatch: pytest.MonkeyPatch, kind: str | None
) -> None:
    row = _row(str(closing.parent), kind=kind)
    monkeypatch.setattr(_PHASE, "_worktree_rows", lambda _root: [row])
    assert _PHASE._refuse_open_worktrees(closing.resolve()) is None


def test_the_closure_outside_any_git_checkout_refuses_with_one_fix_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DADAIA_FENCED_ROOTS", raising=False)
    (tmp_path / ".dadaia/states").mkdir(parents=True)
    (tmp_path / ".dadaia/states/spec_contexts.json").write_text("{}", encoding="utf-8")
    specs = tmp_path / "repos/r/specs"
    specs.mkdir(parents=True)
    with pytest.raises(_PHASE.Refusal) as refused:
        _PHASE._refuse_open_worktrees(specs.resolve())
    assert refused.value.fix.startswith("Agent action: ")
    assert "\n" not in refused.value.fix
