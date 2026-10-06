"""TREE-8: the v6 canon root — nothing beyond canon (T-050-05, FR1, A1.2).

v0.5.0 specs-canon closure: TREE-8 tightens from WARN-only/dotfile-exempt to
ERROR, and its dotfile sweep now reaches the WHOLE specs/ tree, not
just the root — a directory is kept by its AGENTS.md, never a placeholder file
(the retired .gitkeep landing-zone mechanism). TREE-8 alone judges placement
(sa-placement-rules-contradict-tree8): one finding per stray path, no second rule.

TREE-8 is never auto-fixed: ``doctor --fix`` deletes nothing (operator decision D8).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import SpecsDoctor
from dadaia_workspace.features.specs.canon import scaffold
from dadaia_workspace.features.specs.doctor_types import finding_path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"


def _make_v6_tree(tmp_path: Path) -> Path:
    specs_dir = tmp_path / "specs"
    scaffold(
        specs_dir,
        project_name="tree8-project",
        force=False,
        public_dir=_TEMPLATES_DIR.parent,
    )
    return specs_dir


def test_tree8_is_silent_on_a_conformant_v6_tree(tmp_path: Path) -> None:
    """A freshly scaffolded (v6-canon) tree produces zero TREE-8 findings — the
    canon root is exactly backlog/, bugs/, memory/, releases/, audits/, ADRs/,
    constitution.md, AGENTS.md."""
    specs_dir = _make_v6_tree(tmp_path)
    issues = SpecsDoctor(specs_dir).check()
    tree8 = [i for i in issues if i.code == "TREE-8"]
    assert tree8 == [], f"Unexpected TREE-8 on a conformant v6 tree: {tree8}"


@pytest.mark.parametrize(
    "rel",
    [
        "README.md",
        "SPEC.md",
        "features/login.md",
        "foundation/vision.md",
        ".DS_Store",
        "backlog/.gitkeep",
        "backlog/old-idea.md",
        "memory/TECHSTACK.md",
        "memory/product.html",
        "bugs/some-bug.md",
        "releases/v0.3.0/SPEC.md",
        "releases/0.3.0/TASKS.md",
    ],
)
def test_tree8_reports_a_non_canon_path_and_fix_never_deletes_it(tmp_path: Path, rel: str) -> None:
    """sa-placement-rules-contradict-tree8#B1 sa-placement-rules-contradict-tree8#B2
    sa-placement-rules-contradict-tree8#B3 sa-placement-rules-contradict-tree8#B4
    sa-placement-rules-contradict-tree8#B6
    sa-release-dir-placement-judged-by-tree8-and-spec-doc-027, ADR 0151 M5 (a flat trio
    file): a non-canon path yields
    exactly one finding, TREE-8 (ERROR, never auto-fixed — bug
    doctor-fix-tree8-deletes-operator-content, decision D8); `doctor --fix` leaves it
    on disk; moving it out of specs/ as the fix says leaves the doctor clean."""
    specs_dir = _make_v6_tree(tmp_path)
    stray = specs_dir / rel
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text("operator content\n", encoding="utf-8")
    flagged = (
        specs_dir / rel.split("/")[0] if rel.split("/")[0] in ("features", "foundation") else stray
    )

    doctor = SpecsDoctor(specs_dir)
    issues = doctor.check()
    assert [(i.code, i.verdict, i.fixable, finding_path(i)) for i in issues] == [
        ("TREE-8", "error", False, str(flagged))
    ]

    doctor.fix(issues)
    assert stray.read_text(encoding="utf-8") == "operator content\n"
    assert [i.code for i in doctor.check()] == ["TREE-8"]

    flagged.rename(tmp_path / "moved-out")
    assert doctor.check() == []
