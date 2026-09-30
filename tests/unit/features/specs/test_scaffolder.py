"""Unit tests for the SDD scaffold — ``canon.scaffold`` renders the birth canon."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION
from dadaia_workspace.features.specs.canon import scaffold

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"

# The complete v6 birth set (T-050-05): no README.md, no assets/, no .gitkeep.
_EXPECTED_FILES = [
    "constitution.md",
    "AGENTS.md",
    "memory/AGENTS.md",
    "memory/ARCHITECTURE.md",
    "memory/QUALITY.md",
    "memory/product/index.md",
    "releases/AGENTS.md",
    "backlog/AGENTS.md",
    "backlog/BACKLOG.json",
    "bugs/AGENTS.md",
    "audits/AGENTS.md",
    "ADRs/AGENTS.md",
    "ADRs/decisions.jsonl",
    "releases/_archive/releases_histo.jsonl",
    "backlog/_archive/backlog_histo.jsonl",
    "bugs/_archive/bugs_histo.jsonl",
    "audits/_archive/audits_histo.jsonl",
]


def _scaffold(specs_dir: Path, *, name: str = "p", force: bool = False) -> list[Path]:
    return scaffold(specs_dir, project_name=name, force=force, public_dir=_TEMPLATES_DIR.parent)


def test_scaffold_emits_exactly_the_v6_birth_set(tmp_path: Path) -> None:
    """Intent: CONTRACT — A1.1 (T-050-05): the written set is exactly the canon files, the
    root is exactly the eight v6 members, no release is live, and the stubs carry
    frontmatter and the current pattern version."""
    specs_dir = tmp_path / "specs"
    result = _scaffold(specs_dir)

    assert sorted(p.relative_to(specs_dir).as_posix() for p in result) == sorted(_EXPECTED_FILES)
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
    assert len(_scaffold(specs_dir)) == len(_EXPECTED_FILES)
    assert _scaffold(specs_dir) == []

    arch_path = specs_dir / "memory" / "ARCHITECTURE.md"
    arch_path.write_text("# MUTATED\n", encoding="utf-8")
    assert len(_scaffold(specs_dir, name="new-name", force=True)) == len(_EXPECTED_FILES)
    assert arch_path.read_text(encoding="utf-8").startswith("---")
