"""Integration tests for doctor() Codex drift checks D-CX-1 through D-CX-5.

Covers acceptance criteria:
  - D-CX-1: missing TOML is reported as [missing] and not [ok]
  - D-CX-3: artificial removal of a workflow is reported as [missing]
  - D-CX-5: corrupted developer_instructions in a TOML reports the agent

Strategy
--------
Each test performs a full stage + install cycle into ``tmp_path`` using the real
``_public_dir`` (the package's own ``public/`` directory with all canonical
agents and workflows).  After install, the test mutates the installed
``.codex/`` artifacts and re-runs ``doctor(tmp_path)`` to confirm the drift is
caught.

This approach exercises the actual public assets and the real TOML generation
pipeline rather than synthetic fixtures, ensuring the checks are not bypassed by
mock substitution.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def installed_workspace(tmp_path: Path) -> Path:
    """Full stage + install cycle for target=codex using real public assets.

    Returns the ``workspace_root`` (``tmp_path``) after the install completes.
    All 20 canonical agent TOMLs and all canonical workflows are present in
    ``.codex/`` after this fixture runs.
    """
    manager = FileSystemPublicAssetManager()
    manager.stage(tmp_path)
    manager.install(tmp_path, target="codex", force=True)
    return tmp_path


# ---------------------------------------------------------------------------
# AC7 — artificial removal of a canonical workflow is detected (D-CX-3)
# ---------------------------------------------------------------------------


def test_ac7_missing_workflow_detected(installed_workspace: Path) -> None:
    """Removing a canonical workflow from .codex/workflows/ is caught as [missing] D-CX-3.

    Given: a workspace with all canonical workflows installed in .codex/workflows/
    When:  one workflow file is deleted from .codex/workflows/
    Then:  doctor() returns at least one report starting with [missing] that
           contains both 'D-CX-3' and the name of the deleted workflow file.
    """
    workspace_root = installed_workspace
    codex_workflows = workspace_root / ".codex" / "workflows"

    # Choose a canonical workflow file that must exist after install.
    # release-ship.workflow.md is one of the two canonical workflows shipped by v0.1.9+.
    target_workflow = "release-ship.workflow.md"
    workflow_path = codex_workflows / target_workflow
    assert workflow_path.exists(), (
        f"Pre-condition failed: expected {target_workflow} to exist after install. "
        f"Files present: {sorted(f.name for f in codex_workflows.glob('*.workflow.md'))}"
    )

    # Remove the workflow to simulate drift.
    workflow_path.unlink()

    manager = FileSystemPublicAssetManager()
    reports = manager.doctor(workspace_root)

    missing_dcx3 = [
        r for r in reports if r.startswith("[missing]") and "D-CX-3" in r and "release-ship" in r
    ]
    assert missing_dcx3, (
        "Expected at least one '[missing] ... D-CX-3 ... release-ship' "
        "report but found none.\nAll reports:\n" + "\n".join(reports)
    )


# ---------------------------------------------------------------------------
# AC8 — corrupted developer_instructions is detected by name (D-CX-5)
# ---------------------------------------------------------------------------


def test_ac8_corrupted_toml_detected(installed_workspace: Path) -> None:
    """Emptying developer_instructions in a TOML is caught as [error] D-CX-5 naming the agent.

    Given: a workspace with all canonical agent TOMLs installed in .codex/agents/
    When:  the developer_instructions field in qa-engineer.toml is replaced with
           an empty string
    Then:  doctor() returns at least one report containing 'D-CX-5' and 'qa-engineer'.
    """
    workspace_root = installed_workspace
    toml_path = workspace_root / ".codex" / "agents" / "qa-engineer.toml"
    assert toml_path.exists(), (
        f"Pre-condition failed: qa-engineer.toml must exist after install. "
        f"Files in .codex/agents/: {sorted(f.name for f in (workspace_root / '.codex' / 'agents').glob('*.toml'))}"
    )

    # Read and parse to confirm the field exists and is non-empty before corruption.
    original_text = toml_path.read_text(encoding="utf-8")
    original_data = tomllib.loads(original_text)
    assert original_data.get("developer_instructions", "").strip(), (
        "Pre-condition failed: qa-engineer.toml should have non-empty developer_instructions before corruption."
    )

    # Empty developer_instructions using regex substitution on the raw TOML.
    corrupted = re.sub(
        r'developer_instructions\s*=\s*""".*?"""',
        'developer_instructions = """"""',
        original_text,
        flags=re.DOTALL,
    )
    toml_path.write_text(corrupted, encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    reports = manager.doctor(workspace_root)

    dcx5_qa = [r for r in reports if "D-CX-5" in r and "qa-engineer" in r]
    assert dcx5_qa, (
        "Expected at least one D-CX-5 report naming 'qa-engineer' after emptying "
        "developer_instructions.\nAll reports:\n" + "\n".join(reports)
    )


# ---------------------------------------------------------------------------
# AC9 — missing TOML is not reported as [ok] and is reported as [missing] (D-CX-1)
# ---------------------------------------------------------------------------


def test_ac9_missing_toml_no_ok_reported(installed_workspace: Path) -> None:
    """Removing a TOML produces [missing] D-CX-1 and suppresses any [ok] for that agent.

    Given: all canonical agent TOMLs installed in .codex/agents/
    When:  qa-engineer.toml is deleted
    Then:
      - doctor() does NOT report '[ok] ... qa-engineer ... codex' (no false positive)
      - doctor() reports '[missing] codex:agents/qa-engineer.toml (D-CX-1)'
    """
    workspace_root = installed_workspace
    toml_path = workspace_root / ".codex" / "agents" / "qa-engineer.toml"
    assert toml_path.exists(), "Pre-condition failed: qa-engineer.toml must exist after install."

    toml_path.unlink()

    manager = FileSystemPublicAssetManager()
    reports = manager.doctor(workspace_root)

    # No [ok] report should reference qa-engineer in the codex agent context.
    ok_for_qa = [
        r for r in reports if r.startswith("[ok]") and "qa-engineer" in r and "codex" in r.lower()
    ]
    assert not ok_for_qa, (
        "qa-engineer should not appear as [ok] after its TOML was deleted. "
        f"Offending reports: {ok_for_qa}\nAll reports:\n" + "\n".join(reports)
    )

    # D-CX-1 must flag the missing TOML.
    dcx1_missing = [
        r for r in reports if r.startswith("[missing]") and "D-CX-1" in r and "qa-engineer" in r
    ]
    assert dcx1_missing, (
        "Expected '[missing] codex:agents/qa-engineer.toml (D-CX-1)' report. "
        "All reports:\n" + "\n".join(reports)
    )
