"""Intent: CONTRACT — context-alive-copies-scaffold-image-bypassing-canon-fold (AC-O-1).

AC-O-1's surviving half: this repository's real ``specs/`` tree produces 0 TREE-* ERROR
issues. The alive-born-tree half died with alive's specs scaffold (0.4.8 T-048-02, AC3.7).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace import container  # noqa: E402
from dadaia_workspace.features.specs import Severity, SpecsDoctor  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"


def test_repository_own_specs_tree_has_no_tree_errors() -> None:
    """AC-O-1's second half, unchanged: this repository's real ``specs/`` tree produces 0
    TREE-* ERROR issues."""
    repo_specs = _REPO_ROOT / "specs"
    if not repo_specs.exists():
        pytest.skip("specs/ not found outside the dadaia-workspace repo context")

    issues = SpecsDoctor(
        repo_specs, public_dir=_PUBLIC_DIR, bug_store_factory=container.build_bug_record_store
    ).check()
    tree_errors = [i for i in issues if i.code.startswith("TREE-") and i.severity is Severity.ERROR]
    assert tree_errors == [], "Repository specs triggered TREE ERROR invariants:\n" + "\n".join(
        f"  {issue.code}: {issue.description}" for issue in tree_errors
    )
