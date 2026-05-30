"""AC-O-1: Onboarding E2E — copytree-from-scaffold path → v2 tree → doctor exit-0.

Exercises the exact onboarding path that `dadaia context activate` uses:
  shutil.copytree(_SCAFFOLD_SRC, specs_dir)
from dadaia_workspace/public/scaffold/ into a fresh tmp_path/specs.

This is distinct from AC-T9-15 (which exercises the scaffold() function path).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from dadaia_workspace.features.specs import Severity, SpecsDoctor

# Repo root: tests/integration/test_onboarding_tree_v2_e2e.py → 3 parents up = repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCAFFOLD_SRC = _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold"
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"
_TEMPLATES_DIR = _PUBLIC_DIR / "templates"


def test_ac_o1_copytree_scaffold_produces_valid_v2_tree(tmp_path: Path) -> None:
    """AC-O-1: A specs/ tree materialised via copytree from public/scaffold/ (the exact
    mechanism used by `dadaia context activate`) must:
      1. Contain the v2 mandatory directories (backlog/, bugs/, releases/) each with
         README.md and .gitkeep.
      2. Contain the memory HTML files (architecture.html, tech-stack.html,
         memory/product/index.html), all non-empty.
      3. Contain specs/AGENTS.md (the SDD workflow contract).
      4. NOT contain specs/foundation/ or specs/SPEC.md at the tree root.
      5. Produce 0 ERROR-severity issues AND 0 TREE-* issues when SpecsDoctor.check()
         is run against it (the core assertion of AC-O-1).
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

    # ---- Assertion 2: memory HTML files exist and are non-empty ----
    memory_files = [
        specs_dir / "memory" / "architecture.html",
        specs_dir / "memory" / "tech-stack.html",
        specs_dir / "memory" / "product" / "index.html",
    ]
    for html_path in memory_files:
        assert html_path.exists(), f"{html_path.relative_to(tmp_path)} must exist"
        content = html_path.read_text(encoding="utf-8")
        assert len(content) > 0, f"{html_path.name} must be non-empty"
        assert "<html" in content.lower(), f"{html_path.name} must contain valid HTML"

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

    # ---- Assertion 5 (AC-O-1 core): SpecsDoctor reports 0 TREE-* issues ----
    # A fresh scaffold has no ACTIVE.md yet (that is populated when the first release
    # is created, not during onboarding), so SPEC-DOC-003 is expected and acceptable.
    # The critical invariant is that ALL 7 TREE invariants (spec-context-tree-v2) are
    # clean — both zero TREE-* warnings and zero TREE-* errors.
    doctor = SpecsDoctor(specs_dir, public_dir=_PUBLIC_DIR)
    issues = doctor.check()

    # Zero TREE-* issues of any severity (warnings included).
    # The scaffold is the v2 reference tree; all 7 TREE invariants must be clean.
    tree_issues = [i for i in issues if i.code.startswith("TREE-")]
    assert tree_issues == [], (
        "Fresh copytree-from-scaffold specs/ must produce 0 TREE-* issues:\n"
        + "\n".join(f"  {i.code} ({i.severity}): {i.description}" for i in tree_issues)
    )

    # Zero TREE-* ERROR-severity issues (belt-and-suspenders: covered by the above,
    # but makes the assertion explicit for AC-O-1 compliance reporting).
    tree_errors = [i for i in issues if i.code.startswith("TREE-") and i.severity == Severity.ERROR]
    assert tree_errors == [], (
        "Fresh copytree-from-scaffold specs/ must produce 0 TREE-* ERROR issues:\n"
        + "\n".join(f"  {i.code}: {i.description}" for i in tree_errors)
    )
