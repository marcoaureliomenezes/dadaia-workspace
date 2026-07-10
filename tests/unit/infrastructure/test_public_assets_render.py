"""Pure rendering primitives extracted from ``public_assets`` (T-2, v0.1.75 split of
``test_public_assets.py`` by concern — 1/4: render).

Covers: sha256/package-version/json-dump helpers, TOML string escaping, per-agent TOML
block + codex-agent TOML rendering (incl. the reasoning-effort tier map), agent
frontmatter parsing, the two codex-config rendering helpers, and the
``_agents_md_source`` data/templates precedence. No filesystem beyond tmp_path
fixtures.
"""

from __future__ import annotations

import hashlib
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    _json_dump,
    _package_version,
    _parse_agent_frontmatter,
    _render_agent_toml_block,
    _render_agents_config_file_blocks,
    _render_agents_into_codex_config,
    _render_codex_agent_toml,
    _sha256,
    _toml_escape,
)


def _make_agent_md(
    name: str, model: str = "claude-sonnet-4-6", tools: list[str] | None = None
) -> str:
    """Build a minimal agent .md file with YAML frontmatter."""
    tools_block = ""
    if tools:
        items = "\n".join(f"  - {t}" for t in tools)
        tools_block = f"tools:\n{items}\n"
    return f"---\nname: {name}\nmodel: {model}\n{tools_block}---\n# Body of {name}\n"


def _build_minimal_agentic_dir(tmp_path: Path) -> tuple[Path, Path]:
    """Build a minimal agentic_dir + workspace_root usable for doctor/install tests."""
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    agentic_dir = workspace_root / ".dadaia" / "agentic"
    agentic_dir.mkdir(parents=True)
    return agentic_dir, workspace_root


def test_sha256_package_version_and_json_dump_helpers(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_bytes(b"hello world")
    assert _sha256(f) == hashlib.sha256(b"hello world").hexdigest()

    # > 1 MB chunk size — exercises chunked reading.
    big_data = b"X" * (2 * 1024 * 1024 + 7)
    big = tmp_path / "big.bin"
    big.write_bytes(big_data)
    assert _sha256(big) == hashlib.sha256(big_data).hexdigest()

    with patch(
        "dadaia_workspace.infrastructure.public_assets_common.version",
        side_effect=PackageNotFoundError,
    ):
        assert _package_version() == "editable"

    out = _json_dump({"b": 1, "a": 2})
    assert out.index('"a"') < out.index('"b"')
    assert out.endswith("\n")
    assert "\n  " in out


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("hello", '"hello"', id="single-line"),
        pytest.param('say "hi"', '"say \\"hi\\""', id="embedded-quotes"),
        pytest.param("a\\b", '"a\\\\b"', id="backslash"),
    ],
)
def test_toml_escape_single_line(raw: str, expected: str) -> None:
    assert _toml_escape(raw) == expected

    if raw == "hello":  # run the multiline assertions once, piggy-backing this param
        result = _toml_escape("line1\nline2")
        assert result.startswith('"""')
        assert result.endswith('"""')
        assert "line1" in result
        assert "line2" in result

        escaped = _toml_escape('has """here')
        assert '"""here' not in escaped or escaped.startswith('"""')


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            "---\nname: my-agent\nmodel: claude-sonnet-4-6\n---\n# body\n",
            {"name": "my-agent", "model": "claude-sonnet-4-6"},
            id="simple-fields",
        ),
        pytest.param(
            "---\nname: agent\ntools:\n  - Read\n  - Write\n---\n",
            {"tools": ["Read", "Write"]},
            id="tools-list",
        ),
        pytest.param("---\nmodel: claude-sonnet-4-6\n---\n", {}, id="missing-name-empty"),
        pytest.param("just some body\n", {}, id="no-frontmatter"),
        pytest.param("---\nname: x\n", {}, id="unterminated-frontmatter"),
    ],
)
def test_parse_agent_frontmatter(text: str, expected: dict[str, object]) -> None:
    fm = _parse_agent_frontmatter(text)
    for key, value in expected.items():
        assert fm.get(key) == value
    if expected == {}:
        assert fm == {}

    dropped = _parse_agent_frontmatter("---\nname: a\nunknown_field: value\n---\n")
    assert "unknown_field" not in dropped
    assert dropped["name"] == "a"

    folded = _parse_agent_frontmatter("---\nname: a\ndescription: >\n  line one\n  line two\n---\n")
    assert "line one" in str(folded.get("description", ""))


@pytest.mark.parametrize(
    ("model", "claude_model", "expected_effort"),
    [
        pytest.param("gpt-5.5", "claude-fable-5", "high", id="deep-tier-is-high"),
        pytest.param("gpt-5.5", "claude-opus-4-8", "medium", id="dispatch-tier-is-medium"),
        pytest.param(
            "gpt-5.4-mini", "claude-haiku-4-5-20251001", "medium", id="fast-tier-is-medium"
        ),
        pytest.param("m", "claude-not-in-registry", "medium", id="unknown-model-defaults-medium"),
        pytest.param("m", None, "medium", id="no-claude-model-defaults-medium"),
    ],
)
def test_render_codex_agent_toml_fields_escaping_and_reasoning_effort_tiers(
    model: str, claude_model: str | None, expected_effort: str
) -> None:
    """Field rendering + escaping (checked once via the first param's fixed body)
    plus T-013-12's reasoning-effort tier map (deep→high, dispatch/fast/unknown→
    medium), which derives from the claude model's registry tier."""
    kwargs = {"claude_model": claude_model} if claude_model is not None else {}
    out = _render_codex_agent_toml("x", model, "body", **kwargs)  # type: ignore[arg-type]
    assert f'model_reasoning_effort = "{expected_effort}"' in out

    if claude_model == "claude-fable-5":  # run the field/escaping asserts once
        fields_out = _render_codex_agent_toml("my-agent", "gpt-4o", "You are helpful.")
        assert 'name = "my-agent"' in fields_out
        assert 'model = "gpt-4o"' in fields_out
        assert "developer_instructions" in fields_out
        assert "You are helpful." in fields_out

        backslash_out = _render_codex_agent_toml("a", "m", "path\\to\\file")
        assert "path\\\\to\\\\file" in backslash_out

        triple_out = _render_codex_agent_toml("a", "m", 'has """here')
        assert (
            '"""here'
            not in triple_out.split("developer_instructions", 1)[1].strip().lstrip('= \n"')[:-3]
        )

        # _render_agent_toml_block (the per-agent TOML block, distinct from the
        # codex-agent full-file render exercised above) shares this param slot.
        fm = {"name": "my-agent", "model": "gpt-4o", "description": "Does stuff"}
        block_out = _render_agent_toml_block("my-agent", fm)
        assert '[agents."my-agent"]' in block_out
        assert 'name = "my-agent"' in block_out
        assert 'model = "gpt-4o"' in block_out
        assert 'description = "Does stuff"' in block_out

        tools_out = _render_agent_toml_block("a", {"name": "a", "tools": ["Read", "Write"]})
        assert "tools = " in tools_out
        assert '"Read"' in tools_out
        assert '"Write"' in tools_out

        minimal_out = _render_agent_toml_block("minimal", {"name": "minimal"})
        assert "model" not in minimal_out
        assert "description" not in minimal_out

        for bad_name, message in [("bad]name", "invalid character"), ("bad\nname", "newline")]:
            with pytest.raises(ValueError, match=message):
                _render_agent_toml_block(bad_name, {"name": bad_name})


def test_render_agents_into_codex_config_and_config_file_blocks(tmp_path: Path) -> None:
    """Both codex-config rendering helpers share the same shape contract: empty for
    a nonexistent/empty/noname-only source dir, non-empty and agent-named
    otherwise. Exercised together since both fns are driven by the same source
    agents dir."""
    assert _render_agents_into_codex_config(Path("/nonexistent-dir-xyz")) == ""
    assert _render_agents_config_file_blocks(tmp_path / "missing") == ""

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    assert _render_agents_into_codex_config(agents_dir) == ""

    (agents_dir / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
    result = _render_agents_into_codex_config(agents_dir)
    assert "my-agent" in result

    blocks_result = _render_agents_config_file_blocks(agents_dir)
    assert '[agents."my-agent"]' in blocks_result
    assert 'config_file = "agents/my-agent.toml"' in blocks_result

    noname_only_dir = tmp_path / "noname-only"
    noname_only_dir.mkdir()
    (noname_only_dir / "noname.md").write_text("---\nmodel: x\n---\n", encoding="utf-8")
    assert _render_agents_into_codex_config(noname_only_dir) == ""
    assert _render_agents_config_file_blocks(noname_only_dir) == ""


def test_agents_md_source_precedence(tmp_path: Path) -> None:
    """templates/AGENTS.md wins when both exist; data/AGENTS.md is the sole source
    when templates is absent; absent of both yields None."""
    agentic_dir, _ = _build_minimal_agentic_dir(tmp_path)
    manager = FileSystemPublicAssetManager()
    assert manager._agents_md_source(agentic_dir) is None

    data_dir = agentic_dir / "data"
    data_dir.mkdir()
    (data_dir / "AGENTS.md").write_text("# DATA\n", encoding="utf-8")
    data_src = manager._agents_md_source(agentic_dir)
    assert data_src is not None
    assert "data" in str(data_src)

    templates_dir = agentic_dir / "templates"
    templates_dir.mkdir()
    (templates_dir / "AGENTS.md").write_text("# TEMPLATES\n", encoding="utf-8")
    templates_src = manager._agents_md_source(agentic_dir)
    assert templates_src is not None
    assert "templates" in str(templates_src)
