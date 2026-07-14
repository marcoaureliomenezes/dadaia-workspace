"""Integration tests for public asset staging and runtime projections.

Merged per plan-integration.md (39 -> ~8):
  - Keep: install-refuses-dadaia-workspace-source-root (safety), public-privacy gate
    (flags identifiers + ignores bytecode, merged -> 1), CLI pi install+doctor-clean.
  - Merge: stage (manifest + codex adapters) -> 1; install-all + pi projection block
    (ring-1, tree, idempotent, system-note markers, doctor pi-ok) -> 1;
    overwrite-stale/skip-canonical/force -> 1; codex projection (config omits/emits +
    legacy workflow cleanup + native-rules-only) -> 1; model-governance
    overlay (no-overlay lockstep + overlay-change lockstep + invalid-overlay-loud +
    doctor rerender-drift/invalid-vs-missing) -> 2.
  - Delete -> unit (already covered by tests/unit/infrastructure/test_public_assets_*.py,
    T-2's per-concern split): ``_render_agent_toml_block`` quoting/escaping,
    ``_parse_agent_frontmatter`` param cases, ``_render_codex_agent_toml`` field/tier
    cases, command-policy prefix rules, and the
    skill-frontmatter static-lint fn (moved to unit/features/public).

Privacy gate is CRITICAL (public-boundary). Renderer fns keep coverage as unit tests —
no fs/subprocess needed there.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.infrastructure.public_assets import (
    _PRIVACY_DENYLIST_ENV,
    FileSystemPublicAssetManager,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_runner = CliRunner()


# ---------------------------------------------------------------------------
# stage() — manifest + codex runtime adapters, plus
# install(target="all") + pi projection block (Ring-1, tree, idempotent, system-note,
# doctor pi-ok)
# ---------------------------------------------------------------------------


def test_stage_manifest_codex_adapters_install_all_and_pi_projection_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage_workspace = tmp_path / "stage-ws"
    stage_manager = FileSystemPublicAssetManager()

    stage_manager.stage(stage_workspace)

    manifest_path = stage_workspace / ".dadaia" / "agentic" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1"
    assert any(asset["path"] == "data/AGENTS.md" for asset in manifest["assets"])

    assert (
        stage_workspace / ".dadaia" / "agentic" / "runtime" / "codex" / "design-ctx" / "SKILL.md"
    ).exists()
    assert any(asset["path"] == "runtime/codex/design-ctx/SKILL.md" for asset in manifest["assets"])

    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()

    manager.install(workspace, target="all")

    assert (workspace / "AGENTS.md").exists()
    assert (workspace / ".dadaia" / "AGENTS.md").exists()
    assert (workspace / ".dadaia" / "tmp" / "AGENTS.md").exists()
    assert (workspace / ".dadaia" / "states" / "AGENTS.md").exists()
    assert (workspace / ".agents" / "skills" / "dadaia-grill-me" / "SKILL.md").exists()
    assert (workspace / ".claude" / "agents" / "software-architect.md").exists()
    assert (workspace / ".codex" / "hooks.json").exists()
    assert (workspace / ".codex" / "config.toml").exists()
    # Codex receives Starlark .rules for command policy. Markdown behavioral
    # protocols remain guidance, not executable Codex Rules.
    assert not (workspace / ".codex" / "rules" / "game-agents-coordination.md").exists()
    assert not (workspace / ".codex" / "rules" / "game-developer-scope.md").exists()
    assert (workspace / ".codex" / "rules" / "dadaia-command-policy.rules").exists()
    # T-PIO-03: the `pi` target is part of `all`.
    assert (workspace / ".pi" / "SYSTEM.md").exists()
    assert (workspace / ".pi" / "settings.json").exists()

    # T-PIO-04: doctor emits [ok] pi: lines after a clean install.
    reports = manager.doctor(workspace)
    pi_lines = [r for r in reports if "pi:" in r]
    assert any("[ok] pi:SYSTEM.md" in r for r in reports), reports
    assert any("[ok] pi:settings.json" in r for r in reports), reports
    assert all(r.startswith("[ok]") for r in pi_lines), pi_lines

    # WS-PI-4: --target pi (isolated) projects the Layer-1 Ring-1 SDD-gate extension;
    # settings.json lists it, the body carries its invariants, and — as a post-trust
    # executable asset — carries NO operator-local path or secret.
    pi_ws = tmp_path / "pi-only"
    FileSystemPublicAssetManager().install(pi_ws, target="pi")

    ext = pi_ws / ".pi" / "extensions" / "dadaia-sdd-gate.ts"
    assert ext.exists()
    body = ext.read_text(encoding="utf-8")
    assert "dadaia_workspace.hooks.pre_gate" in body
    assert 'pi.on("tool_call"' in body or "pi.on('tool_call'" in body
    assert "write" in body and "Write" in body and "edit" in body and "Edit" in body
    assert '"decision":"block"' in body or "decision" in body
    assert "block: true" in body
    assert ".venv" in body and "python" in body
    assert "/home/" not in body and "/Users/" not in body
    for secret_token in ("ANTHROPIC_API_KEY", "TOKEN=", "SECRET", "password"):
        assert secret_token not in body

    settings = json.loads((pi_ws / ".pi" / "settings.json").read_text(encoding="utf-8"))
    assert any("dadaia-sdd-gate" in entry for entry in settings.get("extensions", [])), settings

    # T-PIO-03: public/pi/ -> .pi/ tree.
    assert (pi_ws / ".pi" / "prompts" / "dadaia-context.md").exists()
    assert isinstance(settings, dict)

    # T-PIO-03/07: re-install is idempotent (hash-compare skip); doctor stays clean.
    second = FileSystemPublicAssetManager().install(pi_ws, target="pi")
    pi_results = [line for line in second if str(pi_ws / ".pi") in line]
    assert pi_results, "expected .pi/ projection lines on re-install"
    assert all("[skip]" in line for line in pi_results), pi_results

    reports2 = FileSystemPublicAssetManager().doctor(pi_ws)
    pi_lines2 = [r for r in reports2 if "pi:" in r]
    assert pi_lines2 and all(r.startswith("[ok]") for r in pi_lines2), pi_lines2
    drift = [r for r in reports2 if r.startswith(("[drift]", "[missing]")) and "pi" in r]
    assert not drift, drift

    # Layer-1 governance content in the projected .pi/SYSTEM.md + context prompt.
    system_note = (pi_ws / ".pi" / "SYSTEM.md").read_text(encoding="utf-8")
    context_prompt = (pi_ws / ".pi" / "prompts" / "dadaia-context.md").read_text(encoding="utf-8")
    assert "AGENTS.md" in system_note
    assert "dadaia" in system_note
    assert "SDD" in system_note
    assert "Layer-1" in system_note
    assert "post-trust" in system_note
    assert "this note carries none" in system_note
    assert "/home/" not in system_note
    assert "/home/" not in context_prompt
    assert "dadaia" in context_prompt

    # Layer-1 e2e through the REAL CLI: `dadaia public install --target pi` is the
    # command the operator runs to 'enter pi'. Drive it via CliRunner against an
    # isolated temp workspace, then `dadaia public doctor` — assert the `.pi/` tree
    # lands and doctor reports the pi projection green (proving the operator-facing
    # path, not just the manager API).
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    cli_workspace = tmp_path / "cli-ws"
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(cli_workspace)
    monkeypatch.chdir(cli_workspace)

    install = _runner.invoke(app, ["public", "install", "--target", "pi"])
    assert install.exit_code == 0, install.output

    assert (cli_workspace / ".pi" / "SYSTEM.md").exists()
    assert (cli_workspace / ".pi" / "settings.json").exists()
    assert (cli_workspace / ".pi" / "prompts" / "dadaia-context.md").exists()

    doctor = _runner.invoke(app, ["public", "doctor"])
    assert doctor.exit_code == 0, doctor.output
    assert "pi:" in doctor.output


# ---------------------------------------------------------------------------
# Safety — never touch the dadaia-workspace source root itself.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Safety (never touch the dadaia-workspace source root itself) +
# overwrite-stale/skip-canonical/force
# ---------------------------------------------------------------------------


def test_install_refuses_source_root_overwrite_skip_force_and_doctor_drift_tracking(
    tmp_path: Path,
) -> None:
    """T-PROP-01: hash-compare governs overwrite-without-force / skip-when-canonical /
    force; doctor tracks the dadaia-scoped AGENTS.md files for drift. Plus: install()
    refuses to project onto the dadaia-workspace source root itself (own workspace)."""
    source_root = tmp_path / "dadaia-workspace"
    source_root.mkdir()
    (source_root / "dadaia_workspace" / "public").mkdir(parents=True)
    (source_root / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "dadaia-workspace"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )

    source_root_manager = FileSystemPublicAssetManager()

    with pytest.raises(PublicAssetError, match="Refusing to project public runtime assets"):
        source_root_manager.install(source_root, target="all")

    assert not (source_root / ".dadaia").exists()
    assert not (source_root / ".codex").exists()

    workspace = tmp_path / "ws"
    agents_md = workspace / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text("custom\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager.install(workspace, target="all")

    content = agents_md.read_text(encoding="utf-8")
    assert content != "custom\n", "Expected stale AGENTS.md to be overwritten"
    assert "AI agent" in content or "dadaia" in content.lower()
    canonical_content = content
    mtime_before = agents_md.stat().st_mtime

    # Second install: same hash -> skip (no-op).
    manager.install(workspace, target="all")
    assert agents_md.read_text(encoding="utf-8") == canonical_content
    assert agents_md.stat().st_mtime == mtime_before

    # force=True overwrites even when a stale placeholder is reintroduced.
    force_ws = tmp_path / "force-ws"
    force_agents = force_ws / "AGENTS.md"
    force_agents.parent.mkdir(parents=True, exist_ok=True)
    force_agents.write_text("custom\n", encoding="utf-8")
    FileSystemPublicAssetManager().install(force_ws, target="all", force=True)
    force_content = force_agents.read_text(encoding="utf-8")
    assert force_content != "custom\n"
    assert "# dadaia-workspace" in force_content

    # doctor tracks .dadaia-scoped AGENTS.md files for drift.
    drift_ws = tmp_path / "drift-ws"
    drift_manager = FileSystemPublicAssetManager()
    drift_manager.stage(drift_ws)
    drift_manager.install(drift_ws, target="all", force=True)

    clean_report = drift_manager.doctor(drift_ws)
    assert "[ok] dadaia:AGENTS.md" in clean_report
    assert "[ok] dadaia:tmp/AGENTS.md" in clean_report
    assert "[ok] dadaia:states/AGENTS.md" in clean_report

    (drift_ws / ".dadaia" / "states" / "AGENTS.md").write_text("drift\n", encoding="utf-8")
    drift_report = drift_manager.doctor(drift_ws)
    assert "[drift] dadaia:states/AGENTS.md" in drift_report


# ---------------------------------------------------------------------------
# Public-privacy gate (CRITICAL — public-boundary)
# ---------------------------------------------------------------------------

_PRIVACY_TEST_TERM = "10.99.99.99"


def _seed_denylist_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Seed the denylist via env var (location-independent; avoids .dadaia/ in lib repo)."""
    source = tmp_path / "privacy_denylist.json"
    source.write_text(json.dumps([[_PRIVACY_TEST_TERM, "test private IP"]]), encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(source))


def test_public_privacy_gate_flags_identifiers_and_ignores_bytecode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_denylist_env(monkeypatch, tmp_path)
    repo_root = tmp_path / "repo"
    public_dir = repo_root / "dadaia_workspace" / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "AGENTS.md").write_text(
        f"Private endpoint: {_PRIVACY_TEST_TERM}\n", encoding="utf-8"
    )

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    report = manager._check_public_privacy()  # noqa: SLF001

    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any(_PRIVACY_TEST_TERM in line.lower() for line in report)

    # A denylisted term inside a __pycache__/*.pyc is ignored (bytecode is not scanned).
    clean_repo_root = tmp_path / "repo-clean"
    clean_public_dir = clean_repo_root / "dadaia_workspace" / "public"
    cache_dir = clean_public_dir / "skills" / "sample" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "leak.pyc").write_bytes(_PRIVACY_TEST_TERM.encode())
    (clean_public_dir / "data").mkdir()
    (clean_public_dir / "data" / "AGENTS.md").write_text("# clean\n", encoding="utf-8")

    clean_manager = FileSystemPublicAssetManager()
    clean_manager._public_dir = clean_public_dir  # noqa: SLF001
    assert clean_manager._check_public_privacy() == ["[ok] public-privacy"]  # noqa: SLF001


# ---------------------------------------------------------------------------
# Codex projection: config omits inert keys, legacy workflow references are removed,
# and only native .rules command policy is installed.
# ---------------------------------------------------------------------------


def _make_codex_install_manager(tmp_path: Path) -> tuple[FileSystemPublicAssetManager, Path]:
    """Return a manager pointed at a minimal public dir and a workspace root.

    The public/ dir has only what _install_codex() strictly requires: a rules/
    subdir and an agents/ subdir (both may be empty).
    """
    public_dir = tmp_path / "public"
    (public_dir / "rules").mkdir(parents=True)
    (public_dir / "agents").mkdir(parents=True)
    workspace_root = tmp_path / "ws"
    workspace_root.mkdir()
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001
    return manager, workspace_root


def test_codex_projection_config_legacy_cleanup_and_native_rules(tmp_path: Path) -> None:
    # W1-2 — _codex_config() emits neither the [skills] table nor approved_commands,
    # for both a no-agents and a real-agents source dir; the real dir still emits
    # [agents.*] blocks.
    manager_probe = FileSystemPublicAssetManager()
    real_agentic_dir = manager_probe._public_dir  # noqa: SLF001
    for agentic_dir in (Path("/nonexistent/agentic"), real_agentic_dir):
        output = manager_probe._codex_config(agentic_dir)  # noqa: SLF001
        assert "[skills]" not in output, f"Expected no '[skills]' section; got:\n{output}"
        assert "approved_commands" not in output, (
            f"Expected no 'approved_commands' array; got:\n{output}"
        )

    real_output = manager_probe._codex_config(real_agentic_dir)  # noqa: SLF001
    assert "[agents." in real_output, "Expected at least one [agents.*] block in output"
    assert real_output.startswith('# Generated by "dadaia public install --target codex".')

    # The retired Markdown workflow source is not projected.
    manager, workspace_root = _make_codex_install_manager(tmp_path)
    manager.install(workspace_root, target="codex", force=True)
    assert not (workspace_root / ".codex" / "workflows").exists()

    # Installation removes only retired workflow files and preserves unrelated
    # operator-owned content in the directory.
    legacy_manager, legacy_ws = _make_codex_install_manager(tmp_path / "legacy-case")
    legacy_workflows_dir = legacy_ws / ".codex" / "workflows"
    legacy_workflows_dir.mkdir(parents=True)
    (legacy_workflows_dir / "hotfix-release.workflow.md").write_text(
        "stale content\n", encoding="utf-8"
    )
    (legacy_workflows_dir / "operator-note.txt").write_text("keep\n", encoding="utf-8")
    legacy_manager.install(legacy_ws, target="codex", force=True)
    assert not (legacy_workflows_dir / "hotfix-release.workflow.md").exists()
    assert (legacy_workflows_dir / "operator-note.txt").read_text(encoding="utf-8") == "keep\n"

    # Markdown behavioral protocols are not projected as Codex Rules — only the
    # native .rules command policy is.
    rules_manager, rules_ws = _make_codex_install_manager(tmp_path / "rules-case")
    rules_public_dir = rules_manager._public_dir  # noqa: SLF001
    rules_src = rules_public_dir / "rules"
    (rules_src / "game-agents-coordination.md").write_text(
        "# game-agents-coordination\nProse rule\n", encoding="utf-8"
    )
    (rules_src / "workspace-protocol.md").write_text(
        "---\nname: workspace-protocol\n---\n# body\n", encoding="utf-8"
    )
    rules_manager.install(rules_ws, target="codex", force=True)
    rules_dst = rules_ws / ".codex" / "rules"
    assert not (rules_dst / "game-agents-coordination.md").exists(), (
        "Behavioral rule should NOT be projected to .codex/rules/"
    )
    assert not (rules_dst / "workspace-protocol.md").exists()
    assert (rules_dst / "dadaia-command-policy.rules").exists()


# ---------------------------------------------------------------------------
# Model-governance overlay (v0.1.65 FR5/FR7) — lockstep rendering, invalid-overlay
# fail-loud, and the render-at-install doctor.
# ---------------------------------------------------------------------------


def _claude_frontmatter(ws: Path, agent: str) -> dict[str, str]:
    text = (ws / ".claude" / "agents" / f"{agent}.md").read_text(encoding="utf-8")
    fm = text.split("---\n", 2)[1]
    out: dict[str, str] = {}
    for line in fm.splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            out[key] = value.strip()
    return out


def _codex_toml_fields(ws: Path, agent: str) -> dict[str, str]:
    text = (ws / ".codex" / "agents" / f"{agent}.toml").read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for line in text.splitlines():
        if " = " in line and not line.startswith(" "):
            key, _, value = line.partition(" = ")
            out[key] = value.strip().strip('"')
        if line.startswith("developer_instructions"):
            break
    return out


def test_model_policy_overlay_lockstep_rendering_invalid_fails_loud_and_doctor_rerender(
    tmp_path: Path,
) -> None:
    """AC-2/AC-3 + F-1: no-overlay renders the balanced roster; an overlay change moves
    BOTH .claude md and .codex toml together at install (byte-stable repeats); an
    invalid overlay fails loud before any write.

    Plus FR7 — AC-5, all three directions + F-2 pin, plus the invalid-vs-missing overlay
    doctor distinction (own workspace):
    1. Immediately after a policy re-render, doctor reports [ok] on every
       ``claude:agents/*.md`` line (no false [drift] against staged generic bytes).
    2. A hand-edited projected ``.claude/agents/*.md`` reads [drift].
    3. Non-agent ``stage:``/runtime compare lines stay [ok], untouched by the
       render seam (F-2 — never a global ``_compare`` patch).
    4. A missing overlay is not a doctor ERROR; an invalid overlay is.
    """
    ws = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()
    manager.install(ws, target="all")

    # AC-2: with no overlay, BOTH projections render the exact `balanced` roster from
    # the SAME resolved config — this lockstep IS the codex-correctness assurance (no
    # codex doctor byte-compare exists).
    pm = _claude_frontmatter(ws, "project-manager")
    assert (pm["model"], pm["effort"]) == ("claude-fable-5", "high")
    se = _claude_frontmatter(ws, "software-engineer")
    assert (se["model"], se["effort"]) == ("claude-sonnet-5", "xhigh")
    sec = _claude_frontmatter(ws, "security-reviewer")
    assert sec["model"] == "claude-opus-4-8", "never Fable on security-reviewer (G-1)"

    pm_toml = _codex_toml_fields(ws, "project-manager")
    assert (pm_toml["model"], pm_toml["model_reasoning_effort"]) == ("gpt-5.5", "high")
    se_toml = _codex_toml_fields(ws, "software-engineer")
    assert (se_toml["model"], se_toml["model_reasoning_effort"]) == (
        "gpt-5.3-codex",
        "high",  # xhigh clamps to high (D-3)
    )

    # AC-3: an overlay change moves the .claude md AND .codex toml together at install.
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "agent_model_policy.json").write_text(
        json.dumps(
            {
                "schema_version": "agent-model-policy-v1",
                "applied_template": "subscription-saver",
                "overrides": {"software-engineer": {"model": "claude-opus-4-8"}},
            }
        ),
        encoding="utf-8",
    )
    manager.install(ws, target="all")

    se2 = _claude_frontmatter(ws, "software-engineer")
    assert (se2["model"], se2["effort"]) == ("claude-opus-4-8", "xhigh")
    pm2 = _claude_frontmatter(ws, "project-manager")
    assert (pm2["model"], pm2["effort"]) == ("claude-opus-4-8", "high")

    se2_toml = _codex_toml_fields(ws, "software-engineer")
    assert (se2_toml["model"], se2_toml["model_reasoning_effort"]) == ("gpt-5.5", "high")
    pm2_toml = _codex_toml_fields(ws, "project-manager")
    assert (pm2_toml["model"], pm2_toml["model_reasoning_effort"]) == ("gpt-5.5", "high")

    # Byte-stable repeated install: every agent projection line is a [skip].
    third = manager.install(ws, target="all")
    agent_lines = [
        line
        for line in third
        if "/.claude/agents/" in line.replace("\\", "/")
        or "/.codex/agents/" in line.replace("\\", "/")
    ]
    assert agent_lines, "expected agent projection lines"
    not_skipped = [line for line in agent_lines if not line.startswith("[skip]")]
    assert not_skipped == [], f"repeated install must be byte-stable: {not_skipped}"

    # NFR-4: invalid overlay -> loud typed error, never a silent fallback; the
    # projection tree is not touched.
    from dadaia_workspace.core.models.agent_model_policy import (
        AgentModelPolicyStoreError,
    )

    invalid_ws = tmp_path / "invalid-ws"
    invalid_manager = FileSystemPublicAssetManager()
    invalid_manager.install(invalid_ws, target="all")
    before = (invalid_ws / ".claude" / "agents" / "software-engineer.md").read_bytes()

    invalid_states = invalid_ws / ".dadaia" / "states"
    (invalid_states / "agent_model_policy.json").write_text(
        json.dumps(
            {
                "schema_version": "agent-model-policy-v1",
                "overrides": {"security-reviewer": {"model": "claude-fable-5"}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AgentModelPolicyStoreError):
        invalid_manager.install(invalid_ws, target="all")
    after = (invalid_ws / ".claude" / "agents" / "software-engineer.md").read_bytes()
    assert after == before

    # FR7 doctor rerender/hand-edit-drift/invalid-overlay-error, own workspace.
    doctor_ws = tmp_path / "doctor-ws"
    doctor_manager = FileSystemPublicAssetManager()
    doctor_manager.install(doctor_ws, target="all")

    clean = doctor_manager.doctor(doctor_ws)
    assert not any("agent-model-policy ERROR" in r for r in clean), (
        "missing overlay must not emit an agent-model-policy ERROR line"
    )

    doctor_states = doctor_ws / ".dadaia" / "states"
    doctor_states.mkdir(parents=True, exist_ok=True)
    (doctor_states / "agent_model_policy.json").write_text(
        json.dumps(
            {
                "schema_version": "agent-model-policy-v1",
                "applied_template": "max-quality",
            }
        ),
        encoding="utf-8",
    )
    doctor_manager.install(doctor_ws, target="all")

    reports = doctor_manager.doctor(doctor_ws)
    agent_lines = [r for r in reports if r.split(" ", 1)[-1].startswith("claude:agents/")]
    assert agent_lines, "expected claude:agents doctor lines"
    bad = [r for r in agent_lines if not r.startswith("[ok]")]
    assert bad == [], f"policy re-render must be doctor-[ok]: {bad}"

    stage_agent_lines = [r for r in reports if r.split(" ", 1)[-1].startswith("stage:agents/")]
    assert stage_agent_lines and all(r.startswith("[ok]") for r in stage_agent_lines), (
        stage_agent_lines
    )
    rule_lines = [r for r in reports if r.split(" ", 1)[-1].startswith("claude:rules/")]
    assert rule_lines and all(r.startswith("[ok]") for r in rule_lines), rule_lines[:5]

    target = doctor_ws / ".claude" / "agents" / "software-engineer.md"
    target.write_text(target.read_text(encoding="utf-8") + "\nHAND EDIT\n", encoding="utf-8")
    reports2 = doctor_manager.doctor(doctor_ws)
    assert any(
        r.startswith("[drift]") and r.endswith("claude:agents/software-engineer.md")
        for r in reports2
    ), [r for r in reports2 if "software-engineer" in r]

    (doctor_states / "agent_model_policy.json").write_text("{not json", encoding="utf-8")
    reports3 = doctor_manager.doctor(doctor_ws)
    assert any(r.startswith("[drift]") and "agent-model-policy" in r for r in reports3), [
        r for r in reports3 if "policy" in r
    ]
