"""Integration checks for the repository's real specs tree."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow(reason="checks the repository's real specs tree"),
]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"


def test_repo_specs_have_no_tree_errors() -> None:
    """The repository specs tree must not trigger ERROR-severity TREE issues."""
    repo_specs = _REPO_ROOT / "specs"
    if not repo_specs.exists():
        pytest.skip("specs/ not found outside the dadaia-workspace repo context")

    issues = SpecsDoctor(repo_specs, public_dir=_PUBLIC_DIR).check()
    tree_errors = [i for i in issues if i.code.startswith("TREE-") and i.severity == Severity.ERROR]

    assert tree_errors == [], "Repository specs triggered TREE ERROR invariants:\n" + "\n".join(
        f"  {issue.code}: {issue.description}" for issue in tree_errors
    )
