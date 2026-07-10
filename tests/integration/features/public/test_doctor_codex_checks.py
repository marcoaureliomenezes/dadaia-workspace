"""Integration tests for doctor() Codex drift checks D-CX-1 through D-CX-10.

Merged per plan-integration.md (16 -> 4), riding the shared session-scoped
``installed_codex_workspace`` fixture (tests/integration/conftest.py) — one full
stage+install(target=codex) per session, per-test ``shutil.copytree`` instead of a
fresh install per test:

  1. missing/corrupt table: D-CX-1 (toml gone, no false [ok]) + D-CX-3 (workflow gone) +
     D-CX-5 (emptied instructions)
  2. Claude-ism/skill-ref: D-CX-4 model-id + tool-name + description transform +
     canonical software-engineer no-lint
  3. rules/hooks: D-CX-7 missing skill + D-CX-8 md-rule + undocumented command +
     D-CX-9 missing/non-exec/shell-string wrappers
  4. D-CX-10 sandbox pair + SINGLE-SRC-1 memory-phase lint

Strategy (unchanged): mutate the installed ``.codex/`` artifacts and re-run
``doctor(workspace_root)`` to confirm drift is caught, using the real public assets and
TOML generation pipeline rather than synthetic fixtures.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def test_missing_and_corrupt_table_dcx1_dcx3_dcx5(installed_codex_workspace: Path) -> None:
    """D-CX-1 missing TOML (no false [ok]) + D-CX-3 missing workflow + D-CX-5 corrupted
    developer_instructions — each caught by name."""
    workspace_root = installed_codex_workspace

    # D-CX-3 — a canonical workflow removed from .codex/workflows/.
    codex_workflows = workspace_root / ".codex" / "workflows"
    target_workflow = "release-ship.workflow.md"
    workflow_path = codex_workflows / target_workflow
    assert workflow_path.exists(), (
        f"Pre-condition failed: expected {target_workflow} to exist after install. "
        f"Files present: {sorted(f.name for f in codex_workflows.glob('*.workflow.md'))}"
    )
    workflow_path.unlink()

    # D-CX-5 — developer_instructions emptied in qa-engineer.toml.
    toml_path = workspace_root / ".codex" / "agents" / "qa-engineer.toml"
    original_text = toml_path.read_text(encoding="utf-8")
    original_data = tomllib.loads(original_text)
    assert original_data.get("developer_instructions", "").strip(), (
        "Pre-condition failed: qa-engineer.toml should have non-empty developer_instructions."
    )
    corrupted = re.sub(
        r'developer_instructions\s*=\s*""".*?"""',
        'developer_instructions = """"""',
        original_text,
        flags=re.DOTALL,
    )
    toml_path.write_text(corrupted, encoding="utf-8")

    # D-CX-1 — a TOML deleted entirely.
    (workspace_root / ".codex" / "agents" / "ai-engineer.toml").unlink()

    reports = FileSystemPublicAssetManager().doctor(workspace_root)

    missing_dcx3 = [
        r for r in reports if r.startswith("[missing]") and "D-CX-3" in r and "release-ship" in r
    ]
    assert missing_dcx3, "Expected [missing] ... D-CX-3 ... release-ship.\n" + "\n".join(reports)

    dcx5_qa = [r for r in reports if "D-CX-5" in r and "qa-engineer" in r]
    assert dcx5_qa, "Expected D-CX-5 naming 'qa-engineer'.\n" + "\n".join(reports)

    ok_for_ai = [
        r for r in reports if r.startswith("[ok]") and "ai-engineer" in r and "codex" in r.lower()
    ]
    assert not ok_for_ai, f"ai-engineer should not appear as [ok] after deletion: {ok_for_ai}"
    dcx1_missing = [
        r for r in reports if r.startswith("[missing]") and "D-CX-1" in r and "ai-engineer" in r
    ]
    assert dcx1_missing, "Expected [missing] codex:agents/ai-engineer.toml (D-CX-1).\n" + "\n".join(
        reports
    )


def test_claude_ism_and_skill_ref_dcx4(installed_codex_workspace: Path) -> None:
    """D-CX-4 model-id + tool-name leak + description transform; canonical no-lint."""
    workspace_root = installed_codex_workspace
    toml_path = workspace_root / ".codex" / "agents" / "ai-engineer.toml"
    text = toml_path.read_text(encoding="utf-8")
    assert "ai-harness-claude-code" in text
    assert "ai-harness-gpt" not in text

    clean = FileSystemPublicAssetManager().doctor(workspace_root)
    assert not any("D-CX-4" in r and "ai-harness-claude-code" in r for r in clean)
    assert not any("D-CX-4" in r and "claude-tool-name" in r for r in clean)

    # Model-id leak.
    toml_path.write_text(text + "\nClaude model leak: claude-opus-4-7\n", encoding="utf-8")
    drift_reports = FileSystemPublicAssetManager().doctor(workspace_root)
    assert any("D-CX-4" in r and "ai-engineer.toml" in r for r in drift_reports)

    # Tool-name leak (independent mutation, restored to the clean baseline first).
    toml_path.write_text(text, encoding="utf-8")
    toml_path.write_text(text + '\ndescription = "delegate via Agent tool"\n', encoding="utf-8")
    tool_name_reports = FileSystemPublicAssetManager().doctor(workspace_root)
    assert any(
        "D-CX-4" in r and "claude-tool-name" in r and "ai-engineer.toml" in r
        for r in tool_name_reports
    ), tool_name_reports

    # Restore the clean baseline before the remaining assertions in this fn.
    toml_path.write_text(text, encoding="utf-8")

    # T-013-09 — description runs through transform_for_codex (Claude-ism removed).
    pm_toml = workspace_root / ".codex" / "agents" / "project-manager.toml"
    data = tomllib.loads(pm_toml.read_text(encoding="utf-8"))
    description = data.get("description", "")
    assert description, "project-manager.toml must carry a description"
    assert "Agent tool" not in description
    assert "explicit Codex subagent delegation" in description

    # T-013-11 — canonical `software-engineer` reference produces no doctor error/lint.
    canonical = workspace_root / ".codex" / "agents" / "project-manager.toml"
    canonical.write_text(
        canonical.read_text(encoding="utf-8")
        + "\n# dispatch note: subagent_type: software-engineer\n",
        encoding="utf-8",
    )
    reports = FileSystemPublicAssetManager().doctor(workspace_root)
    offending = [
        r
        for r in reports
        if "software-engineer" in r and (r.startswith("[error]") or "[LINT]" in r)
    ]
    assert not offending, (
        "Canonical 'software-engineer' must not produce error/lint.\n" + "\n".join(offending)
    )


def test_rules_and_hooks_dcx7_dcx8_dcx9(installed_codex_workspace: Path) -> None:
    """D-CX-7 missing skill reference; D-CX-8 markdown rule + undocumented command;
    D-CX-9 missing/non-executable/shell-string hook wrappers."""
    workspace_root = installed_codex_workspace

    # D-CX-7 — a documented skill reference swapped for a nonexistent one.
    ai_toml = workspace_root / ".codex" / "agents" / "ai-engineer.toml"
    original = ai_toml.read_text(encoding="utf-8")
    ai_toml.write_text(
        original.replace("`ai-harness-claude-code`", "`ai-harness-gpt-5.3-codex`", 1),
        encoding="utf-8",
    )
    reports = FileSystemPublicAssetManager().doctor(workspace_root)
    assert any("D-CX-7" in r and "ai-harness-gpt-5.3-codex" in r for r in reports)

    # D-CX-8 — a markdown rule file is not executable; an undocumented allow fn is rejected.
    rules_dir = workspace_root / ".codex" / "rules"
    assert (rules_dir / "dadaia-command-policy.rules").exists()
    (rules_dir / "workspace-protocol.md").write_text("# not executable\n", encoding="utf-8")
    reports = FileSystemPublicAssetManager().doctor(workspace_root)
    assert any("D-CX-8" in r and "workspace-protocol.md" in r for r in reports)

    rules_path = rules_dir / "dadaia-command-policy.rules"
    rules_path.write_text(
        "def command_allowed(cmd):\n    return True\n",
        encoding="utf-8",
    )
    reports = FileSystemPublicAssetManager().doctor(workspace_root)
    assert any("D-CX-8" in r and "command_allowed" in r for r in reports)
    assert any("D-CX-8" in r and "missing prefix_rule" in r for r in reports)

    # D-CX-9 — missing hook command wrapper path.
    hooks_path = workspace_root / ".codex" / "hooks.json"
    text = hooks_path.read_text(encoding="utf-8")
    assert ".dadaia/hooks/codex-ctx-inject" in text
    hooks_path.write_text(
        text.replace(".dadaia/hooks/codex-ctx-inject", ".dadaia/hooks/DELETED"),
        encoding="utf-8",
    )
    reports = FileSystemPublicAssetManager().doctor(workspace_root)
    assert any("D-CX-9" in r and ".dadaia/hooks/codex-ctx-inject" in r for r in reports)

    # D-CX-9 — non-executable wrapper.
    wrapper = workspace_root / ".dadaia" / "hooks" / "codex-pre-gate"
    assert wrapper.exists()
    wrapper.chmod(0o644)
    reports = FileSystemPublicAssetManager().doctor(workspace_root)
    assert any("D-CX-9" in r and "not executable" in r and "codex-pre-gate" in r for r in reports)

    # D-CX-9 — shell command string instead of the direct-exec wrapper path.
    hooks_path2 = workspace_root / ".codex" / "hooks.json"
    text2 = hooks_path2.read_text(encoding="utf-8")
    hooks_path2.write_text(
        text2.replace(
            ".dadaia/hooks/codex-pre-gate",
            "/tmp/workspace/.dadaia/.venv/bin/python -m dadaia_workspace.hooks.pre_gate",
        ),
        encoding="utf-8",
    )
    reports = FileSystemPublicAssetManager().doctor(workspace_root)
    assert any("D-CX-9" in r and "must use .dadaia/hooks wrapper" in r for r in reports)


def test_dcx10_sandbox_pair_and_single_src1_memory_phase_lint(
    installed_codex_workspace: Path, tmp_path: Path
) -> None:
    """D-CX-10: missing sandbox_mode + reviewer workspace-write both flagged by name.
    SINGLE-SRC-1: memory-phase-claim lint flags a CLOSURE-only claim, accepts
    DEFINITION+CLOSURE, ignores incidental mentions."""
    workspace_root = installed_codex_workspace

    toml_path = workspace_root / ".codex" / "agents" / "qa-engineer.toml"
    text = toml_path.read_text(encoding="utf-8")
    toml_path.write_text(
        re.sub(r"^sandbox_mode = .+\n", "", text, flags=re.MULTILINE),
        encoding="utf-8",
    )
    reports = FileSystemPublicAssetManager().doctor(workspace_root)
    assert any("D-CX-10" in r and "qa-engineer.toml" in r and "sandbox_mode" in r for r in reports)

    sec_toml = workspace_root / ".codex" / "agents" / "security-reviewer.toml"
    sec_text = sec_toml.read_text(encoding="utf-8")
    assert 'sandbox_mode = "read-only"' in sec_text
    sec_toml.write_text(
        sec_text.replace('sandbox_mode = "read-only"', 'sandbox_mode = "workspace-write"', 1),
        encoding="utf-8",
    )
    reports = FileSystemPublicAssetManager().doctor(workspace_root)
    assert any(
        "D-CX-10" in r and "security-reviewer.toml" in r and "must be read-only" in r
        for r in reports
    )

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
