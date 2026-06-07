"""Workflow catalog fixture tests.

Asserts exactly 2 generic workflows ship in the public default surface
after the v0.1.8/v0.1.9 surface reduction (7 old workflows deleted,
2 new ones — release-ship and audit-fanout — replace them).

These tests read from the canonical source directory
dadaia_workspace/public/workflows/ — no mocks, no fakes.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_WORKFLOWS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "workflows"

# The exact public workflow catalog shipped by the package (v0.1.9 surface).
_EXPECTED_SURVIVING_WORKFLOWS: frozenset[str] = frozenset(
    [
        "audit-fanout",
        "release-ship",
    ]
)


def _workflow_names() -> frozenset[str]:
    """Return the set of workflow names present in public/workflows/."""
    return frozenset(
        p.name.removesuffix(".workflow.md") for p in _WORKFLOWS_DIR.glob("*.workflow.md")
    )


def test_exactly_2_workflows_survive() -> None:
    """Exactly 2 generic workflows must remain in public/workflows/ (v0.1.9 surface)."""
    names = _workflow_names()
    assert len(names) == 2, f"Expected 2 workflows, found {len(names)}: {sorted(names)}"


def test_surviving_workflow_names_match_expected_set() -> None:
    """The public workflow catalog matches the current canonical set."""
    names = _workflow_names()
    assert names == _EXPECTED_SURVIVING_WORKFLOWS, (
        f"Surviving workflows mismatch.\n"
        f"  Expected: {sorted(_EXPECTED_SURVIVING_WORKFLOWS)}\n"
        f"  Got:      {sorted(names)}\n"
        f"  Missing:  {sorted(_EXPECTED_SURVIVING_WORKFLOWS - names)}\n"
        f"  Extra:    {sorted(names - _EXPECTED_SURVIVING_WORKFLOWS)}"
    )
