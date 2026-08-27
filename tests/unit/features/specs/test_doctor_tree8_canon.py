"""TREE-8: the v6 canon root — nothing beyond canon (T-050-05, FR1, A1.2).

Intent: CONTRACT — A1.2.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs.scaffolder import scaffold

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"


def _make_v6_tree(tmp_path: Path) -> Path:
    specs_dir = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs_dir,
        project_name="tree8-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], f"Scaffold errors: {result.errors}"
    return specs_dir


def test_tree8_is_silent_on_a_conformant_v6_tree(tmp_path: Path) -> None:
    """A freshly scaffolded (v6-canon) tree produces zero TREE-8 findings — the
    canon root is exactly backlog/, bugs/, memory/, releases/, audits/, ADRs/,
    constitution.md, AGENTS.md."""
    specs_dir = _make_v6_tree(tmp_path)
    issues = SpecsDoctor(specs_dir).check()
    tree8 = [i for i in issues if i.code == "TREE-8"]
    assert tree8 == [], f"Unexpected TREE-8 on a conformant v6 tree: {tree8}"


def test_tree8_warns_on_a_stray_root_entry(tmp_path: Path) -> None:
    """A1.2: TREE-8 reports any path directly under specs/ that is not a v6 canon
    root member, as WARNING (never ERROR) — never fixable, compliance is WARN-only
    (D15)."""
    specs_dir = _make_v6_tree(tmp_path)
    stray = specs_dir / "scratch-legacy-folder"
    stray.mkdir()
    (stray / "note.md").write_text("stray content\n", encoding="utf-8")

    issues = SpecsDoctor(specs_dir).check()
    tree8 = [i for i in issues if i.code == "TREE-8"]
    assert len(tree8) == 1, f"Expected exactly one TREE-8 finding, got: {tree8}"
    finding = tree8[0]
    assert finding.severity == Severity.WARNING, "TREE-8 must never be ERROR (D15)"
    assert finding.fixable is False
    assert finding.path == str(stray)


def test_tree8_ignores_dotfiles_at_root(tmp_path: Path) -> None:
    """Editor/OS dotfile artifacts directly under specs/ are not TREE-8 findings."""
    specs_dir = _make_v6_tree(tmp_path)
    (specs_dir / ".DS_Store").write_text("", encoding="utf-8")

    issues = SpecsDoctor(specs_dir).check()
    tree8 = [i for i in issues if i.code == "TREE-8"]
    assert tree8 == []
