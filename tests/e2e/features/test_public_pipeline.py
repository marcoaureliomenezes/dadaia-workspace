"""E2E tests for the public asset pipeline: stage → .dadaia/agentic/ → runtime targets.

These tests use FileSystemPublicAssetManager with real I/O (tmp_path) to validate
the full pipeline: canonical source → staging → Claude / Codex / Pi / .agents.
They catch content-level bugs that unit tests with fakes cannot detect.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

# ---------------------------------------------------------------------------
# Canonical expectations — update when agents/skills are added or removed
# ---------------------------------------------------------------------------

EXPECTED_AGENTS = {
    "ai-engineer",
    "code-reviewer",
    "design-specialist",
    "devops-engineer",
    "frontend-engineer",
    "product-engineer",
    "project-auditor",
    "project-manager",
    "qa-engineer",
    "security-reviewer",
    "software-architect",
    "software-engineer",
}

# These must NEVER appear in any staging or runtime target
STALE_AGENTS = {
    "product-auditor-agent",
    "soft-engineer-agent",
    "architect-agent",
}

EXPECTED_SKILLS = {
    "ai-context-engineering",
    "ai-harness-claude-code",
    "ai-harness-codex",
    "architect-core-workflow",
    "dadaia-grill-me",
    "dadaia-handoff-emitter",
    "dadaia-release-closure",
    "dadaia-release-definition",
    "dadaia-step0-memory-bootstrap",
    "dadaia-task-manager",
    "dadaia-workspace-doctor",
    "dadaia-workspace-manager",
    "dadaia-workspace-spec-navigator",
    "dadaia-workspace-spec-reviewer",
    "dev-server-registry",
    "drift-detection",
    "harness-primitives",
    "project-orchestration",
}

# Required YAML fields in every agent's frontmatter
_REQUIRED_FRONTMATTER = {"name", "description", "model", "tools"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _manager() -> FileSystemPublicAssetManager:
    return FileSystemPublicAssetManager()


def _staged_agents(workspace: Path) -> set[str]:
    """Set of agent stem names found in .dadaia/agentic/agents/."""
    agents_dir = workspace / ".dadaia" / "agentic" / "agents"
    return {p.stem for p in agents_dir.glob("*.md")} if agents_dir.exists() else set()


def _runtime_agents(target_dir: Path) -> set[str]:
    """Set of agent stem names found in a runtime agents/ directory."""
    return {p.stem for p in target_dir.glob("*.md")} if target_dir.exists() else set()


def _parse_frontmatter_keys(content: str) -> set[str]:
    """Return top-level YAML key names found in frontmatter (between --- markers)."""
    if not content.startswith("---\n"):
        return set()
    end = content.find("\n---\n", 4)
    if end == -1:
        return set()
    frontmatter = content[4:end]
    return {m.group(1) for m in re.finditer(r"^(\w[\w-]*):", frontmatter, re.MULTILINE)}


def _parse_skills_list(content: str) -> list[str]:
    """Extract the `skills:` list values from agent frontmatter."""
    m = re.search(r"^skills:\n((?:  - [^\n]+\n)+)", content, re.MULTILINE)
    if not m:
        return []
    return [line.strip().lstrip("- ").strip() for line in m.group(1).splitlines() if line.strip()]


def _is_plugin_stub(content: str) -> bool:
    """Return True when the agent file is a plugin stub (has ``plugin: true`` in frontmatter).

    Plugin stubs declare a minimal frontmatter (name + description + plugin: true) and
    intentionally omit ``model``, ``tools``, and behavior body. They must not be tested
    for full-agent frontmatter completeness.
    """
    if not content.startswith("---\n"):
        return False
    end = content.find("\n---\n", 4)
    if end == -1:
        return False
    frontmatter = content[4:end]
    return bool(re.search(r"^plugin:\s*true\b", frontmatter, re.MULTILINE))


def _staged_install(workspace: Path) -> FileSystemPublicAssetManager:
    """Stage then install; return the manager for further assertions."""
    mgr = _manager()
    mgr.install(workspace, target="all", force=True)
    return mgr


# Synthetic workflow with parallel_group — decoupled from canonical workflow content.
# The filename stem must match the 'name' field exactly (MarkdownWorkflowStore validation).
_SYNTHETIC_PARALLEL_WORKFLOW_NAME = "synthetic-parallel"
_SYNTHETIC_PARALLEL_WORKFLOW_FILENAME = f"{_SYNTHETIC_PARALLEL_WORKFLOW_NAME}.workflow.md"
_SYNTHETIC_PARALLEL_WORKFLOW_CONTENT = """\
---
name: synthetic-parallel
description: Synthetic test fixture with a parallel_group stage for doctor classification tests.
version: 0.0.1
schema_version: "1"
stages:
  - id: review_a
    agent: qa-engineer
    parallel_group: review_batch
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-qa-engineer-review-a.handoff.json"
  - id: review_b
    agent: code-reviewer
    parallel_group: review_batch
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-code-reviewer-review-b.handoff.json"
  - id: finalize
    agent: project-manager
    needs: [review_a, review_b]
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-project-manager-finalize.handoff.json"
---

# synthetic-parallel

Synthetic fixture for test_public_pipeline.py — validates doctor [partial]/[reference-only]
classification when a workflow contains parallel_group stages.
"""


def _inject_synthetic_parallel_workflow(workspace: Path) -> None:
    """Write the synthetic parallel workflow into the staged area and all runtime targets.

    The doctor reads workflow classification from the staged area
    (``.dadaia/agentic/workflows/``). All runtime dirs must also contain the file so
    that D-CX-3 (codex drift check) does not produce a spurious [missing] report that
    would shadow the [partial]/[reference-only] lines under test.
    """
    content = _SYNTHETIC_PARALLEL_WORKFLOW_CONTENT
    filename = _SYNTHETIC_PARALLEL_WORKFLOW_FILENAME
    # Staged area (what _classify_workflows reads).
    staged_dir = workspace / ".dadaia" / "agentic" / "workflows"
    staged_dir.mkdir(parents=True, exist_ok=True)
    (staged_dir / filename).write_text(content, encoding="utf-8")
    # Runtime targets (needed to satisfy D-CX-3 codex mirror check).
    for runtime in (".agents", ".claude", ".codex"):
        rt_dir = workspace / runtime / "workflows"
        rt_dir.mkdir(parents=True, exist_ok=True)
        (rt_dir / filename).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# TestStage — validates .dadaia/agentic/ content after dadaia public stage
# ---------------------------------------------------------------------------


class TestStage:
    def test_stage_creates_all_expected_dirs(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _manager().stage(workspace)

        agentic = workspace / ".dadaia" / "agentic"
        for subdir in ("agents", "skills", "rules", "scripts", "data"):
            assert (agentic / subdir).is_dir(), f".dadaia/agentic/{subdir}/ not created by stage"

    def test_stage_manifest_schema_is_valid(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _manager().stage(workspace)

        manifest_path = workspace / ".dadaia" / "agentic" / "manifest.json"
        assert manifest_path.exists(), "manifest.json not created"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert manifest.get("schema_version") == "1", "schema_version must be '1'"
        assert "generated_at" in manifest, "manifest missing generated_at"
        assert "assets" in manifest, "manifest missing assets list"
        for asset in manifest["assets"]:
            assert "path" in asset, f"asset missing 'path': {asset}"
            assert "sha256" in asset, f"asset missing 'sha256': {asset}"
            assert "type" in asset, f"asset missing 'type': {asset}"

    def test_stage_manifest_lists_exactly_expected_agents(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _manager().stage(workspace)

        manifest = json.loads(
            (workspace / ".dadaia" / "agentic" / "manifest.json").read_text(encoding="utf-8")
        )
        staged = {
            Path(a["path"]).stem
            for a in manifest["assets"]
            if a["type"] == "agents" and a["path"].endswith(".md")
        }

        assert staged == EXPECTED_AGENTS, (
            f"Staged agents mismatch.\n  Expected: {sorted(EXPECTED_AGENTS)}\n  Got: {sorted(staged)}"
        )

    def test_stage_manifest_has_no_stale_agents(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _manager().stage(workspace)

        manifest = json.loads(
            (workspace / ".dadaia" / "agentic" / "manifest.json").read_text(encoding="utf-8")
        )
        all_paths = {a["path"] for a in manifest["assets"]}

        for stale in STALE_AGENTS:
            assert f"agents/{stale}.md" not in all_paths, (
                f"Stale agent '{stale}.md' found in manifest — must be deleted from canonical source"
            )

    def test_stage_creates_all_expected_skills(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _manager().stage(workspace)

        skills_dir = workspace / ".dadaia" / "agentic" / "skills"
        staged_skills = {p.name for p in skills_dir.iterdir() if p.is_dir()}

        assert staged_skills == EXPECTED_SKILLS, (
            f"Staged skills mismatch.\n"
            f"  Missing: {sorted(EXPECTED_SKILLS - staged_skills)}\n"
            f"  Extra:   {sorted(staged_skills - EXPECTED_SKILLS)}"
        )


# ---------------------------------------------------------------------------
# TestInstallAll — validates runtime targets after dadaia public install --target all
# ---------------------------------------------------------------------------


class TestInstallAll:
    def test_install_all_populates_claude_agents(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _staged_install(workspace)

        claude_agents = _runtime_agents(workspace / ".claude" / "agents")
        assert claude_agents == EXPECTED_AGENTS, (
            f".claude/agents/ mismatch.\n"
            f"  Missing: {sorted(EXPECTED_AGENTS - claude_agents)}\n"
            f"  Extra:   {sorted(claude_agents - EXPECTED_AGENTS)}"
        )

    def test_install_all_populates_universal_skills(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _staged_install(workspace)

        skills_dir = workspace / ".agents" / "skills"
        installed_skills = {p.name for p in skills_dir.iterdir() if p.is_dir()}

        assert installed_skills == EXPECTED_SKILLS, (
            f".agents/skills/ mismatch.\n"
            f"  Missing: {sorted(EXPECTED_SKILLS - installed_skills)}\n"
            f"  Extra:   {sorted(installed_skills - EXPECTED_SKILLS)}"
        )

    def test_install_all_creates_codex_config_files(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _staged_install(workspace)

        assert (workspace / ".codex" / "hooks.json").exists(), ".codex/hooks.json not created"
        assert (workspace / ".codex" / "config.toml").exists(), ".codex/config.toml not created"
        assert (workspace / ".codex" / "rules" / "dadaia-command-policy.rules").exists(), (
            ".codex/rules/dadaia-command-policy.rules not installed"
        )
        assert not (workspace / ".codex" / "rules" / "workspace-protocol.md").exists()

    def test_install_no_stale_agents_in_claude(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _staged_install(workspace)

        claude_agents = _runtime_agents(workspace / ".claude" / "agents")
        stale_found = claude_agents & STALE_AGENTS
        assert not stale_found, f"Stale agents found in .claude/agents/: {sorted(stale_found)}"


# ---------------------------------------------------------------------------
# TestContentConsistency — validates agent file content at staging and install time
# ---------------------------------------------------------------------------


class TestContentConsistency:
    def test_staged_agents_have_required_frontmatter(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _manager().stage(workspace)

        agents_dir = workspace / ".dadaia" / "agentic" / "agents"
        for agent_file in sorted(agents_dir.glob("*.md")):
            content = agent_file.read_text(encoding="utf-8")
            # Plugin stubs (plugin: true) intentionally omit model/tools — skip them.
            if _is_plugin_stub(content):
                continue
            keys = _parse_frontmatter_keys(content)
            missing = _REQUIRED_FRONTMATTER - keys
            assert not missing, (
                f"Agent '{agent_file.name}' is missing required frontmatter fields: {missing}"
            )

    def test_staged_agent_skill_references_are_all_valid(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _manager().stage(workspace)

        agents_dir = workspace / ".dadaia" / "agentic" / "agents"
        skills_dir = workspace / ".dadaia" / "agentic" / "skills"

        for agent_file in sorted(agents_dir.glob("*.md")):
            content = agent_file.read_text(encoding="utf-8")
            for skill in _parse_skills_list(content):
                skill_md = skills_dir / skill / "SKILL.md"
                assert skill_md.exists(), (
                    f"Agent '{agent_file.name}' references skill '{skill}' "
                    f"but '{skill_md.relative_to(workspace)}' does not exist"
                )

    def test_claude_agents_retain_tools_array(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _staged_install(workspace)

        agents_dir = workspace / ".claude" / "agents"
        for agent_file in sorted(agents_dir.glob("*.md")):
            content = agent_file.read_text(encoding="utf-8")
            # Plugin stubs (plugin: true) intentionally omit tools — skip them.
            if _is_plugin_stub(content):
                continue
            assert "tools:" in content, (
                f".claude/agents/{agent_file.name} is missing 'tools:' in frontmatter — "
                "Claude projection must retain it"
            )

    def test_all_skill_dirs_have_skill_md(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _manager().stage(workspace)

        skills_dir = workspace / ".dadaia" / "agentic" / "skills"
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.is_dir():
                assert (skill_dir / "SKILL.md").exists(), (
                    f"Skill directory '{skill_dir.name}' has no SKILL.md"
                )


# ---------------------------------------------------------------------------
# TestDoctor — validates drift/missing detection by the doctor command
# ---------------------------------------------------------------------------


class TestDoctor:
    def test_doctor_reports_all_ok_after_clean_install(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        mgr = _manager()
        mgr.install(workspace, target="all", force=True)

        report = mgr.doctor(workspace)

        failures = [line for line in report if line.startswith(("[drift]", "[missing]"))]
        assert not failures, "Doctor reported failures after clean install:\n" + "\n".join(failures)

    def test_doctor_detects_drift_after_runtime_modification(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        mgr = _manager()
        mgr.install(workspace, target="all", force=True)

        # Introduce drift in a Claude agent file
        target = workspace / ".claude" / "agents" / "software-engineer.md"
        target.write_text(target.read_text(encoding="utf-8") + "\n# drifted\n", encoding="utf-8")

        report = mgr.doctor(workspace)

        drift_lines = [line for line in report if "[drift]" in line and "software-engineer" in line]
        assert drift_lines, (
            "Doctor did not detect drift in .claude/agents/software-engineer.md.\n"
            "Full report:\n" + "\n".join(report)
        )

    def test_doctor_detects_missing_after_runtime_deletion(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        mgr = _manager()
        mgr.install(workspace, target="all", force=True)

        target = workspace / ".claude" / "agents" / "qa-engineer.md"
        target.unlink()

        report = mgr.doctor(workspace)

        missing_lines = [line for line in report if "[missing]" in line and "qa-engineer" in line]
        assert missing_lines, (
            "Doctor did not detect missing .claude/agents/qa-engineer.md.\n"
            "Full report:\n" + "\n".join(report)
        )


# ---------------------------------------------------------------------------
# TestWorkflows — validates the workflows/ asset type (multi-agent-orchestration)
# ---------------------------------------------------------------------------


EXPECTED_WORKFLOWS = {
    "audit-fanout",
    "release-ship",
}


class TestWorkflows:
    def test_stage_includes_all_workflow_files(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _manager().stage(workspace)
        workflows_dir = workspace / ".dadaia" / "agentic" / "workflows"
        assert workflows_dir.is_dir()
        staged = {p.stem.removesuffix(".workflow") for p in workflows_dir.glob("*.workflow.md")}
        assert staged == EXPECTED_WORKFLOWS

    def test_install_all_projects_workflows_to_every_runtime(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _staged_install(workspace)
        # Codex receives workflows as reference documents; it does not execute them.
        for runtime in (".agents", ".claude", ".codex"):
            for stem in EXPECTED_WORKFLOWS:
                projected = workspace / runtime / "workflows" / f"{stem}.workflow.md"
                assert projected.exists(), f"workflow not projected to {projected}"

    def test_doctor_reports_reference_only_for_codex_when_parallel_group(
        self, tmp_path: Path
    ) -> None:
        """Doctor emits [reference-only] for codex regardless of parallel_group.

        Same synthetic-parallel fixture as the [partial] test. Codex always gets
        [reference-only] for any workflow — it has no workflow executor.
        """
        workspace = tmp_path / "ws"
        _staged_install(workspace)

        # Inject a synthetic workflow with parallel_group into the staged area and all runtimes.
        _inject_synthetic_parallel_workflow(workspace)

        report = _manager().doctor(workspace)
        reference_lines = [
            line
            for line in report
            if line.startswith("[reference-only]") and "codex:workflows/synthetic-parallel" in line
        ]
        assert reference_lines, (
            "Doctor did not emit [reference-only] for codex:synthetic-parallel.\n"
            "Full report:\n" + "\n".join(report)
        )

    def test_doctor_reports_ok_for_serial_workflow(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _staged_install(workspace)
        report = _manager().doctor(workspace)
        # audit-fanout is a canonical serial workflow (no parallel_group) shipped by v0.1.9+.
        # claude should be [ok]; codex emits [reference-only].
        ok_lines = [
            line
            for line in report
            if line.startswith("[ok]") and "audit-fanout" in line and ":workflows/" in line
        ]
        assert any("claude" in line for line in ok_lines)
        # Codex check: [reference-only] because workflows are installed reference docs.
        ref_lines = [
            line
            for line in report
            if line.startswith("[reference-only]") and "codex:workflows/audit-fanout" in line
        ]
        assert ref_lines, "Doctor did not emit [reference-only] for codex:audit-fanout"

    def test_seed_workflows_pass_schema_validation(self, tmp_path: Path) -> None:
        """`dadaia public stage` aborts if any workflow fails schema validation."""
        workspace = tmp_path / "ws"
        # Should not raise — seed workflows are valid by contract.
        _manager().stage(workspace)
        # Re-staging idempotently must keep working.
        _manager().stage(workspace)
