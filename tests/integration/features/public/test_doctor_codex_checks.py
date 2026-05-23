"""Integration tests for doctor() Codex drift checks D-CX-1 through D-CX-5.

Covers acceptance criteria:
  - AC7: artificial removal of a workflow → doctor returns a [missing] report (D-CX-3)
  - AC8: corrupted developer_instructions in a TOML → doctor names the agent (D-CX-5)
  - AC9: missing TOML → doctor does not report [ok] for that agent; reports [missing] (D-CX-1)

Strategy
--------
Each test performs a full stage + install cycle into ``tmp_path`` using the real
``_public_dir`` (the package's own ``public/`` directory with all 20 canonical
agents and 7 canonical workflows).  After install, the test mutates the installed
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

    # Choose a workflow file that must exist after install.
    target_workflow = "cross-cutting-feature.workflow.md"
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
        r
        for r in reports
        if r.startswith("[missing]") and "D-CX-3" in r and "cross-cutting-feature" in r
    ]
    assert missing_dcx3, (
        "Expected at least one '[missing] ... D-CX-3 ... cross-cutting-feature' "
        "report but found none.\nAll reports:\n" + "\n".join(reports)
    )


def test_ac7_non_zero_exit_code_for_missing_workflow(installed_workspace: Path) -> None:
    """The presence of a [missing] D-CX-3 report implies a non-zero doctor exit.

    The CLI treats any report NOT starting with '[ok]' or '[skip]' as a failure.
    This test validates that invariant holds for the D-CX-3 missing-workflow case
    by checking that no [ok] report exists for the deleted workflow.
    """
    workspace_root = installed_workspace
    codex_workflows = workspace_root / ".codex" / "workflows"

    target_workflow = "hotfix-release.workflow.md"
    (codex_workflows / target_workflow).unlink()

    manager = FileSystemPublicAssetManager()
    reports = manager.doctor(workspace_root)

    # At least one non-ok/non-skip report must exist for a non-zero exit.
    non_ok = [r for r in reports if not r.startswith("[ok]") and not r.startswith("[skip]")]
    assert non_ok, (
        "Expected at least one non-ok/non-skip report after deleting a workflow. "
        "Reports:\n" + "\n".join(reports)
    )

    # Specifically the D-CX-3 check must flag the missing workflow.
    dcx3_missing = any("D-CX-3" in r and "hotfix-release" in r for r in reports)
    assert dcx3_missing, (
        "Expected a D-CX-3 missing report for 'hotfix-release.workflow.md'. "
        "Reports:\n" + "\n".join(reports)
    )


# ---------------------------------------------------------------------------
# AC8 — corrupted developer_instructions is detected by name (D-CX-5)
# ---------------------------------------------------------------------------


def test_ac8_corrupted_toml_detected(installed_workspace: Path) -> None:
    """Emptying developer_instructions in a TOML is caught as [error] D-CX-5 naming the agent.

    Given: a workspace with all 20 agent TOMLs installed in .codex/agents/
    When:  the developer_instructions field in researcher.toml is replaced with
           an empty string
    Then:  doctor() returns at least one report containing 'D-CX-5' and 'researcher'.
    """
    workspace_root = installed_workspace
    toml_path = workspace_root / ".codex" / "agents" / "researcher.toml"
    assert toml_path.exists(), (
        f"Pre-condition failed: researcher.toml must exist after install. "
        f"Files in .codex/agents/: {sorted(f.name for f in (workspace_root / '.codex' / 'agents').glob('*.toml'))}"
    )

    # Read and parse to confirm the field exists and is non-empty before corruption.
    original_text = toml_path.read_text(encoding="utf-8")
    original_data = tomllib.loads(original_text)
    assert original_data.get("developer_instructions", "").strip(), (
        "Pre-condition failed: researcher.toml should have non-empty developer_instructions before corruption."
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

    dcx5_researcher = [r for r in reports if "D-CX-5" in r and "researcher" in r]
    assert dcx5_researcher, (
        "Expected at least one D-CX-5 report naming 'researcher' after emptying "
        "developer_instructions.\nAll reports:\n" + "\n".join(reports)
    )


def test_ac8_error_report_not_ok_for_corrupted_agent(installed_workspace: Path) -> None:
    """A corrupted TOML must NOT produce an [ok] report for that agent.

    This complements AC8 by verifying the absence of a false-positive [ok] label
    for the corrupted agent, confirming doctor cannot be fooled into reporting
    health while the invariant is violated.
    """
    workspace_root = installed_workspace
    agent_name = "qa-engineer"
    toml_path = workspace_root / ".codex" / "agents" / f"{agent_name}.toml"
    assert toml_path.exists(), f"Pre-condition: {agent_name}.toml must exist after install."

    original_text = toml_path.read_text(encoding="utf-8")
    corrupted = re.sub(
        r'developer_instructions\s*=\s*""".*?"""',
        'developer_instructions = """"""',
        original_text,
        flags=re.DOTALL,
    )
    toml_path.write_text(corrupted, encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    reports = manager.doctor(workspace_root)

    # The corrupted agent must not appear as [ok] for D-CX-5.
    ok_dcx5_for_agent = [
        r for r in reports if r.startswith("[ok]") and agent_name in r and "D-CX-5" in r
    ]
    assert not ok_dcx5_for_agent, (
        f"Corrupted {agent_name}.toml must not produce an [ok] D-CX-5 report. "
        f"Reports:\n" + "\n".join(reports)
    )

    # D-CX-5 error must be present.
    assert any("D-CX-5" in r and agent_name in r for r in reports), (
        f"Expected D-CX-5 report naming '{agent_name}'. Reports:\n" + "\n".join(reports)
    )


# ---------------------------------------------------------------------------
# AC9 — missing TOML is not reported as [ok] and is reported as [missing] (D-CX-1)
# ---------------------------------------------------------------------------


def test_ac9_missing_toml_no_ok_reported(installed_workspace: Path) -> None:
    """Removing a TOML produces [missing] D-CX-1 and suppresses any [ok] for that agent.

    Given: all 20 agent TOMLs installed in .codex/agents/
    When:  researcher.toml is deleted
    Then:
      - doctor() does NOT report '[ok] ... researcher ... codex' (no false positive)
      - doctor() reports '[missing] codex:agents/researcher.toml (D-CX-1)'
    """
    workspace_root = installed_workspace
    toml_path = workspace_root / ".codex" / "agents" / "researcher.toml"
    assert toml_path.exists(), "Pre-condition failed: researcher.toml must exist after install."

    toml_path.unlink()

    manager = FileSystemPublicAssetManager()
    reports = manager.doctor(workspace_root)

    # No [ok] report should reference researcher in the codex agent context.
    ok_for_researcher = [
        r for r in reports if r.startswith("[ok]") and "researcher" in r and "codex" in r.lower()
    ]
    assert not ok_for_researcher, (
        "researcher should not appear as [ok] after its TOML was deleted. "
        f"Offending reports: {ok_for_researcher}\nAll reports:\n" + "\n".join(reports)
    )

    # D-CX-1 must flag the missing TOML.
    dcx1_missing = [
        r for r in reports if r.startswith("[missing]") and "D-CX-1" in r and "researcher" in r
    ]
    assert dcx1_missing, (
        "Expected '[missing] codex:agents/researcher.toml (D-CX-1)' report. "
        "All reports:\n" + "\n".join(reports)
    )


def test_ac9_missing_toml_for_second_agent(installed_workspace: Path) -> None:
    """D-CX-1 triggers for any removed TOML, not just researcher.

    Verifies that the check is not agent-specific by removing a different agent's TOML
    (backend-engineer) and confirming the same invariant holds.
    """
    workspace_root = installed_workspace
    agent_name = "backend-engineer"
    toml_path = workspace_root / ".codex" / "agents" / f"{agent_name}.toml"
    assert toml_path.exists(), f"Pre-condition failed: {agent_name}.toml must exist after install."

    toml_path.unlink()

    manager = FileSystemPublicAssetManager()
    reports = manager.doctor(workspace_root)

    # Must not be [ok].
    ok_for_agent = [
        r for r in reports if r.startswith("[ok]") and agent_name in r and "codex" in r.lower()
    ]
    assert not ok_for_agent, (
        f"{agent_name} must not appear as [ok] after its TOML was deleted. "
        f"Offending: {ok_for_agent}"
    )

    # Must be reported as [missing] with D-CX-1.
    assert any("D-CX-1" in r and agent_name in r for r in reports), (
        f"Expected D-CX-1 [missing] report for '{agent_name}'. Reports:\n" + "\n".join(reports)
    )
