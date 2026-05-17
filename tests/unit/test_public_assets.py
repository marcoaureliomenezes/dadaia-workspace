"""Unit tests for public asset staging and runtime projections."""

import json
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    _parse_agent_frontmatter,
    _render_agent_toml_block,
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


def test_install_all_projects_runtime_assets(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()

    manager.install(workspace, target="all")

    assert (workspace / "AGENTS.md").exists()
    assert (workspace / ".agents" / "skills" / "dadaia-grill-me" / "SKILL.md").exists()
    assert (workspace / ".claude" / "agents" / "software-architect.md").exists()
    assert (workspace / ".codex" / "hooks.json").exists()
    assert (workspace / ".codex" / "config.toml").exists()
    assert (workspace / ".codex" / "rules" / "dadaia-workspace-dev-guardrail.md").exists()
    assert (workspace / ".opencode" / "commands" / "spec-context.md").exists()
    assert (workspace / "opencode.json").exists()


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

    assert agents_md.read_text(encoding="utf-8").startswith("# dadaia Labs")


_CLASSIFY_WORKFLOWS_CASES = [
    {
        "id": "codex_linear",
        "content": "# linear workflow\nstep: do_something\n",
        "expected_in": ["[not-applicable] codex:workflows/sample.workflow.md (no workflow runtime)"],
        "expected_not_in": ["[partial] opencode:workflows/sample.workflow.md"],
    },
    {
        "id": "codex_parallel",
        "content": "# parallel workflow\nparallel_group: batch_a\nstep: do_something\n",
        "expected_in": ["[not-applicable] codex:workflows/sample.workflow.md (no workflow runtime)"],
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
        "expected_in": ["[partial] opencode:workflows/sample.workflow.md (parallel_group sequentially)"],
        "expected_not_in": ["[ok] opencode:workflows/sample.workflow.md"],
    },
]


@pytest.mark.parametrize("case", _CLASSIFY_WORKFLOWS_CASES, ids=[str(c["id"]) for c in _CLASSIFY_WORKFLOWS_CASES])
def test_classify_workflows_quadrants(tmp_path: Path, case: dict) -> None:  # type: ignore[type-arg]
    agentic_dir = tmp_path / "agentic"
    workflows_dir = agentic_dir / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "sample.workflow.md").write_text(case["content"], encoding="utf-8")

    result = FileSystemPublicAssetManager()._classify_workflows(agentic_dir)  # noqa: SLF001

    for expected in case["expected_in"]:
        assert expected in result, f"Expected {expected!r} in result; got {result}"
    for not_expected in case["expected_not_in"]:
        assert not_expected not in result, f"Did not expect {not_expected!r} in result; got {result}"


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


@pytest.mark.parametrize("case", _PARSE_FM_SIMPLE_CASES, ids=[c["id"] for c in _PARSE_FM_SIMPLE_CASES])
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
        "opencode_model": "claude-haiku",       # unknown field — must be dropped
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
    assert 'tools = ["Read", "Edit", "Bash"]' in result, (
        f"Expected tools array in: {result!r}"
    )
