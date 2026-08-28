"""E2E tests for the public asset pipeline: stage → .dadaia/agentic/ → runtime targets.

These tests use FileSystemPublicAssetManager with real I/O (tmp_path) to validate
the full pipeline: canonical source → staging → Claude / Codex / Pi / .agents.
They catch content-level bugs that unit tests with fakes cannot detect.

Intent: CONTRACT — v0.1.65 FR1/AC-1, FR5/AC-8 (public asset pipeline)
Owner: software-engineer
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app as cli_app
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.scan_population import assert_populated
from tests.helpers.skill_inventory_oracle import skill_names

# NEVER pass mix_stderr (removed in Click 8.2; the installed 8.4.1 TypeErrors on it) —
# QA-atom law (v0.1.57). stdout/stderr are read as separate channels.
_runner = CliRunner()

# ---------------------------------------------------------------------------
# Canonical expectations — update when agents/skills are added or removed
# ---------------------------------------------------------------------------

EXPECTED_AGENTS = {
    "ai-engineer",
    "code-reviewer",
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

# The skill roster is NOT hand-kept here (v0.4.5 FR4, coupled-inventory-shared-oracle):
# it is derived at assertion time by tests.helpers.skill_inventory_oracle.skill_names(),
# the one oracle every skill-roster consumer in this repo now reads.

# Required YAML fields in every STAGED agent's frontmatter. v0.1.65 FR1: staged core
# bodies are model-agnostic (`model:`/`effort:` are injected at install-time by the
# render seam from the resolved policy), so `model` is no longer required at staging —
# the AC-1 half is asserted alongside in test_staged_agents_have_required_frontmatter.
_REQUIRED_FRONTMATTER = {"name", "description", "tools"}

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


# ---------------------------------------------------------------------------
# TestStage — validates .dadaia/agentic/ content after dadaia public stage
# ---------------------------------------------------------------------------


class TestStage:
    def test_stage_dirs_manifest_agents_and_skills(self, tmp_path: Path) -> None:
        """One staged workspace, every stage-time invariant: dirs+manifest schema+
        exact agent roster (no stale)+skill roster, in a single check pass."""
        workspace = tmp_path / "ws"
        _manager().stage(workspace)

        agentic = workspace / ".dadaia" / "agentic"
        # ``rules`` is NOT staged: the nine core rules were consolidated into the single
        # always-on law file (``data/DADAIA.md``), so the family no longer exists as a
        # core asset dir. Plugin-pack rules stage under ``plugins/<pack>/rules/``.
        for subdir in ("agents", "skills", "scripts", "data"):
            assert (agentic / subdir).is_dir(), f".dadaia/agentic/{subdir}/ not created by stage"
        assert (agentic / "data" / "DADAIA.md").is_file(), "the workspace law file is not staged"

        manifest_path = agentic / "manifest.json"
        assert manifest_path.exists(), "manifest.json not created"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert manifest.get("schema_version") == "1", "schema_version must be '1'"
        assert "generated_at" in manifest, "manifest missing generated_at"
        assert "assets" in manifest, "manifest missing assets list"
        for asset in manifest["assets"]:
            assert "path" in asset, f"asset missing 'path': {asset}"
            assert "sha256" in asset, f"asset missing 'sha256': {asset}"
            assert "type" in asset, f"asset missing 'type': {asset}"

        staged = {
            Path(a["path"]).stem
            for a in manifest["assets"]
            if a["type"] == "agents" and a["path"].endswith(".md")
        }
        assert staged == EXPECTED_AGENTS, (
            f"Staged agents mismatch.\n  Expected: {sorted(EXPECTED_AGENTS)}\n  Got: {sorted(staged)}"
        )

        all_paths = {a["path"] for a in manifest["assets"]}
        for stale in STALE_AGENTS:
            assert f"agents/{stale}.md" not in all_paths, (
                f"Stale agent '{stale}.md' found in manifest — must be deleted from canonical source"
            )

        skills_dir = agentic / "skills"
        staged_skills = {p.name for p in skills_dir.iterdir() if p.is_dir()}
        expected_skills = skill_names()
        # v0.4.5 FR5 (scan-test-vacuity-guard): a mis-rooted oracle scan would degrade
        # `expected_skills` to empty, mirroring the same systemic-mis-root risk a
        # simultaneously-empty `staged_skills` (derived from the SAME production
        # public_dir) would leave uncaught.
        assert_populated(expected_skills, sentinel="dd-cli-library")
        assert staged_skills == expected_skills, (
            f"Staged skills mismatch.\n"
            f"  Missing: {sorted(expected_skills - staged_skills)}\n"
            f"  Extra:   {sorted(staged_skills - expected_skills)}"
        )


# ---------------------------------------------------------------------------
# TestInstallAll — validates runtime targets after dadaia public install --target all
# ---------------------------------------------------------------------------


class TestInstallAll:
    def test_install_all_populates_claude_agents_skills_no_stale(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        _staged_install(workspace)

        claude_agents = _runtime_agents(workspace / ".claude" / "agents")
        assert claude_agents == EXPECTED_AGENTS, (
            f".claude/agents/ mismatch.\n"
            f"  Missing: {sorted(EXPECTED_AGENTS - claude_agents)}\n"
            f"  Extra:   {sorted(claude_agents - EXPECTED_AGENTS)}"
        )
        stale_found = claude_agents & STALE_AGENTS
        assert not stale_found, f"Stale agents found in .claude/agents/: {sorted(stale_found)}"

        skills_dir = workspace / ".agents" / "skills"
        installed_skills = {p.name for p in skills_dir.iterdir() if p.is_dir()}
        expected_skills = skill_names()
        # v0.4.5 FR5 (scan-test-vacuity-guard): same reasoning as TestStage above.
        assert_populated(expected_skills, sentinel="dd-cli-library")
        assert installed_skills == expected_skills, (
            f".agents/skills/ mismatch.\n"
            f"  Missing: {sorted(expected_skills - installed_skills)}\n"
            f"  Extra:   {sorted(installed_skills - expected_skills)}"
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


# ---------------------------------------------------------------------------
# TestContentConsistency — validates agent file content at staging and install time
# ---------------------------------------------------------------------------


class TestContentConsistency:
    def test_agent_frontmatter_skill_refs_tools_and_skill_md_presence(self, tmp_path: Path) -> None:
        """One staged + installed workspace, every content-consistency invariant in a
        single pass: staged agent frontmatter (required fields present, model/effort
        absent — FR1), staged agent skill references all resolve to a real skill,
        installed Claude agents retain `tools:`, and every staged skill dir has a
        SKILL.md. Also folds the retired `us7_skill_file_exists` content asserts
        (`dadaia server list/next/register/release` mentioned in the dev-server-registry
        skill) since skill presence is already pinned by the one derived skill-inventory
        oracle (`tests.helpers.skill_inventory_oracle.skill_names`)."""
        workspace = tmp_path / "ws"
        _staged_install(workspace)

        agents_dir = workspace / ".dadaia" / "agentic" / "agents"
        skills_dir = workspace / ".dadaia" / "agentic" / "skills"
        for agent_file in sorted(agents_dir.glob("*.md")):
            content = agent_file.read_text(encoding="utf-8")
            # Plugin stubs (plugin: true) intentionally omit model/tools — skip them.
            if _is_plugin_stub(content):
                for skill in _parse_skills_list(content):
                    skill_md = skills_dir / skill / "SKILL.md"
                    assert skill_md.exists(), (
                        f"Agent '{agent_file.name}' references skill '{skill}' "
                        f"but '{skill_md.relative_to(workspace)}' does not exist"
                    )
                continue
            keys = _parse_frontmatter_keys(content)
            missing = _REQUIRED_FRONTMATTER - keys
            assert not missing, (
                f"Agent '{agent_file.name}' is missing required frontmatter fields: {missing}"
            )
            # v0.1.65 FR1/AC-1: staged core bodies are model-agnostic — the resolved
            # `model:`/`effort:` are injected at install time, never staged.
            assert "model" not in keys, (
                f"Agent '{agent_file.name}' stages a hardcoded 'model:' (FR1 violation)"
            )
            assert "effort" not in keys, (
                f"Agent '{agent_file.name}' stages a hardcoded 'effort:' (FR1 violation)"
            )
            for skill in _parse_skills_list(content):
                skill_md = skills_dir / skill / "SKILL.md"
                assert skill_md.exists(), (
                    f"Agent '{agent_file.name}' references skill '{skill}' "
                    f"but '{skill_md.relative_to(workspace)}' does not exist"
                )

        claude_agents_dir = workspace / ".claude" / "agents"
        for agent_file in sorted(claude_agents_dir.glob("*.md")):
            content = agent_file.read_text(encoding="utf-8")
            # Plugin stubs (plugin: true) intentionally omit tools — skip them.
            if _is_plugin_stub(content):
                continue
            assert "tools:" in content, (
                f".claude/agents/{agent_file.name} is missing 'tools:' in frontmatter — "
                "Claude projection must retain it"
            )

        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.is_dir():
                assert (skill_dir / "SKILL.md").exists(), (
                    f"Skill directory '{skill_dir.name}' has no SKILL.md"
                )
        dev_server_skill = (skills_dir / "dev-server-registry" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for cmd in (
            "dadaia server list",
            "dadaia server next",
            "dadaia server register",
            "dadaia server release",
        ):
            assert cmd in dev_server_skill, (
                f"dev-server-registry SKILL.md missing content assert for {cmd!r}"
            )


# ---------------------------------------------------------------------------
# TestDoctor — validates drift/missing detection by the doctor command
# ---------------------------------------------------------------------------


class TestDoctor:
    def test_doctor_reports_all_ok_after_clean_install(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        mgr = _manager()
        mgr.install(workspace, target="all", force=True)

        report = [line.render() for line in mgr.doctor(workspace)]

        failures = [line for line in report if line.startswith(("[drift]", "[missing]"))]
        assert not failures, "Doctor reported failures after clean install:\n" + "\n".join(failures)

    @pytest.mark.parametrize("mutation", ["drift", "missing"], ids=["drift", "missing"])
    def test_doctor_detects_drift_and_missing_after_runtime_mutation(
        self, tmp_path: Path, mutation: str
    ) -> None:
        workspace = tmp_path / "ws"
        mgr = _manager()
        mgr.install(workspace, target="all", force=True)

        if mutation == "drift":
            target = workspace / ".claude" / "agents" / "software-engineer.md"
            target.write_text(
                target.read_text(encoding="utf-8") + "\n# drifted\n", encoding="utf-8"
            )
            report = [line.render() for line in mgr.doctor(workspace)]
            drift_lines = [
                line for line in report if "[drift]" in line and "software-engineer" in line
            ]
            assert drift_lines, (
                "Doctor did not detect drift in .claude/agents/software-engineer.md.\n"
                "Full report:\n" + "\n".join(report)
            )
        else:
            target = workspace / ".claude" / "agents" / "qa-engineer.md"
            target.unlink()
            report = [line.render() for line in mgr.doctor(workspace)]
            missing_lines = [
                line for line in report if "[missing]" in line and "qa-engineer" in line
            ]
            assert missing_lines, (
                "Doctor did not detect missing .claude/agents/qa-engineer.md.\n"
                "Full report:\n" + "\n".join(report)
            )


# ---------------------------------------------------------------------------
# TestPerProfileInit — FR5 / AC-8: per-profile sandboxed E2E scaffolded via the REAL
# `dadaia init --harness <set>` CLI (in-process CliRunner, Q4 — NOT a subprocess), each
# asserting the EXACT default structure + the persisted profile + a profile-scoped GREEN
# `public doctor` (Q7: no [missing]/[drift]/[fail] for out-of-profile harnesses AND CLI
# exit 0). Extends this pipeline module (reuses FileSystemPublicAssetManager + helpers);
# does NOT duplicate the all-harness pipeline tests above.
#
# `WorkspaceService.init` builds a real venv via `ensure_workspace_venv`, but the root
# conftest `_no_real_venv_in_tests` autouse fixture fakes it to a bare mkdir — so these
# real-CLI inits create no venv and exhaust no disk. tmp_path isolates every workspace
# from the repo (no `.dadaia/` inside any repo); the suite runs `-p no:cacheprovider`.
# ---------------------------------------------------------------------------

_DOCTOR_BLOCKER_PREFIXES = ("[missing]", "[drift]", "[fail]")


def _run_init(workspace: Path, harness: str | None) -> object:
    """Scaffold *workspace* via the real `dadaia init` CLI (in-process, Q4).

    ``harness=None`` omits ``--harness`` entirely (default = all-four back-compat path).
    """
    args = ["init", "--workspace", str(workspace)]
    if harness is not None:
        args += ["--harness", harness]
    return _runner.invoke(cli_app, args)


def _persisted_profile(workspace: Path) -> list[str]:
    data = json.loads(
        (workspace / ".dadaia" / "states" / "harness_profile.json").read_text(encoding="utf-8")
    )
    return data["harnesses"]


def _ctx_inject_registered(claude_dir: Path) -> bool:
    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    commands = [
        h["command"]
        for entry in settings.get("hooks", {}).get("UserPromptSubmit", [])
        for h in entry.get("hooks", [])
    ]
    return any("dadaia_workspace.hooks.ctx_inject" in c for c in commands)


def _doctor_blockers(report: list[str]) -> list[str]:
    return [line for line in report if line.startswith(_DOCTOR_BLOCKER_PREFIXES)]


def _assert_profile_doctor_green(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert the profile-scoped `public doctor` is GREEN on both Q7 surfaces.

    * report-list surface — ``FileSystemPublicAssetManager.doctor`` returns no
      ``[missing]``/``[drift]``/``[fail]`` line (this subsumes Q7's "no blocker for the
      out-of-profile harnesses" clause and is stronger — a clean profile tree is fully
      blocker-free);
    * CLI surface — ``dadaia public doctor`` exits 0 (the mechanical Q7 second clause).
    """
    report = [line.render() for line in _manager().doctor(workspace)]
    blockers = _doctor_blockers(report)
    assert blockers == [], "profile doctor must be blocker-free, got:\n" + "\n".join(blockers)

    monkeypatch.chdir(workspace)
    result = _runner.invoke(cli_app, ["public", "doctor"])
    assert result.exit_code == 0, result.output


class TestPerProfileInit:
    def test_claude_only_profile(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-8 claude-only: `.claude/` (agents/skills) + ctx-inject hook; NO .codex/ NO .kimi-code/.

        FR31/T-044-59 (bug dadaia-md-projected-twice-into-claude-code-context): Claude
        Code's own root-import chain (CLAUDE.md -> @AGENTS.md -> @DADAIA.md) already
        resolves the law, so `.claude/rules/DADAIA.md` was the only thing that ever
        landed under `.claude/rules/` and its projection was retired — the directory is
        now never created for a claude profile at all.
        """
        ws = tmp_path / "claude_only"
        monkeypatch.chdir(tmp_path)
        result = _run_init(ws, "claude")
        assert result.exit_code == 0, result.output

        # EXACT structure — claude present with the agents/skills projection subdirs.
        for sub in ("agents", "skills"):
            assert (ws / ".claude" / sub).is_dir(), f".claude/{sub}/ missing for a claude profile"
        assert _ctx_inject_registered(ws / ".claude"), (
            "ctx-inject hook not registered in settings.json"
        )
        # FR31 discriminating anchor: no per-harness law mirror for claude (A31.4/D11).
        assert not (ws / ".claude" / "rules").exists(), (
            ".claude/rules/ must NOT be scaffolded for a claude profile — the law reaches "
            "Claude Code through its own root-import chain, never a rules-dir mirror"
        )
        # AC-9(f) discriminating anchor: the two un-chosen harnesses get NO projection dir.
        assert not (ws / ".codex").exists(), "codex must NOT be scaffolded for a claude profile"
        assert not (ws / ".kimi-code").exists(), "kimi must NOT be scaffolded for a claude profile"

        assert _persisted_profile(ws) == ["claude"]
        _assert_profile_doctor_green(ws, monkeypatch)

    def test_codex_only_profile(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-8 codex-only: `.codex/` (agents/config/rules/hooks.json) + `.dadaia/hooks/codex-*`; NO .claude/ NO .kimi-code/."""
        ws = tmp_path / "codex_only"
        monkeypatch.chdir(tmp_path)
        result = _run_init(ws, "codex")
        assert result.exit_code == 0, result.output

        # EXACT structure — codex config surface + the codex hook wrappers.
        assert (ws / ".codex" / "agents").is_dir(), ".codex/agents/ missing for a codex profile"
        assert (ws / ".codex" / "hooks.json").exists(), ".codex/hooks.json missing"
        assert (ws / ".codex" / "config.toml").exists(), ".codex/config.toml missing"
        assert (ws / ".codex" / "rules" / "dadaia-command-policy.rules").exists()
        codex_wrappers = sorted((ws / ".dadaia" / "hooks").glob("codex-*"))
        assert codex_wrappers, "expected .dadaia/hooks/codex-* wrappers for a codex profile"
        # un-chosen harnesses get no projection.
        assert not (ws / ".claude").exists(), "claude must NOT be scaffolded for a codex profile"
        assert not (ws / ".kimi-code").exists(), "kimi must NOT be scaffolded for a codex profile"

        assert _persisted_profile(ws) == ["codex"]
        # Green requires the W5 boundary completion (runtime_expectations claude:* loop scoped);
        # without it a codex-only doctor emits ×40 [missing] claude:* lines and exits 1.
        _assert_profile_doctor_green(ws, monkeypatch)

    def test_kimi_code_only_profile(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-8 kimi-code-only (v0.2.8): `.kimi-code/` projection; NO .claude/ NO .codex/ NO .kimi-code/."""
        ws = tmp_path / "kimi_code_only"
        monkeypatch.chdir(tmp_path)
        result = _run_init(ws, "kimi-code")
        assert result.exit_code == 0, result.output

        # EXACT structure — the `.kimi-code/` projection carries the staged AGENTS.md.
        assert (ws / ".kimi-code" / "AGENTS.md").is_file(), ".kimi-code/AGENTS.md missing"
        # un-chosen harnesses get no projection.
        assert not (ws / ".claude").exists(), (
            "claude must NOT be scaffolded for a kimi-code profile"
        )
        assert not (ws / ".codex").exists(), "codex must NOT be scaffolded for a kimi-code profile"

        assert _persisted_profile(ws) == ["kimi-code"]

        # Same scripts boundary: chokepoint scripts install for
        # every L1 target (v0.2.8), so the kimi-only tree is doctor-green directly.
        _assert_profile_doctor_green(ws, monkeypatch)

    def test_default_no_flag_scaffolds_all_three(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-8 all-harness: default (no `--harness`) is still all-four; green doctor (back-compat)."""
        ws = tmp_path / "all_default"
        monkeypatch.chdir(tmp_path)
        result = _run_init(ws, None)  # omit --harness entirely → default all-four
        assert result.exit_code == 0, result.output

        assert (ws / ".claude" / "agents").is_dir()
        assert (ws / ".codex").is_dir()
        assert (ws / ".kimi-code").is_dir()
        assert _ctx_inject_registered(ws / ".claude")
        # The all-four install path also lays the chokepoint scripts (target=="all").
        assert (ws / ".dadaia" / "scripts").is_dir()

        assert _persisted_profile(ws) == ["claude", "codex", "kimi-code"]
        _assert_profile_doctor_green(ws, monkeypatch)
