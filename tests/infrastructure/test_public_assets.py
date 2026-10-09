"""v0.4.5 A4.1-4.3: the authority for public stage, install and drift
(rosters, the source-root refusal, hash-compare overwrite/skip/force, the privacy gate,
model-policy rendering, single-place skill rename). Size: MEDIUM — real projection I/O.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.model_registry import is_fable_model
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers import public_asset_roster
from tests.helpers.harness_profile import register_all
from tests.helpers.privacy_fixtures import private_ip
from tests.helpers.scan_population import assert_populated
from tests.helpers.skill_inventory_oracle import skill_names


def _rendered(result: object) -> list[str]:
    """Legacy string view of a typed doctor result (DoctorReport | list[DoctorLine])."""
    if hasattr(result, "rendered"):
        return result.rendered()  # type: ignore[attr-defined, no-any-return]
    return [
        line.render() if hasattr(line, "render") else str(line)
        for line in result  # type: ignore[union-attr]
    ]


pytestmark = pytest.mark.slow

_DESIGN_SKILLS = tuple(f"dd-{n}" for n in ("domain-modeling", "codebase-design", "architecture-survey"))

_runner = CliRunner()
_AGENTS = {"dd-code-reviewer", "dd-product-engineer", "dd-software-engineer"}


def test_stage_manifest_and_install_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stage_workspace = tmp_path / "stage-ws"
    stage_manager = FileSystemPublicAssetManager()

    stage_manager.stage(stage_workspace)

    agentic = stage_workspace / ".dadaia" / "agentic"
    # sa-staged-assets-without-consumers#44.2: only families a reader of
    # .dadaia/agentic/ consumes are staged (no `rules`, no 0.4.7 FR3 `runtime/`).
    assert sorted(p.name for p in agentic.iterdir()) == [
        "agents", "data", "manifest.json", "schemas", "skills",
    ]  # fmt: skip
    manifest = json.loads((agentic / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1"
    assert any(asset["path"] == "data/AGENTS.md" for asset in manifest["assets"])
    assert all({"path", "sha256", "type"} <= set(asset) for asset in manifest["assets"])
    staged_agents = {
        Path(a["path"]).stem
        for a in manifest["assets"]
        if a["type"] == "agents" and a["path"].endswith(".md")
    }
    assert staged_agents == _AGENTS
    oracle_skills = skill_names()
    # v0.4.5 FR5 (scan-test-vacuity-guard): an empty oracle would make every roster vacuous.
    assert_populated(oracle_skills, sentinel="dd-cli-library")
    assert {p.name for p in (agentic / "skills").iterdir() if p.is_dir()} == oracle_skills

    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()

    register_all(workspace)
    manager.install(workspace)

    assert (workspace / "AGENTS.md").exists()
    assert (workspace / ".dadaia" / "AGENTS.md").exists()
    assert (workspace / ".dadaia" / "tmp" / "AGENTS.md").exists()
    assert (workspace / ".dadaia" / "states" / "AGENTS.md").exists()
    installed = {p.parent.name for p in (workspace / ".agents" / "skills").glob("*/SKILL.md")}
    assert installed == oracle_skills
    assert {p.stem for p in (workspace / ".claude" / "agents").glob("*.md")} == _AGENTS
    assert (workspace / ".codex" / "hooks.json").exists()
    assert (workspace / ".codex" / "config.toml").exists()
    assert (workspace / ".codex" / "rules" / "dadaia-command-policy.rules").exists()


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
        source_root_manager.install(source_root)

    assert not (source_root / ".dadaia").exists()
    assert not (source_root / ".codex").exists()

    workspace = tmp_path / "ws"
    agents_md = workspace / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text("custom\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager.install(workspace)

    content = agents_md.read_text(encoding="utf-8")
    assert content != "custom\n", "Expected stale AGENTS.md to be overwritten"
    assert "AI agent" in content or "dadaia" in content.lower()
    canonical_content = content
    mtime_before = agents_md.stat().st_mtime

    # Second install: same hash -> skip (no-op).
    manager.install(workspace)
    assert agents_md.read_text(encoding="utf-8") == canonical_content
    assert agents_md.stat().st_mtime == mtime_before

    # force=True overwrites even when a stale placeholder is reintroduced.
    force_ws = tmp_path / "force-ws"
    force_agents = force_ws / "AGENTS.md"
    force_agents.parent.mkdir(parents=True, exist_ok=True)
    force_agents.write_text("custom\n", encoding="utf-8")
    FileSystemPublicAssetManager().install(force_ws, force=True)
    force_content = force_agents.read_text(encoding="utf-8")
    assert force_content != "custom\n"
    assert "# dadaia-workspace" in force_content

    # doctor tracks .dadaia-scoped AGENTS.md files for drift.
    drift_ws = tmp_path / "drift-ws"
    drift_manager = FileSystemPublicAssetManager()
    drift_manager.stage(drift_ws)
    drift_manager.install(drift_ws, force=True)

    clean_report = _rendered(drift_manager.doctor(drift_ws))
    assert "[ok] dadaia:AGENTS.md" in clean_report
    assert "[ok] dadaia:tmp/AGENTS.md" in clean_report
    assert "[ok] dadaia:states/AGENTS.md" in clean_report

    (drift_ws / ".dadaia" / "states" / "AGENTS.md").write_text("drift\n", encoding="utf-8")
    drift_report = _rendered(drift_manager.doctor(drift_ws))
    assert "[drift] dadaia:states/AGENTS.md" in drift_report


# ---------------------------------------------------------------------------
# Public-privacy gate (CRITICAL — public-boundary)
# ---------------------------------------------------------------------------

_PRIVACY_TEST_TERM = private_ip()


def _seed_denylist_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Seed the denylist via env var (location-independent; avoids .dadaia/ in lib repo)."""
    source = tmp_path / "privacy_denylist.json"
    source.write_text(json.dumps({_PRIVACY_TEST_TERM: "test private IP"}), encoding="utf-8")
    monkeypatch.setenv("DADAIA_PRIVACY_DENYLIST", str(source))


def test_public_privacy_gate_flags_identifiers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-private-match-rendering-has-three-renderers#B1."""
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

    rendered = [line.render() for line in report]
    assert any(line.startswith("[error] public-privacy:") for line in rendered)
    shown = f"'{_PRIVACY_TEST_TERM[0]}…{_PRIVACY_TEST_TERM[-1]}'"  # WP-11: first…last
    assert any(shown in line.lower() for line in rendered)


# ---------------------------------------------------------------------------
# Codex projection: config omits inert keys, legacy workflow references are removed,
# and only native .rules command policy is installed.
# ---------------------------------------------------------------------------


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
    2. A hand edit made THROUGH the ``.claude/agents/*.md`` symlink lands on the
       authored ``.agents/agents/*.md`` and reads [drift] there — one authored set,
       so one drift line, not one per harness view.
    3. Non-agent ``stage:``/runtime compare lines stay [ok], untouched by the
       render seam (F-2 — never a global ``_compare`` patch).
    4. A missing overlay is not a doctor ERROR; an invalid overlay is.
    """
    ws = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()
    register_all(ws)
    manager.install(ws)

    # AC-2: with no overlay, BOTH projections render the exact `balanced` roster from
    # the SAME resolved config — this lockstep IS the codex-correctness assurance (no
    # codex doctor byte-compare exists).
    pm = _claude_frontmatter(ws, "dd-product-engineer")
    assert (pm["model"], pm["effort"]) == ("claude-opus-5-5", "high")
    se = _claude_frontmatter(ws, "dd-software-engineer")
    assert (se["model"], se["effort"]) == ("claude-opus-5-5", "low")
    sec = _claude_frontmatter(ws, "dd-code-reviewer")
    assert not is_fable_model(sec["model"]), "never Fable on dd-code-reviewer (G-1)"

    pm_toml = _codex_toml_fields(ws, "dd-product-engineer")
    assert (pm_toml["model"], pm_toml["model_reasoning_effort"]) == ("gpt-5.6-sol", "high")
    se_toml = _codex_toml_fields(ws, "dd-software-engineer")
    assert (se_toml["model"], se_toml["model_reasoning_effort"]) == ("gpt-5.6-sol", "low")

    # AC-3: an overlay change moves the .claude md AND .codex toml together at install.
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "agent_model_policy.json").write_text(
        json.dumps(
            {
                "schema_version": "agent-model-policy-v1",
                "applied_template": "max-quality",
                "overrides": {"dd-software-engineer": {"model": "claude-opus-4-8"}},
            }
        ),
        encoding="utf-8",
    )
    manager.install(ws)

    se2 = _claude_frontmatter(ws, "dd-software-engineer")
    assert (se2["model"], se2["effort"]) == ("claude-opus-4-8", "medium")
    pm2 = _claude_frontmatter(ws, "dd-product-engineer")
    assert (pm2["model"], pm2["effort"]) == ("claude-fable-5-1", "high")

    se2_toml = _codex_toml_fields(ws, "dd-software-engineer")
    assert (se2_toml["model"], se2_toml["model_reasoning_effort"]) == ("gpt-5.6-sol", "medium")
    pm2_toml = _codex_toml_fields(ws, "dd-product-engineer")
    assert (pm2_toml["model"], pm2_toml["model_reasoning_effort"]) == ("gpt-5.6-sol", "high")

    # Byte-stable repeated install: every agent projection line is a [skip].
    third = manager.install(ws)
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
    from dadaia_workspace.core.model_registry import (
        AgentModelPolicyStoreError,
    )

    invalid_ws = tmp_path / "invalid-ws"
    invalid_manager = FileSystemPublicAssetManager()
    register_all(invalid_ws)
    invalid_manager.install(invalid_ws)
    before = (invalid_ws / ".claude" / "agents" / "dd-software-engineer.md").read_bytes()

    invalid_states = invalid_ws / ".dadaia" / "states"
    (invalid_states / "agent_model_policy.json").write_text(
        json.dumps(
            {
                "schema_version": "agent-model-policy-v1",
                "overrides": {"dd-code-reviewer": {"model": "claude-fable-5"}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AgentModelPolicyStoreError):
        invalid_manager.install(invalid_ws)
    after = (invalid_ws / ".claude" / "agents" / "dd-software-engineer.md").read_bytes()
    assert after == before

    # FR7 doctor rerender/hand-edit-drift/invalid-overlay-error, own workspace.
    doctor_ws = tmp_path / "doctor-ws"
    doctor_manager = FileSystemPublicAssetManager()
    register_all(doctor_ws)
    doctor_manager.install(doctor_ws)

    clean = _rendered(doctor_manager.doctor(doctor_ws))
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
    doctor_manager.install(doctor_ws)

    reports = _rendered(doctor_manager.doctor(doctor_ws))
    agent_lines = [r for r in reports if r.split(" ", 1)[-1].startswith("claude:agents/")]
    assert agent_lines, "expected claude:agents doctor lines"
    bad = [r for r in agent_lines if not r.startswith("[ok]")]
    assert bad == [], f"policy re-render must be doctor-[ok]: {bad}"

    stage_agent_lines = [r for r in reports if r.split(" ", 1)[-1].startswith("stage:agents/")]
    assert stage_agent_lines and all(r.startswith("[ok]") for r in stage_agent_lines), (
        stage_agent_lines
    )
    # The law is one projected file, the root map: its doctor line is ``root:AGENTS.md``
    # (byte-compared), never a ``claude:rules/*`` per-rule line.
    law_lines = [r for r in reports if r.split(" ", 1)[-1].startswith("root:AGENTS.md")]
    assert law_lines and all(r.startswith("[ok]") for r in law_lines), law_lines[:5]

    target = doctor_ws / ".claude" / "agents" / "dd-software-engineer.md"
    target.write_text(target.read_text(encoding="utf-8") + "\nHAND EDIT\n", encoding="utf-8")
    reports2 = _rendered(doctor_manager.doctor(doctor_ws))
    assert any(
        r.startswith("[drift]") and r.endswith("agents:agents/dd-software-engineer.md")
        for r in reports2
    ), [r for r in reports2 if "dd-software-engineer" in r]
    assert any(
        r.startswith("[ok]") and r.endswith("claude:agents/dd-software-engineer.md")
        for r in reports2
    ), "the claude view is a link: it is correct as long as it points at the authored set"

    (doctor_states / "agent_model_policy.json").write_text("{not json", encoding="utf-8")
    reports3 = _rendered(doctor_manager.doctor(doctor_ws))
    assert any(r.startswith("[drift]") and "agent-model-policy" in r for r in reports3), [
        r for r in reports3 if "policy" in r
    ]


# ---------------------------------------------------------------------------
# FR4 — one derived skill-inventory oracle replaces three hand-kept lists.
# ---------------------------------------------------------------------------


def test_a_single_skill_rename_is_green_everywhere_after_one_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.4.5 A4.1, A4.2, A4.3

    Executed proof (not reasoning) that ``tests.helpers.skill_inventory_oracle`` is the
    ONE shared source every former hand-kept inventory now reads. This seam produced
    two v0.4.4 bugs: a skill added/renamed/removed under
    ``dadaia_workspace/public/skills/`` and forgotten in one of three independently
    kept lists — ``test_public_pipeline.py``'s ``EXPECTED_SKILLS`` literal and this file's
    single hand-picked skill path assertion. Both are gone; each now reads
    :func:`tests.helpers.skill_inventory_oracle.skill_names`.

    A mirror tree (the T-045-15 pattern) is built — the real
    ``dadaia_workspace/public/`` tree is never mutated — and ONE skill directory is
    renamed inside it, plus the same skill's references in every agent frontmatter
    files that list it (the edit a real rename requires; the ORACLE ITSELF needs no
    edit — A4.3, derived from the tree, never a literal list). What is asserted is that
    the pipeline expectation (the former ``EXPECTED_SKILLS`` comparison) and the
    installed-asset assertion (the former hand-picked path) agree with the renamed name
    with ZERO further edits to either former list.
    """
    real_public_dir = public_asset_roster.default_public_dir()
    old_name, new_name = "dd-handoff-emitter", "dd-handoff-emitter-renamed-t045-16"
    real_roster = skill_names()
    assert old_name in real_roster
    assert new_name not in real_roster

    mirror_public = tmp_path / "mirror" / "dadaia_workspace" / "public"
    mirror_public.parent.mkdir(parents=True)
    shutil.copytree(real_public_dir, mirror_public)

    (mirror_public / "skills" / old_name).rename(mirror_public / "skills" / new_name)
    old_ref, new_ref = f"  - {old_name}\n", f"  - {new_name}\n"
    rewritten_agents = 0
    for agent_file in (mirror_public / "agents").glob("*.md"):
        text = agent_file.read_text(encoding="utf-8")
        if old_ref in text:
            agent_file.write_text(text.replace(old_ref, new_ref), encoding="utf-8")
            rewritten_agents += 1
    assert rewritten_agents >= 1, "expected at least one agent frontmatter file to reference it"

    mutated_roster = skill_names(mirror_public)
    assert new_name in mutated_roster
    assert old_name not in mutated_roster
    assert mutated_roster == (real_roster - {old_name}) | {new_name}

    # Consumer 1 — the pipeline expectation (test_public_pipeline.py's staged/installed
    # skill-set comparison): `installed_skills == skill_names()`, now a live call, not a
    # hardcoded literal — so it needs zero edit to reflect the rename.
    mgr = FileSystemPublicAssetManager()
    mgr._public_dir = mirror_public  # noqa: SLF001 — exercise the mirror only
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr.install(ws)
    installed_skills = {p.name for p in (ws / ".agents" / "skills").iterdir() if p.is_dir()}
    assert installed_skills == mutated_roster

    # Consumer 2 — the installed-asset assertion (this file's
    # test_stage_manifest_codex_adapters_and_install_all): every oracle-listed skill
    # has its SKILL.md installed — again zero edit needed for the rename.
    for skill in mutated_roster:
        assert (ws / ".agents" / "skills" / skill / "SKILL.md").exists()
    assert not (ws / ".agents" / "skills" / old_name).exists()


def test_the_three_design_skills_are_gone_from_stage_install_and_the_shipped_tree(
    tmp_path: Path,
) -> None:
    """AC1.2: stage ships none, install prunes stale instance copies, doctor stays clean,
    and the shipped tree (dadaia_workspace, tests, CONTEXT.md) cites none of them."""
    ws = tmp_path / "ws"
    stale = ws / ".agents" / "skills"
    for name in _DESIGN_SKILLS:
        (stale / name).mkdir(parents=True)
        (stale / name / "SKILL.md").write_text("stale\n", encoding="utf-8")
    manager = FileSystemPublicAssetManager()
    register_all(ws)
    manager.stage(ws)
    manager.install(ws)

    staged = {p.name for p in (ws / ".dadaia" / "agentic" / "skills").iterdir()}
    installed = {p.name for p in stale.iterdir()}
    assert staged & set(_DESIGN_SKILLS) == set()
    assert installed & set(_DESIGN_SKILLS) == set()
    report = _rendered(manager.doctor(ws))
    assert not [line for line in report if line.startswith(("[drift]", "[missing]", "[error]"))]

    repo = Path(__file__).resolve().parents[2]
    hits = subprocess.run(
        ["git", "grep", "-nE", "|".join(_DESIGN_SKILLS), "--", "dadaia_workspace", "tests", "CONTEXT.md"],
        cwd=repo, capture_output=True, text=True, check=False,
    ).stdout.splitlines()  # fmt: skip
    # this file spells the names only through f"dd-{n}", so it cannot self-match
    assert hits == []
