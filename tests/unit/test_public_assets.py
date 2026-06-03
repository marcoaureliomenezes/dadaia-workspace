"""Unit tests for public asset staging and runtime projections."""

import json
import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    _parse_agent_frontmatter,
    _render_agent_toml_block,
    _render_codex_agent_toml,
)


def test_stage_creates_agentic_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()

    manager.stage(workspace)

    manifest_path = workspace / ".dadaia" / "agentic" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1"
    assert any(asset["path"] == "data/AGENTS.md" for asset in manifest["assets"])


def test_stage_copies_codex_runtime_adapters(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()

    manager.stage(workspace)

    assert (
        workspace / ".dadaia" / "agentic" / "runtime" / "codex" / "design-ctx" / "SKILL.md"
    ).exists()
    manifest = json.loads(
        (workspace / ".dadaia" / "agentic" / "manifest.json").read_text(encoding="utf-8")
    )
    assert any(asset["path"] == "runtime/codex/design-ctx/SKILL.md" for asset in manifest["assets"])


def test_install_all_projects_runtime_assets(tmp_path: Path) -> None:
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
    # T-18 / ADR-1/D2: behavioral prose rules must NOT be projected to .codex/rules/.
    # Only executable rules (those with YAML frontmatter) are projected.
    assert not (workspace / ".codex" / "rules" / "game-agents-coordination.md").exists()
    assert not (workspace / ".codex" / "rules" / "game-developer-scope.md").exists()
    # Executable rules with frontmatter ARE projected:
    assert (workspace / ".codex" / "rules" / "dadaia-workspace-dev-guardrail.md").exists()
    assert (workspace / ".codex" / "rules" / "plugin-scope.md").exists()
    assert (workspace / ".codex" / "rules" / "workspace-protocol.md").exists()
    assert (workspace / "opencode.json").exists()


def test_install_refuses_dadaia_workspace_source_root(tmp_path: Path) -> None:
    workspace = tmp_path / "dadaia-workspace"
    workspace.mkdir()
    (workspace / "dadaia_workspace" / "public").mkdir(parents=True)
    (workspace / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "dadaia-workspace"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )

    manager = FileSystemPublicAssetManager()

    with pytest.raises(PublicAssetError, match="Refusing to project public runtime assets"):
        manager.install(workspace, target="all")

    assert not (workspace / ".dadaia").exists()
    assert not (workspace / "opencode.json").exists()


def test_problematic_skill_files_have_frontmatter() -> None:
    public_dir = FileSystemPublicAssetManager()._public_dir  # noqa: SLF001
    skill_paths = [
        public_dir / "skills" / "ux-ui-review" / "SKILL.md",
        public_dir / "skills" / "design-report-quality-gate" / "SKILL.md",
        public_dir / "skills" / "frontend-implementation-quality" / "SKILL.md",
        public_dir / "skills" / "frontend-design" / "SKILL.md",
        public_dir / "skills" / "design-reference-research" / "SKILL.md",
        public_dir / "runtime" / "codex" / "design-ctx" / "SKILL.md",
        public_dir / "runtime" / "codex" / "frontend-ctx" / "SKILL.md",
    ]

    for skill_path in skill_paths:
        text = skill_path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{skill_path} must start with YAML frontmatter"
        assert "\n---\n" in text[4:], f"{skill_path} must close YAML frontmatter"
        frontmatter = text.split("\n---\n", 1)[0]
        assert "\nname: " in frontmatter
        assert "\ndescription: " in frontmatter


def test_install_preserves_existing_files_without_force(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    agents_md = workspace / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text("custom\n", encoding="utf-8")

    FileSystemPublicAssetManager().install(workspace, target="all")

    assert agents_md.read_text(encoding="utf-8") == "custom\n"


def test_install_overwrites_existing_files_with_force(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    agents_md = workspace / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text("custom\n", encoding="utf-8")

    FileSystemPublicAssetManager().install(workspace, target="all", force=True)

    content = agents_md.read_text(encoding="utf-8")
    assert content != "custom\n"  # force overwrote the placeholder
    assert "# dadaia-workspace" in content  # canonical content is present


def test_doctor_tracks_dadaia_scoped_agents_files(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()

    manager.stage(workspace)
    manager.install(workspace, target="all", force=True)

    clean_report = manager.doctor(workspace)
    assert "[ok] dadaia:AGENTS.md" in clean_report
    assert "[ok] dadaia:tmp/AGENTS.md" in clean_report
    assert "[ok] dadaia:states/AGENTS.md" in clean_report

    (workspace / ".dadaia" / "states" / "AGENTS.md").write_text("drift\n", encoding="utf-8")
    drift_report = manager.doctor(workspace)

    assert "[drift] dadaia:states/AGENTS.md" in drift_report


def test_public_privacy_gate_flags_private_identifiers(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    public_dir = repo_root / "dadaia_workspace" / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    # Use the first denylist term dynamically so the literal never appears in source.
    from dadaia_workspace.infrastructure.public_assets import (
        _PUBLIC_PRIVACY_DENYLIST,  # noqa: PLC0415
    )

    first_term, _ = _PUBLIC_PRIVACY_DENYLIST[0]
    (data_dir / "AGENTS.md").write_text(f"Private endpoint: {first_term}\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    report = manager._check_public_privacy()  # noqa: SLF001

    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any(first_term in line.lower() for line in report)


def test_public_privacy_gate_ignores_bytecode_cache(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    public_dir = repo_root / "dadaia_workspace" / "public"
    cache_dir = public_dir / "skills" / "sample" / "__pycache__"
    cache_dir.mkdir(parents=True)
    from dadaia_workspace.infrastructure.public_assets import (
        _PUBLIC_PRIVACY_DENYLIST,  # noqa: PLC0415
    )

    first_term, _ = _PUBLIC_PRIVACY_DENYLIST[0]
    (cache_dir / "leak.pyc").write_bytes(first_term.encode())
    (public_dir / "data").mkdir()
    (public_dir / "data" / "AGENTS.md").write_text("# clean\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    assert manager._check_public_privacy() == ["[ok] public-privacy"]  # noqa: SLF001


_CLASSIFY_WORKFLOWS_CASES = [
    {
        "id": "codex_linear",
        "content": "# linear workflow\nstep: do_something\n",
        "expected_in": [
            "[reference-only] codex:workflows/sample.workflow.md (installed, no workflow executor)"
        ],
        "expected_not_in": ["[partial] opencode:workflows/sample.workflow.md"],
    },
    {
        "id": "codex_parallel",
        "content": "# parallel workflow\nparallel_group: batch_a\nstep: do_something\n",
        "expected_in": [
            "[reference-only] codex:workflows/sample.workflow.md (installed, no workflow executor)"
        ],
        "expected_not_in": ["[ok] opencode:workflows/sample.workflow.md"],
    },
    {
        "id": "opencode_linear",
        "content": "# linear workflow\nstep: do_something\n",
        "expected_in": ["[ok] opencode:workflows/sample.workflow.md"],
        "expected_not_in": ["[partial] opencode:workflows/sample.workflow.md"],
    },
    {
        "id": "opencode_parallel",
        "content": "# parallel workflow\nparallel_group: batch_a\nstep: do_something\n",
        "expected_in": [
            "[partial] opencode:workflows/sample.workflow.md (parallel_group sequentially)"
        ],
        "expected_not_in": ["[ok] opencode:workflows/sample.workflow.md"],
    },
]


@pytest.mark.parametrize(
    "case", _CLASSIFY_WORKFLOWS_CASES, ids=[str(c["id"]) for c in _CLASSIFY_WORKFLOWS_CASES]
)
def test_classify_workflows_quadrants(tmp_path: Path, case: dict) -> None:  # type: ignore[type-arg]
    agentic_dir = tmp_path / "agentic"
    workflows_dir = agentic_dir / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "sample.workflow.md").write_text(case["content"], encoding="utf-8")

    result = FileSystemPublicAssetManager()._classify_workflows(agentic_dir)  # noqa: SLF001

    for expected in case["expected_in"]:
        assert expected in result, f"Expected {expected!r} in result; got {result}"
    for not_expected in case["expected_not_in"]:
        assert not_expected not in result, (
            f"Did not expect {not_expected!r} in result; got {result}"
        )


# ---------------------------------------------------------------------------
# T-MPP-2.9 — T-PB-1 happy-path unit tests (#1..#6)
# ---------------------------------------------------------------------------

_PARSE_FM_SIMPLE_CASES = [
    {
        "id": "name_and_model",
        "text": "---\nname: my-agent\nmodel: claude-3\n---\n# body\n",
        "expected": {"name": "my-agent", "model": "claude-3"},
    },
    {
        "id": "description_scalar",
        "text": "---\nname: helper\ndescription: Does stuff\n---\n",
        "expected": {"name": "helper", "description": "Does stuff"},
    },
]


@pytest.mark.parametrize(
    "case", _PARSE_FM_SIMPLE_CASES, ids=[c["id"] for c in _PARSE_FM_SIMPLE_CASES]
)
def test_parse_agent_frontmatter_extracts_whitelisted_fields(case: dict) -> None:  # type: ignore[type-arg]
    """T-PB-1 #1 — basic key:value parsing."""
    result = _parse_agent_frontmatter(case["text"])
    for key, val in case["expected"].items():
        assert result[key] == val, f"Key {key!r}: expected {val!r}, got {result.get(key)!r}"


def test_render_agent_toml_block_quotes_hyphenated_name() -> None:
    """T-PB-1 #2 — hyphenated name is double-quoted in TOML header."""
    fm: dict[str, object] = {"name": "software-engineer", "model": "claude-sonnet-4-6"}
    result = _render_agent_toml_block("software-engineer", fm)
    assert result.startswith('[agents."software-engineer"]\n'), (
        f"Expected quoted header, got: {result!r}"
    )


def test_render_agent_toml_block_emits_triple_quoted_description() -> None:
    """T-PB-1 #3 — multi-line description (folded YAML >) → TOML triple-quoted string."""
    description = "Implements tasks for Python services\nand Node.js tooling."
    fm: dict[str, object] = {"name": "dev", "description": description}
    result = _render_agent_toml_block("dev", fm)
    # Multi-line value must be wrapped in triple-quotes
    assert '"""' in result, f"Expected triple-quoted description in: {result!r}"
    assert description.split("\n")[0] in result


def test_render_agent_toml_block_drops_unknown_fields() -> None:
    """T-PB-1 #4 — fields outside _TOML_SAFE_AGENT_FIELDS are dropped."""
    fm: dict[str, object] = {
        "name": "dev",
        "model": "claude-3",
        "skills": ["dadaia-handoff-emitter"],  # unknown field — must be dropped
        "opencode_model": "claude-haiku",  # unknown field — must be dropped
    }
    result = _render_agent_toml_block("dev", fm)
    assert "skills" not in result
    assert "opencode_model" not in result
    assert "claude-3" in result  # whitelisted field present


def test_render_agent_toml_block_drops_missing_name() -> None:
    """T-PB-1 #5 — _parse_agent_frontmatter returns {} when name is absent."""
    text = "---\nmodel: claude-3\ndescription: No name here\n---\n"
    result = _parse_agent_frontmatter(text)
    assert result == {}, f"Expected empty dict when name missing, got: {result!r}"


def test_render_agent_toml_block_emits_tools_array_literal() -> None:
    """T-PB-1 #6 — tools list → TOML array of quoted strings."""
    fm: dict[str, object] = {"name": "dev", "tools": ["Read", "Edit", "Bash"]}
    result = _render_agent_toml_block("dev", fm)
    assert 'tools = ["Read", "Edit", "Bash"]' in result, f"Expected tools array in: {result!r}"


def test_render_codex_agent_toml_emits_description() -> None:
    result = _render_codex_agent_toml(
        "ai-engineer",
        "gpt-5.3-codex",
        "Follow the Codex persona.",
        description="AI entity authoring agent.",
    )

    parsed = tomllib.loads(result)
    assert parsed["name"] == "ai-engineer"
    assert parsed["description"] == "AI entity authoring agent."
    assert parsed["model"] == "gpt-5.3-codex"
    assert parsed["developer_instructions"].strip() == "Follow the Codex persona."


# ---------------------------------------------------------------------------
# T-MPP-2.10 — T-PB-1 adversarial unit tests (#7, #8)
# ---------------------------------------------------------------------------


def test_render_agent_toml_block_escapes_quote_in_name() -> None:
    """T-PB-1 #7 — adversarial: names with double-quote escape correctly; ] raises.

    Defensive coding floor: even though agent names are lib-controlled (Q1), the
    escape path must round-trip correctly for names containing special characters.
    """
    # Part A: name containing double-quote — must escape and round-trip
    name_with_quote = 'my"agent'
    fm: dict[str, object] = {"name": name_with_quote, "description": "x"}
    rendered = _render_agent_toml_block(name_with_quote, fm)
    parsed = tomllib.loads(rendered)
    extracted_name = next(iter(parsed["agents"]))
    assert extracted_name == name_with_quote, (
        f"Round-trip name mismatch: expected {name_with_quote!r}, got {extracted_name!r}"
    )

    # Part B: name containing ] must raise ValueError
    with pytest.raises(ValueError, match=r"\]"):
        _render_agent_toml_block("bad]name", {"name": "bad]name"})

    # Part C: name containing newline must raise ValueError
    with pytest.raises(ValueError, match="newline"):
        _render_agent_toml_block("bad\nname", {"name": "bad\nname"})


def test_render_agent_toml_block_escapes_triple_quote_in_description() -> None:
    """T-PB-1 #8 — adversarial: triple-quote in description must round-trip.

    _toml_escape() uses triple-quoted TOML strings for multi-line values.
    An embedded triple-quote must be escaped so the round-trip preserves
    the original description bytes.
    """
    description_with_triple_quote = 'first line\nsecond with """embedded""" quotes\nthird'
    fm: dict[str, object] = {"name": "agent-x", "description": description_with_triple_quote}
    rendered = _render_agent_toml_block("agent-x", fm)
    parsed = tomllib.loads(rendered)
    extracted_description = parsed["agents"]["agent-x"]["description"]
    assert extracted_description == description_with_triple_quote, (
        f"Round-trip description mismatch:\n"
        f"  expected: {description_with_triple_quote!r}\n"
        f"  got:      {extracted_description!r}"
    )


# ---------------------------------------------------------------------------
# T-MPP-2.11 — T-PB-4 unit tests (#1, #2) for [skills] table emission
# ---------------------------------------------------------------------------

# Use a non-existent path so _render_agents_into_codex_config returns "" (no agent
# blocks). The [skills] table must still be emitted unconditionally.
_NONEXISTENT_AGENTIC_DIR = Path("/nonexistent/agentic")

_SKILLS_TABLE_CASES = [
    {
        "id": "emits_skills_table",
        "agentic_dir": _NONEXISTENT_AGENTIC_DIR,
    },
    {
        "id": "skills_appears_after_agents",
        # Use the real public/ dir so that [agents.*] blocks ARE present.
        # FileSystemPublicAssetManager._public_dir points to dadaia_workspace/public/.
        "agentic_dir": FileSystemPublicAssetManager()._public_dir,  # noqa: SLF001
    },
]


@pytest.mark.parametrize("case", _SKILLS_TABLE_CASES, ids=[c["id"] for c in _SKILLS_TABLE_CASES])
def test_codex_config_emits_skills_table(case: dict) -> None:  # type: ignore[type-arg]
    """T-PB-4 #1 — _codex_config() always emits a [skills] section."""
    manager = FileSystemPublicAssetManager()
    output = manager._codex_config(case["agentic_dir"])  # noqa: SLF001
    assert "[skills]" in output, f"Expected '[skills]' in output; got:\n{output}"
    assert 'paths = [".agents/skills", ".codex/skills"]' in output, (
        f"Expected shared and Codex-only skill roots in output; got:\n{output}"
    )


@pytest.mark.parametrize("case", _SKILLS_TABLE_CASES[1:], ids=["skills_appears_after_agents"])
def test_codex_config_skills_paths_array_ordering(case: dict) -> None:  # type: ignore[type-arg]
    """T-PB-4 #2 — [skills] table appears AFTER the [agents.*] tables."""
    manager = FileSystemPublicAssetManager()
    output = manager._codex_config(case["agentic_dir"])  # noqa: SLF001

    assert "[skills]" in output, "Expected '[skills]' in output"
    assert "[agents." in output, "Expected at least one [agents.*] block in output"

    agents_offset = output.find("[agents.")
    skills_offset = output.find("[skills]")
    assert agents_offset < skills_offset, (
        f"Expected [agents.*] (offset {agents_offset}) to appear before "
        f"[skills] (offset {skills_offset}) in output"
    )


# ---------------------------------------------------------------------------
# T-MPP-3.4 — T-PB-2 base unit tests (#1, #2)
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


_MINIMAL_WORKFLOW_CROSS_CUTTING = """\
---
name: cross-cutting-feature
description: "Minimal test workflow."
version: 0.1.0
schema_version: "1"
stages:
  - id: step1
    agent: product-engineer
    expected_output:
      path: specs/releases/X/SPEC.md
---
# cross-cutting-feature workflow body
"""

_MINIMAL_WORKFLOW_HOTFIX = """\
---
name: hotfix-release
description: "Minimal test workflow."
version: 0.1.0
schema_version: "1"
stages:
  - id: step1
    agent: product-engineer
    expected_output:
      path: specs/releases/X/SPEC.md
---
# hotfix-release workflow body
"""


def test_install_codex_projects_workflows_dir(tmp_path: Path) -> None:
    """T-16 — _install_codex() projects canonical workflows to .codex/workflows/.

    FR9/ADR-4: the old behavior of removing .codex/workflows/ is replaced by
    projecting the canonical workflows from the agentic directory.
    """
    manager, workspace_root = _make_codex_install_manager(tmp_path)

    # Add a canonical workflow to the public/workflows dir (must be schema-valid)
    public_dir = manager._public_dir  # noqa: SLF001
    workflows_src = public_dir / "workflows"
    workflows_src.mkdir(parents=True)
    (workflows_src / "cross-cutting-feature.workflow.md").write_text(
        _MINIMAL_WORKFLOW_CROSS_CUTTING, encoding="utf-8"
    )

    manager.install(workspace_root, target="codex", force=True)

    workflows_dir = workspace_root / ".codex" / "workflows"
    assert workflows_dir.exists(), ".codex/workflows/ should exist after install"
    assert (workflows_dir / "cross-cutting-feature.workflow.md").exists(), (
        "Canonical workflow should be projected to .codex/workflows/"
    )


def test_install_codex_overwrites_legacy_workflow_file(tmp_path: Path) -> None:
    """T-16 addendum — a pre-existing workflow file is overwritten by the canonical source."""
    manager, workspace_root = _make_codex_install_manager(tmp_path)

    # Pre-create a legacy workflows dir with stale content
    workflows_dir = workspace_root / ".codex" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "hotfix-release.workflow.md").write_text("stale content\n", encoding="utf-8")

    # Add the canonical workflow (must be schema-valid)
    public_dir = manager._public_dir  # noqa: SLF001
    workflows_src = public_dir / "workflows"
    workflows_src.mkdir(parents=True)
    (workflows_src / "hotfix-release.workflow.md").write_text(
        _MINIMAL_WORKFLOW_HOTFIX, encoding="utf-8"
    )

    manager.install(workspace_root, target="codex", force=True)

    # The canonical workflow content was projected (force=True overwrites)
    assert (workflows_dir / "hotfix-release.workflow.md").read_text(
        encoding="utf-8"
    ) == _MINIMAL_WORKFLOW_HOTFIX


# ---------------------------------------------------------------------------
# T-18 — behavioral rules are NOT projected to .codex/rules/
# ---------------------------------------------------------------------------


def test_install_codex_skips_behavioral_rules(tmp_path: Path) -> None:
    """T-18 / ADR-1/D2 — behavioral prose rules (no frontmatter) are excluded from .codex/rules/."""
    manager, workspace_root = _make_codex_install_manager(tmp_path)

    public_dir = manager._public_dir  # noqa: SLF001
    rules_src = public_dir / "rules"
    # Behavioral rule (no frontmatter)
    (rules_src / "game-agents-coordination.md").write_text(
        "# game-agents-coordination\nProse rule\n", encoding="utf-8"
    )
    # Executable rule (has frontmatter)
    (rules_src / "workspace-protocol.md").write_text(
        "---\nname: workspace-protocol\n---\n# body\n", encoding="utf-8"
    )

    manager.install(workspace_root, target="codex", force=True)

    rules_dst = workspace_root / ".codex" / "rules"
    assert not (rules_dst / "game-agents-coordination.md").exists(), (
        "Behavioral rule should NOT be projected to .codex/rules/"
    )
    assert (rules_dst / "workspace-protocol.md").exists(), (
        "Executable rule (with frontmatter) SHOULD be projected to .codex/rules/"
    )
