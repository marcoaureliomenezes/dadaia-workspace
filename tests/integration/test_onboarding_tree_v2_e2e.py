"""AC-O-1: Onboarding E2E — copytree-from-scaffold path → v2 tree → doctor exit-0.

Exercises the exact onboarding path that `dadaia context activate` uses:
  shutil.copytree(_SCAFFOLD_SRC, specs_dir)
from dadaia_workspace/public/scaffold/ into a fresh tmp_path/specs.

This is distinct from AC-T9-15 (which exercises the scaffold() function path).

memory-markdown-source-v1 (T-MMS-10/11): The scaffold now ships ONLY .md born-markdown
atoms for memory.  The legacy YAML stubs (architecture.yaml, tech-stack.yaml,
product/index.yaml), Jinja templates, and placeholder.html were all deleted.
The copytree path therefore:
  - Contains .md atoms (architecture.md, tech-stack.md, product/index.md).
  - Does NOT contain YAML stubs or HTML files for those atoms.
  - A fresh copytree must produce 0 TREE-* ERROR-severity doctor issues.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from dadaia_workspace.features.specs import Severity, SpecsDoctor

# Repo root: tests/integration/test_onboarding_tree_v2_e2e.py → 3 parents up = repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCAFFOLD_SRC = _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold"
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"


def test_ac_o1_copytree_scaffold_produces_valid_v2_tree(tmp_path: Path) -> None:
    """AC-O-1 (updated memory-markdown-source-v1): A specs/ tree materialised via copytree
    from public/scaffold/ (the exact mechanism used by `dadaia context activate`) must:
      1. Contain the v2 mandatory directories (backlog/, bugs/, releases/) each with
         README.md and .gitkeep.
      2. Contain the born-markdown memory atoms (architecture.md, tech-stack.md,
         product/index.md), each with valid YAML frontmatter.
      3. Contain specs/AGENTS.md (the SDD workflow contract).
      4. NOT contain specs/foundation/ or specs/SPEC.md at the tree root.
      5. NOT contain legacy YAML stubs (.yaml) or rendered HTML files (.html) for
         memory atoms — the .md-only scaffold is the source of truth (T-MMS-10/11).
      6. Produce 0 TREE-* ERROR-severity issues when SpecsDoctor.check() is run.
    """
    specs_dir = tmp_path / "specs"

    # --- Onboarding: copy scaffold exactly as context activate does ---
    shutil.copytree(_SCAFFOLD_SRC, specs_dir)

    # ---- Assertion 1: v2 mandatory directories ----
    for dirname in ("backlog", "bugs", "releases"):
        d = specs_dir / dirname
        assert d.exists(), f"specs/{dirname}/ must exist after copytree-from-scaffold"
        assert d.is_dir(), f"specs/{dirname} must be a directory"
        assert (d / "README.md").exists(), f"specs/{dirname}/README.md must exist"
        assert (d / ".gitkeep").exists(), f"specs/{dirname}/.gitkeep must exist"

    # ---- Assertion 2: born-markdown memory atoms exist and have frontmatter ----
    md_atoms = [
        specs_dir / "memory" / "architecture.md",
        specs_dir / "memory" / "tech-stack.md",
        specs_dir / "memory" / "product" / "index.md",
    ]
    for md_path in md_atoms:
        assert md_path.exists(), f"{md_path.relative_to(tmp_path)} must exist (T-MMS-10/11)"
        content = md_path.read_text(encoding="utf-8")
        assert content.startswith("---"), (
            f"{md_path.name} must start with YAML frontmatter (T-MMS-04)"
        )

    # ---- Assertion 3: specs/AGENTS.md exists (SDD workflow contract) ----
    agents_md = specs_dir / "AGENTS.md"
    assert agents_md.exists(), "specs/AGENTS.md must exist after copytree-from-scaffold"

    # ---- Assertion 4: deprecated v1 artifacts must NOT be present ----
    assert not (specs_dir / "foundation").exists(), (
        "specs/foundation/ must NOT exist in a v2 scaffold tree"
    )
    assert not (specs_dir / "SPEC.md").exists(), (
        "specs/SPEC.md at the tree root must NOT exist in a v2 scaffold tree"
    )

    # ---- Assertion 5: no legacy YAML stubs or HTML atoms (T-MMS-10/11) ----
    for stale in (
        specs_dir / "memory" / "architecture.yaml",
        specs_dir / "memory" / "architecture.html",
        specs_dir / "memory" / "tech-stack.yaml",
        specs_dir / "memory" / "tech-stack.html",
        specs_dir / "memory" / "product" / "index.yaml",
        specs_dir / "memory" / "product" / "index.html",
        specs_dir / "memory" / "product" / "placeholder.html",
    ):
        assert not stale.exists(), (
            f"{stale.relative_to(tmp_path)} must NOT exist in the .md-only scaffold "
            "(legacy YAML/HTML pipeline retired in T-MMS-10/11)"
        )

    # ---- Assertion 6 (AC-O-1 core): SpecsDoctor reports 0 TREE-* ERRORs ----
    doctor = SpecsDoctor(specs_dir, public_dir=_PUBLIC_DIR)
    issues = doctor.check()

    tree_errors = [i for i in issues if i.code.startswith("TREE-") and i.severity == Severity.ERROR]
    assert tree_errors == [], (
        "Fresh copytree-from-scaffold specs/ must produce 0 TREE-* ERROR issues:\n"
        + "\n".join(f"  {i.code}: {i.description}" for i in tree_errors)
    )
