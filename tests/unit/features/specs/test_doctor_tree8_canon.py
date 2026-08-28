"""TREE-8: the v6 canon root — nothing beyond canon (T-050-05, FR1, A1.2).

v0.5.0 specs-canon closure: TREE-8 tightens from WARN-only/dotfile-exempt to
ERROR + auto-fixable, and its dotfile sweep now reaches the WHOLE specs/ tree, not
just the root — a directory is kept by its AGENTS.md, never a placeholder file
(the retired .gitkeep landing-zone mechanism). TREE-1/TREE-2's own deprecated-layout
paths (specs/foundation/, specs/SPEC.md) stay exempt: those checks already own
reporting them, fixable=False by explicit design (auto-moving may destroy
SDD-approved content pending operator consent) — TREE-8 must never additionally
flag-and-auto-remove either.

Intent: CONTRACT — A1.2, v0.5.0 specs-canon closure.
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


def test_tree8_errors_on_a_stray_root_entry_and_fix_removes_it(tmp_path: Path) -> None:
    """A stray path directly under specs/ that is not a v6 canon root member is
    ERROR, auto-fixable — removing it via ``doctor --fix``."""
    specs_dir = _make_v6_tree(tmp_path)
    stray = specs_dir / "scratch-legacy-folder"
    stray.mkdir()
    (stray / "note.md").write_text("stray content\n", encoding="utf-8")

    doctor = SpecsDoctor(specs_dir)
    issues = doctor.check()
    tree8 = [i for i in issues if i.code == "TREE-8" and i.path == str(stray)]
    assert len(tree8) == 1, f"Expected exactly one TREE-8 finding for {stray}, got: {tree8}"
    finding = tree8[0]
    assert finding.severity == Severity.ERROR
    assert finding.fixable is True

    fixed = doctor.fix(issues)
    assert any(i.path == str(stray) for i in fixed)
    assert not stray.exists()
    residual = [i for i in doctor.check() if i.code == "TREE-8" and i.path == str(stray)]
    assert residual == []


def test_tree8_errors_on_a_dotfile_at_root_and_fix_removes_it(tmp_path: Path) -> None:
    """A dotfile directly under specs/ (e.g. an editor/OS artifact, or a stray
    .gitkeep) is ERROR, auto-fixable — the .gitkeep landing-zone mechanism is
    retired (v0.5.0): a directory is kept by its AGENTS.md, never a dotfile."""
    specs_dir = _make_v6_tree(tmp_path)
    stray = specs_dir / ".DS_Store"
    stray.write_text("", encoding="utf-8")

    doctor = SpecsDoctor(specs_dir)
    issues = doctor.check()
    tree8 = [i for i in issues if i.code == "TREE-8" and i.path == str(stray)]
    assert len(tree8) == 1, f"Expected exactly one TREE-8 finding for {stray}, got: {tree8}"
    assert tree8[0].severity == Severity.ERROR
    assert tree8[0].fixable is True

    doctor.fix(issues)
    assert not stray.exists()


def test_tree8_errors_on_a_nested_dotfile_and_fix_removes_only_it(tmp_path: Path) -> None:
    """A dotfile NESTED inside an otherwise-conformant area (e.g. a stray
    specs/backlog/.gitkeep) is also ERROR/auto-fixable — the sweep is full-tree,
    not root-only — and the fix removes only the offending file, never the
    conformant parent directory or its siblings."""
    specs_dir = _make_v6_tree(tmp_path)
    stray = specs_dir / "backlog" / ".gitkeep"
    stray.write_text("", encoding="utf-8")
    sibling = specs_dir / "backlog" / "AGENTS.md"
    assert sibling.exists(), "precondition: backlog/AGENTS.md must already exist"

    doctor = SpecsDoctor(specs_dir)
    issues = doctor.check()
    tree8 = [i for i in issues if i.code == "TREE-8" and i.path == str(stray)]
    assert len(tree8) == 1, f"Expected exactly one TREE-8 finding for {stray}, got: {tree8}"
    assert tree8[0].severity == Severity.ERROR
    assert tree8[0].fixable is True

    doctor.fix(issues)
    assert not stray.exists()
    assert sibling.exists(), "the fix must remove only the dotfile, never its conformant sibling"


def test_tree8_never_flags_the_deprecated_foundation_or_root_spec_md(tmp_path: Path) -> None:
    """specs/foundation/ and specs/SPEC.md are TREE-1/TREE-2's own deprecated-layout
    concerns — fixable=False by explicit design (auto-moving may destroy
    SDD-approved content pending operator consent). TREE-8 must never
    additionally flag-and-auto-remove either, even though neither is a v6 canon
    root member (regression seam for a real bug this task's own TDD pass caught:
    an earlier TREE-8 draft auto-deleted specs/foundation/ under --fix)."""
    specs_dir = _make_v6_tree(tmp_path)
    foundation = specs_dir / "foundation"
    foundation.mkdir()
    (foundation / "vision.md").write_text("# Vision\n\nLegacy content.\n", encoding="utf-8")
    (specs_dir / "SPEC.md").write_text("# Legacy root SPEC\n", encoding="utf-8")

    doctor = SpecsDoctor(specs_dir)
    issues = doctor.check()
    tree8_paths = {i.path for i in issues if i.code == "TREE-8"}
    assert str(foundation) not in tree8_paths
    assert str(specs_dir / "SPEC.md") not in tree8_paths

    # TREE-1/TREE-2 still report them, at their own documented fixable=False.
    tree1 = [i for i in issues if i.code == "TREE-1"]
    tree2 = [i for i in issues if i.code == "TREE-2"]
    assert tree1 and tree1[0].fixable is False
    assert tree2 and tree2[0].fixable is False

    doctor.fix(issues)
    assert foundation.exists(), "TREE-8 auto-fix must never remove specs/foundation/"
    assert (specs_dir / "SPEC.md").exists(), "TREE-8 auto-fix must never remove specs/SPEC.md"
