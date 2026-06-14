"""Integration tests for doctor() Codex drift checks D-CX-1 through D-CX-10.

Covers acceptance criteria:
  - D-CX-1: missing TOML is reported as [missing] and not [ok]
  - D-CX-3: artificial removal of a workflow is reported as [missing]
  - D-CX-5: corrupted developer_instructions in a TOML reports the agent
  - D-CX-7/D-CX-8/D-CX-9/D-CX-10: semantic Codex projection drift is caught

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
import sys
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
    venv_bin = tmp_path / ".dadaia" / ".venv" / "bin"
    venv_bin.mkdir(parents=True, exist_ok=True)
    (venv_bin / "python").symlink_to(Path(sys.executable))
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


def test_dcx4_allows_claude_code_skill_but_rejects_model_ids(installed_workspace: Path) -> None:
    toml_path = installed_workspace / ".codex" / "agents" / "ai-engineer.toml"
    text = toml_path.read_text(encoding="utf-8")
    assert "ai-harness-claude-code" in text
    assert "ai-harness-gpt" not in text

    reports = FileSystemPublicAssetManager().doctor(installed_workspace)
    assert not any("D-CX-4" in r and "ai-harness-claude-code" in r for r in reports)

    toml_path.write_text(text + "\nClaude model leak: claude-opus-4-7\n", encoding="utf-8")
    drift_reports = FileSystemPublicAssetManager().doctor(installed_workspace)

    assert any("D-CX-4" in r and "ai-engineer.toml" in r for r in drift_reports)


def test_dcx7_missing_codex_skill_reference_detected(installed_workspace: Path) -> None:
    toml_path = installed_workspace / ".codex" / "agents" / "ai-engineer.toml"
    original = toml_path.read_text(encoding="utf-8")
    toml_path.write_text(
        original.replace("`ai-harness-claude-code`", "`ai-harness-gpt-5.3-codex`", 1),
        encoding="utf-8",
    )

    reports = FileSystemPublicAssetManager().doctor(installed_workspace)

    assert any("D-CX-7" in r and "ai-harness-gpt-5.3-codex" in r for r in reports)


def test_dcx8_markdown_rules_rejected(installed_workspace: Path) -> None:
    rules_dir = installed_workspace / ".codex" / "rules"
    assert (rules_dir / "dadaia-command-policy.rules").exists()

    (rules_dir / "workspace-protocol.md").write_text("# not executable\n", encoding="utf-8")

    reports = FileSystemPublicAssetManager().doctor(installed_workspace)

    assert any("D-CX-8" in r and "workspace-protocol.md" in r for r in reports)


def test_dcx8_undocumented_command_allowed_rejected(installed_workspace: Path) -> None:
    rules_path = installed_workspace / ".codex" / "rules" / "dadaia-command-policy.rules"
    rules_path.write_text(
        "def command_allowed(cmd):\n    return True\n",
        encoding="utf-8",
    )

    reports = FileSystemPublicAssetManager().doctor(installed_workspace)

    assert any("D-CX-8" in r and "command_allowed" in r for r in reports)
    assert any("D-CX-8" in r and "missing prefix_rule" in r for r in reports)


def test_dcx9_missing_hook_command_detected(installed_workspace: Path) -> None:
    # Codex hooks invoke direct-exec wrapper paths, not shell command strings. Strip one
    # wrapper command and assert D-CX-9 catches the missing executable wiring.
    hooks_path = installed_workspace / ".codex" / "hooks.json"
    text = hooks_path.read_text(encoding="utf-8")
    assert ".dadaia/hooks/codex-ctx-inject" in text
    hooks_path.write_text(
        text.replace(".dadaia/hooks/codex-ctx-inject", ".dadaia/hooks/DELETED"),
        encoding="utf-8",
    )

    reports = FileSystemPublicAssetManager().doctor(installed_workspace)

    assert any("D-CX-9" in r and ".dadaia/hooks/codex-ctx-inject" in r for r in reports)


def test_dcx9_non_executable_wrapper_detected(installed_workspace: Path) -> None:
    wrapper = installed_workspace / ".dadaia" / "hooks" / "codex-pre-gate"
    assert wrapper.exists()
    wrapper.chmod(0o644)

    reports = FileSystemPublicAssetManager().doctor(installed_workspace)

    assert any("D-CX-9" in r and "not executable" in r and "codex-pre-gate" in r for r in reports)


def test_dcx9_shell_command_string_detected(installed_workspace: Path) -> None:
    hooks_path = installed_workspace / ".codex" / "hooks.json"
    text = hooks_path.read_text(encoding="utf-8")
    hooks_path.write_text(
        text.replace(
            ".dadaia/hooks/codex-pre-gate",
            "/tmp/workspace/.dadaia/.venv/bin/python -m dadaia_workspace.hooks.pre_gate",
        ),
        encoding="utf-8",
    )

    reports = FileSystemPublicAssetManager().doctor(installed_workspace)

    assert any("D-CX-9" in r and "must use .dadaia/hooks wrapper" in r for r in reports)


def test_dcx10_missing_agent_boundary_detected(installed_workspace: Path) -> None:
    toml_path = installed_workspace / ".codex" / "agents" / "qa-engineer.toml"
    text = toml_path.read_text(encoding="utf-8")
    toml_path.write_text(
        re.sub(r"^sandbox_mode = .+\n", "", text, flags=re.MULTILINE),
        encoding="utf-8",
    )

    reports = FileSystemPublicAssetManager().doctor(installed_workspace)

    assert any("D-CX-10" in r and "qa-engineer.toml" in r and "sandbox_mode" in r for r in reports)


def test_dcx10_reviewer_workspace_write_detected(installed_workspace: Path) -> None:
    toml_path = installed_workspace / ".codex" / "agents" / "security-reviewer.toml"
    text = toml_path.read_text(encoding="utf-8")
    assert 'sandbox_mode = "read-only"' in text
    toml_path.write_text(
        text.replace('sandbox_mode = "read-only"', 'sandbox_mode = "workspace-write"', 1),
        encoding="utf-8",
    )

    reports = FileSystemPublicAssetManager().doctor(installed_workspace)

    assert any(
        "D-CX-10" in r and "security-reviewer.toml" in r and "must be read-only" in r
        for r in reports
    )


def test_check_memory_phase_single_source(tmp_path) -> None:
    """SINGLE-SRC-1 lint (rc-4 / T-017-31): flags a CLOSURE-only memory-write phase claim,
    accepts DEFINITION+CLOSURE, ignores incidental 'release closure' + memory mentions."""
    from dadaia_workspace.infrastructure.codex_doctor import check_memory_phase_single_source

    pub = tmp_path / "public"
    (pub / "agents").mkdir(parents=True)
    (pub / "skills" / "s1").mkdir(parents=True)
    (pub / "agents" / "bad.md").write_text(
        "---\nname: bad\n---\nMemory atoms are write-locked except product-engineer "
        "during the CLOSURE phase.\n",
        encoding="utf-8",
    )
    (pub / "agents" / "good.md").write_text(
        "---\nname: good\n---\nMemory is write-locked except product-engineer in the "
        "DEFINITION and CLOSURE phases.\n",
        encoding="utf-8",
    )
    (pub / "skills" / "s1" / "SKILL.md").write_text(
        "---\nname: s1\n---\nAt release closure, update memory and write CLOSURE.md.\n",
        encoding="utf-8",
    )
    out = check_memory_phase_single_source(pub)
    assert any("bad.md" in line and "SINGLE-SRC-1" in line for line in out), out
    assert not any("good.md" in line for line in out), out
    assert not any("SKILL.md" in line for line in out), out


# ---------------------------------------------------------------------------
# T-013-09 — description field runs through transform_for_codex; D-CX-4 flags
# Claude tool names (codex-agent-description-claude-ism-leak)
# ---------------------------------------------------------------------------


def test_description_field_transformed_through_codex_replacements(
    installed_workspace: Path,
) -> None:
    """The agent TOML description must be run through transform_for_codex.

    project-manager's source description says "dispatches sub-agents via Agent tool".
    After install, the rendered TOML description must carry no Claude tool-name
    Claude-ism — the "Agent tool" phrase must be replaced.
    """
    toml_path = installed_workspace / ".codex" / "agents" / "project-manager.toml"
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    description = data.get("description", "")
    assert description, "project-manager.toml must carry a description"
    assert "Agent tool" not in description, (
        "Description must be transformed; 'Agent tool' Claude-ism leaked: " + description
    )
    assert "explicit Codex subagent delegation" in description


def test_dcx4_flags_claude_tool_name_in_artifact(installed_workspace: Path) -> None:
    """D-CX-4 must flag a Codex artifact that contains a Claude tool-name pattern."""
    toml_path = installed_workspace / ".codex" / "agents" / "ai-engineer.toml"
    text = toml_path.read_text(encoding="utf-8")
    # Clean artifact: no tool-name leak reported.
    clean = FileSystemPublicAssetManager().doctor(installed_workspace)
    assert not any("D-CX-4" in r and "claude-tool-name" in r for r in clean)

    toml_path.write_text(text + '\ndescription = "delegate via Agent tool"\n', encoding="utf-8")
    reports = FileSystemPublicAssetManager().doctor(installed_workspace)
    assert any(
        "D-CX-4" in r and "claude-tool-name" in r and "ai-engineer.toml" in r for r in reports
    ), reports


# ---------------------------------------------------------------------------
# T-013-11 — canonical `software-engineer` is the constitution §14 implementer;
# the stale T-35 roster lint that flagged it is deleted. A public asset
# referencing `subagent_type: software-engineer` must produce NO doctor error
# (regression for bug stale-legacy-software-engineer-lint-inverts-roster).
# ---------------------------------------------------------------------------


def test_canonical_software_engineer_subagent_type_produces_no_doctor_error(
    installed_workspace: Path,
) -> None:
    """`subagent_type: software-engineer` is canonical and must not be flagged.

    The deleted ``lint_legacy_software_engineer`` used to emit a ``[LINT]`` report
    for this exact string. After T-013-11 the canonical implementer name is the
    constitution §14 roster member, so doctor() must return zero error/lint reports
    referencing it for that reason.
    """
    workspace_root = installed_workspace
    codex_agents = workspace_root / ".codex" / "agents"
    canonical = codex_agents / "project-manager.toml"
    assert canonical.exists(), "Pre-condition: project-manager.toml must exist after install."

    # Inject the canonical implementer reference into an installed Codex artifact.
    text = canonical.read_text(encoding="utf-8")
    canonical.write_text(
        text + "\n# dispatch note: subagent_type: software-engineer\n",
        encoding="utf-8",
    )

    reports = FileSystemPublicAssetManager().doctor(workspace_root)

    offending = [
        r
        for r in reports
        if "software-engineer" in r and (r.startswith("[error]") or "[LINT]" in r)
    ]
    assert not offending, (
        "Canonical 'software-engineer' must not produce any error/lint report.\n"
        "Offending reports:\n" + "\n".join(offending)
    )
