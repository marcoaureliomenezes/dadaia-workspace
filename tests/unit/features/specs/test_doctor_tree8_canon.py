"""TREE-8: the v6 canon root — nothing beyond canon (T-050-05, FR1, A1.2).

v0.5.0 specs-canon closure: TREE-8 tightens from WARN-only/dotfile-exempt to
ERROR, and its dotfile sweep now reaches the WHOLE specs/ tree, not
just the root — a directory is kept by its AGENTS.md, never a placeholder file
(the retired .gitkeep landing-zone mechanism). TREE-2's deprecated root SPEC.md
stays exempt: TREE-2 owns it, fixable=False.

TREE-8 is never auto-fixed: ``doctor --fix`` deletes nothing (operator decision D8).

Intent: CONTRACT — A1.2, v0.5.0 specs-canon closure; doctor-fix-tree8-deletes-operator-content.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs.canon import scaffold

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
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
    ["README.md", "features/login.md", ".DS_Store", "backlog/.gitkeep"],
)
def test_tree8_reports_a_non_canon_path_and_fix_never_deletes_it(tmp_path: Path, rel: str) -> None:
    """Bug doctor-fix-tree8-deletes-operator-content (operator decision D8): a
    non-canon path — root file, root folder with content, root or nested dotfile —
    is a TREE-8 ERROR the operator resolves by hand; ``doctor --fix`` leaves it on
    disk and the finding stands (the live repro rmtree'd specs/README.md and
    specs/features/login.md)."""
    specs_dir = _make_v6_tree(tmp_path)
    stray = specs_dir / rel
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text("operator content\n", encoding="utf-8")
    flagged = specs_dir / rel.split("/")[0] if rel.startswith("features/") else stray

    doctor = SpecsDoctor(specs_dir)
    issues = doctor.check()
    tree8 = [i for i in issues if i.code == "TREE-8" and i.path == str(flagged)]
    assert len(tree8) == 1, f"Expected one TREE-8 finding for {flagged}, got: {tree8}"
    assert tree8[0].severity == Severity.ERROR
    assert tree8[0].fixable is False

    doctor.fix(issues)
    assert stray.read_text(encoding="utf-8") == "operator content\n"
    assert [i for i in doctor.check() if i.code == "TREE-8" and i.path == str(flagged)]


def test_tree8_never_removes_foundation_and_defers_root_spec_md(tmp_path: Path) -> None:
    """--fix never removes specs/foundation/ (an earlier TREE-8 draft auto-deleted it);
    specs/SPEC.md is TREE-2's, fixable=False."""
    specs_dir = _make_v6_tree(tmp_path)
    foundation = specs_dir / "foundation"
    foundation.mkdir()
    (foundation / "vision.md").write_text("# Vision\n\nLegacy content.\n", encoding="utf-8")
    (specs_dir / "SPEC.md").write_text("# Legacy root SPEC\n", encoding="utf-8")

    doctor = SpecsDoctor(specs_dir)
    issues = doctor.check()
    tree8_paths = {i.path for i in issues if i.code == "TREE-8"}
    assert str(specs_dir / "SPEC.md") not in tree8_paths

    tree2 = [i for i in issues if i.code == "TREE-2"]
    assert tree2 and tree2[0].fixable is False

    doctor.fix(issues)
    assert foundation.exists(), "TREE-8 auto-fix must never remove specs/foundation/"
    assert (specs_dir / "SPEC.md").exists(), "TREE-8 auto-fix must never remove specs/SPEC.md"
