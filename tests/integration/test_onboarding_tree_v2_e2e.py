"""AC-O-1: Onboarding E2E — copytree-from-scaffold path → v2 tree → doctor exit-0.

Exercises the exact onboarding path that `dadaia context activate` uses:
  shutil.copytree(_SCAFFOLD_SRC, specs_dir)
from dadaia_workspace/public/scaffold/ into a fresh tmp_path/specs.

This is distinct from AC-T9-15 (which exercises the scaffold() function path).

memory-markdown-source-v1 (T-MMS-10/11): The scaffold now ships ONLY .md born-markdown
atoms for memory.  The legacy YAML stubs (architecture.yaml, tech-stack.yaml,
product/index.yaml), Jinja templates, and placeholder.html were all deleted.
The copytree path therefore:
  - Contains .md atoms (ARCHITECTURE.md, TECHSTACK.md, product/index.md).
  - Does NOT contain YAML stubs or HTML files for those atoms.
  - A fresh copytree must produce 0 TREE-* ERROR-severity doctor issues.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor

# Repo root: tests/integration/test_onboarding_tree_v2_e2e.py → 3 parents up = repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCAFFOLD_SRC = _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold"
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"


def test_ac_o1_copytree_scaffold_produces_valid_v2_tree_and_repo_specs_have_no_tree_errors(
    tmp_path: Path,
) -> None:
    """AC-O-1 (updated memory-markdown-source-v1; v6 canon T-050-05/FR1): A specs/ tree
    materialised via copytree from public/scaffold/ (the exact mechanism used by
    `dadaia context activate`) must:
      1. Contain the v2 mandatory directories (backlog/, bugs/, releases/) each with
         AGENTS.md (README.md retired) and .gitkeep.
      2. Contain the born-markdown memory atoms (ARCHITECTURE.md, TECHSTACK.md,
         product/index.md), each with valid YAML frontmatter.
      3. Contain specs/AGENTS.md (the SDD workflow contract).
      4. NOT contain specs/foundation/ or specs/SPEC.md at the tree root (the
         positive v2 tree-shape contract, backed by doctor TREE-1/TREE-2).
      5. Produce 0 TREE-* ERROR-severity issues when SpecsDoctor.check() is run.
    """
    specs_dir = tmp_path / "specs"

    # --- Onboarding: copy scaffold exactly as context activate does ---
    shutil.copytree(_SCAFFOLD_SRC, specs_dir)

    # ---- Assertion 1: v2 mandatory directories ----
    for dirname in ("backlog", "bugs", "releases"):
        d = specs_dir / dirname
        assert d.exists(), f"specs/{dirname}/ must exist after copytree-from-scaffold"
        assert d.is_dir(), f"specs/{dirname} must be a directory"
        assert (d / "AGENTS.md").exists(), f"specs/{dirname}/AGENTS.md must exist"
        assert (d / ".gitkeep").exists(), f"specs/{dirname}/.gitkeep must exist"

    # ---- Assertion 2: born-markdown memory atoms exist and have frontmatter ----
    md_atoms = [
        specs_dir / "memory" / "ARCHITECTURE.md",
        specs_dir / "memory" / "TECHSTACK.md",
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

    # (The former Assertion 5 — legacy YAML/HTML absence — was removed in v0.1.51
    # FR3: it asserted a fully-retired render pipeline stays deleted, violating the
    # no-slop law, and was redundant with the .md-only copytree source. Assertion 4
    # above stays: it is the positive v2 tree-shape contract backed by the live
    # doctor checks TREE-1/TREE-2.)

    # ---- Assertion 5 (AC-O-1 core): SpecsDoctor reports 0 TREE-* ERRORs ----
    doctor = SpecsDoctor(specs_dir, public_dir=_PUBLIC_DIR)
    issues = doctor.check()

    tree_errors = [i for i in issues if i.code.startswith("TREE-") and i.severity == Severity.ERROR]
    assert tree_errors == [], (
        "Fresh copytree-from-scaffold specs/ must produce 0 TREE-* ERROR issues:\n"
        + "\n".join(f"  {i.code}: {i.description}" for i in tree_errors)
    )

    # The repository's own real specs tree must also produce 0 TREE-* ERROR issues.
    repo_specs = _REPO_ROOT / "specs"
    if not repo_specs.exists():
        pytest.skip("specs/ not found outside the dadaia-workspace repo context")

    repo_issues = SpecsDoctor(repo_specs, public_dir=_PUBLIC_DIR).check()
    repo_tree_errors = [
        i for i in repo_issues if i.code.startswith("TREE-") and i.severity == Severity.ERROR
    ]
    assert repo_tree_errors == [], (
        "Repository specs triggered TREE ERROR invariants:\n"
        + "\n".join(f"  {issue.code}: {issue.description}" for issue in repo_tree_errors)
    )
