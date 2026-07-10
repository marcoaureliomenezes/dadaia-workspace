"""v0.1.73 FR6 (bug ``stray-dadaia-tmp-inside-repo``): REPO-DADAIA-1 — a `.dadaia/`
directory INSIDE a context repo is a hard violation (workspace-level only; corrupts
workspace-vs-repo boundary detection). Doctor flags it; --fix reclaims it when it holds
no `states/` (a stray tmp landing zone); a `.dadaia/` WITH `states/` is never auto-removed.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs.doctor import SpecsDoctor


def _specs_tree(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    specs = repo / "specs"
    specs.mkdir(parents=True)
    return specs


def test_repo_dadaia1_flags_fixes_and_stays_silent_without_it(tmp_path: Path) -> None:
    # flags a stray in-repo .dadaia/, fixable.
    specs_a = _specs_tree(tmp_path / "a")
    stray_a = specs_a.parent / ".dadaia" / "tmp" / "code-reviewer" / "20260709"
    stray_a.mkdir(parents=True)
    issues_a = SpecsDoctor(specs_a).check()
    codes_a = [i.code for i in issues_a]
    assert "REPO-DADAIA-1" in codes_a
    issue_a = next(i for i in issues_a if i.code == "REPO-DADAIA-1")
    assert issue_a.fixable is True

    # --fix reclaims a stray with no states/.
    specs_b = _specs_tree(tmp_path / "b")
    stray_b = specs_b.parent / ".dadaia" / "tmp" / "x"
    stray_b.mkdir(parents=True)
    doctor_b = SpecsDoctor(specs_b)
    fixed_b = doctor_b.fix()
    assert any(i.code == "REPO-DADAIA-1" for i in fixed_b)
    assert not (specs_b.parent / ".dadaia").exists()

    # no issue at all without an in-repo .dadaia/.
    specs_c = _specs_tree(tmp_path / "c")
    issues_c = SpecsDoctor(specs_c).check()
    assert not any(i.code == "REPO-DADAIA-1" for i in issues_c)

    # a .dadaia/ WITH states/ is flagged but never auto-removed (operator decision).
    specs_d = _specs_tree(tmp_path / "d")
    (specs_d.parent / ".dadaia" / "states").mkdir(parents=True)
    (specs_d.parent / ".dadaia" / "states" / "spec_contexts.json").write_text(
        "{}", encoding="utf-8"
    )
    doctor_d = SpecsDoctor(specs_d)
    issues_d = doctor_d.check()
    issue_d = next(i for i in issues_d if i.code == "REPO-DADAIA-1")
    assert issue_d.fixable is False  # states/ present — operator decision, never auto-remove
    doctor_d.fix(issues_d)
    assert (specs_d.parent / ".dadaia" / "states").exists()
