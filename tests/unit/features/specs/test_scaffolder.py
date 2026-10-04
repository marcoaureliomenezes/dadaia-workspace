"""Unit tests for the SDD scaffold — ``canon.scaffold`` renders the birth canon."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION
from dadaia_workspace.features.specs import SpecsDoctor
from dadaia_workspace.features.specs.canon import check_tree, scaffold

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"


def _scaffold(specs_dir: Path, *, name: str = "p", force: bool = False) -> list[Path]:
    return scaffold(specs_dir, project_name=name, force=force, public_dir=_TEMPLATES_DIR.parent)


def test_scaffold_emits_exactly_the_v6_birth_set(tmp_path: Path) -> None:
    """Intent: CONTRACT — A1.1 (T-050-05): the written set is every file on disk, the tree
    meets the canon (``check_tree`` empty) and the doctor finds nothing, the root is exactly
    the eight v6 members, no release is live, and the stubs carry frontmatter and the
    current pattern version."""
    specs_dir = tmp_path / "specs"
    result = _scaffold(specs_dir)

    assert sorted(result) == sorted(p for p in specs_dir.rglob("*") if p.is_file())
    assert check_tree(specs_dir) == []
    public = _TEMPLATES_DIR.parent
    assert SpecsDoctor(specs_dir, public_dir=public, templates_dir=_TEMPLATES_DIR).check() == []
    assert {p.name for p in specs_dir.iterdir()} == {
        "backlog",
        "bugs",
        "memory",
        "releases",
        "audits",
        "ADRs",
        "constitution.md",
        "AGENTS.md",
    }
    assert list((specs_dir / "releases").glob("*/_RELEASE.json")) == []
    for rel in ("memory/ARCHITECTURE.md", "memory/QUALITY.md", "memory/product/index.md"):
        assert (specs_dir / rel).read_text(encoding="utf-8").startswith("---"), rel
    constitution = (specs_dir / "constitution.md").read_text(encoding="utf-8")
    assert f"specs_pattern_version: {CANONICAL_SPECS_VERSION}" in constitution


def test_scaffold_idempotent_force_and_template_render(tmp_path: Path) -> None:
    """A second run writes nothing; --force replaces mutated content."""
    specs_dir = tmp_path / "specs"
    born = _scaffold(specs_dir)
    assert _scaffold(specs_dir) == []

    arch_path = specs_dir / "memory" / "ARCHITECTURE.md"
    arch_path.write_text("# MUTATED\n", encoding="utf-8")
    assert sorted(_scaffold(specs_dir, name="new-name", force=True)) == sorted(born)
    assert arch_path.read_text(encoding="utf-8").startswith("---")
