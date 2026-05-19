"""Workflow catalog fixture tests — AGT-r2-07.

Asserts exactly 7 workflows survive the AGT-r2-06 trim.
The 8 deprecated files (game-spec-definition, architecture-review, tdd-cycle,
bug-fix-fastlane, game-bugfix, security-patch, deploy-validation-only,
design-validation) have been archived to
specs/_archive/legacy-workflows/<UTC>/.

These tests read from the canonical source directory
dadaia_workspace/public/workflows/ — no mocks, no fakes.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_WORKFLOWS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "workflows"

# The exact set of workflows that must survive after the P1 trim.
_EXPECTED_SURVIVING_WORKFLOWS: frozenset[str] = frozenset(
    [
        "audit-cycle",
        "code-review-fan-out",
        "cross-cutting-feature",
        "game-dev-cycle",
        "hotfix-release",
        "onboarding-new-repo",
        "spec-refinement",
    ]
)

# The 8 deprecated workflows that must NOT exist under public/workflows/.
_DEPRECATED_WORKFLOWS: frozenset[str] = frozenset(
    [
        "game-spec-definition",
        "architecture-review",
        "tdd-cycle",
        "bug-fix-fastlane",
        "game-bugfix",
        "security-patch",
        "deploy-validation-only",
        "design-validation",
    ]
)


def _workflow_names() -> frozenset[str]:
    """Return the set of workflow names present in public/workflows/."""
    return frozenset(
        p.name.removesuffix(".workflow.md") for p in _WORKFLOWS_DIR.glob("*.workflow.md")
    )


def test_exactly_7_workflows_survive() -> None:
    """After AGT-r2-06 trim, exactly 7 workflows must remain in public/workflows/."""
    names = _workflow_names()
    assert len(names) == 7, f"Expected 7 workflows, found {len(names)}: {sorted(names)}"


def test_surviving_workflow_names_match_expected_set() -> None:
    """The 7 surviving workflows are the canonical set per AGT-r2-06."""
    names = _workflow_names()
    assert names == _EXPECTED_SURVIVING_WORKFLOWS, (
        f"Surviving workflows mismatch.\n"
        f"  Expected: {sorted(_EXPECTED_SURVIVING_WORKFLOWS)}\n"
        f"  Got:      {sorted(names)}\n"
        f"  Missing:  {sorted(_EXPECTED_SURVIVING_WORKFLOWS - names)}\n"
        f"  Extra:    {sorted(names - _EXPECTED_SURVIVING_WORKFLOWS)}"
    )


def test_deprecated_workflows_absent_from_public() -> None:
    """None of the 8 deprecated workflow files must exist under public/workflows/."""
    names = _workflow_names()
    still_present = _DEPRECATED_WORKFLOWS & names
    assert not still_present, (
        f"Deprecated workflows still present in public/workflows/: {sorted(still_present)}"
    )


def test_deprecated_workflows_archived() -> None:
    """The 8 deprecated workflow files must exist in a legacy-workflows archive directory."""
    archive_root = _REPO_ROOT / "specs" / "_archive" / "legacy-workflows"
    archived: set[str] = set()
    for archive_dir in archive_root.iterdir():
        if archive_dir.is_dir():
            for wf in archive_dir.glob("*.workflow.md"):
                archived.add(wf.name.removesuffix(".workflow.md"))

    missing_from_archive = _DEPRECATED_WORKFLOWS - archived
    assert not missing_from_archive, (
        f"Deprecated workflows not found in any legacy-workflows archive: "
        f"{sorted(missing_from_archive)}"
    )
