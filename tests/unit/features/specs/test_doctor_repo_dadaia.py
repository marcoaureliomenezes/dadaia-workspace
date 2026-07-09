"""v0.1.73 FR6 (bug ``stray-dadaia-tmp-inside-repo``): REPO-DADAIA-1 — a `.dadaia/`
directory INSIDE a context repo is a hard violation (workspace-level only; corrupts
workspace-vs-repo boundary detection). Doctor flags it; --fix reclaims it when it holds
no `states/` (a stray tmp landing zone); a `.dadaia/` WITH `states/` is never auto-removed."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs.doctor import SpecsDoctor


def _specs_tree(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    specs = repo / "specs"
    specs.mkdir(parents=True)
    return specs


def test_repo_dadaia1_flags_stray_in_repo_dadaia(tmp_path: Path) -> None:
    specs = _specs_tree(tmp_path)
    stray = specs.parent / ".dadaia" / "tmp" / "code-reviewer" / "20260709"
    stray.mkdir(parents=True)

    issues = SpecsDoctor(specs).check()
    codes = [i.code for i in issues]
    assert "REPO-DADAIA-1" in codes
    issue = next(i for i in issues if i.code == "REPO-DADAIA-1")
    assert issue.fixable is True


def test_repo_dadaia1_fix_reclaims_stray(tmp_path: Path) -> None:
    specs = _specs_tree(tmp_path)
    stray = specs.parent / ".dadaia" / "tmp" / "x"
    stray.mkdir(parents=True)

    doctor = SpecsDoctor(specs)
    fixed = doctor.fix()

    assert any(i.code == "REPO-DADAIA-1" for i in fixed)
    assert not (specs.parent / ".dadaia").exists()


def test_repo_dadaia1_with_states_flagged_but_never_auto_removed(tmp_path: Path) -> None:
    specs = _specs_tree(tmp_path)
    (specs.parent / ".dadaia" / "states").mkdir(parents=True)
    (specs.parent / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")

    doctor = SpecsDoctor(specs)
    issues = doctor.check()
    issue = next(i for i in issues if i.code == "REPO-DADAIA-1")
    assert issue.fixable is False  # states/ present — operator decision, never auto-remove

    doctor.fix(issues)
    assert (specs.parent / ".dadaia" / "states").exists()


def test_no_issue_without_in_repo_dadaia(tmp_path: Path) -> None:
    specs = _specs_tree(tmp_path)
    issues = SpecsDoctor(specs).check()
    assert not any(i.code == "REPO-DADAIA-1" for i in issues)
