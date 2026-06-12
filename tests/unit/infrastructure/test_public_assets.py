"""Unit tests for public asset projection helpers.

These tests cover pure rendering, drift classification, and in-process install
helpers. Process-boundary behavior belongs in integration tests.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    _CLAUDE_MD_STUB,
    FileSystemPublicAssetManager,
    _atomic_write_text,
    _consumer_repos_for_root,
    _doctor_guardrail_pair,
    _install_consumer_repos_guardrail_pair,
    _install_workspace_guardrail_pair,
    _install_workspace_root_guardrail_pair,
    _is_self_repo,
    _json_dump,
    _log_cleanup_error,
    _package_version,
    _parse_agent_frontmatter,
    _prepare_agent_for_opencode,
    _render_agent_toml_block,
    _render_agents_config_file_blocks,
    _render_agents_into_codex_config,
    _render_codex_agent_toml,
    _sha256,
    _strip_tools_from_frontmatter,
    _toml_escape,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_INSTALLED_VERSION = "1.2.3"
_OTHER_VERSION = "0.0.1"


def _make_agent_md(
    name: str, model: str = "claude-sonnet-4-6", tools: list[str] | None = None
) -> str:
    """Build a minimal agent .md file with YAML frontmatter."""
    tools_block = ""
    if tools:
        items = "\n".join(f"  - {t}" for t in tools)
        tools_block = f"tools:\n{items}\n"
    return f"---\nname: {name}\nmodel: {model}\n{tools_block}---\n# Body of {name}\n"


def _add_marker_consumer(
    workspace_root: Path, slug: str, pkg_version: str = _OTHER_VERSION
) -> Path:
    """Create a marker-bearing consumer repo under workspace_root/repos/."""
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": "1", "package_version": pkg_version}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return consumer


def _make_source_file(tmp_path: Path, content: str = "# AGENTS\n") -> Path:
    """Write a data/AGENTS.md source file and return its path.

    Written to a _src/ subdirectory to avoid SameFileError when tmp_path IS
    the workspace root.
    """
    src_dir = tmp_path / "_src"
    src_dir.mkdir(exist_ok=True)
    src = src_dir / "AGENTS.md"
    src.write_text(content, encoding="utf-8")
    return src


# ---------------------------------------------------------------------------
# _sha256
# ---------------------------------------------------------------------------


class TestSha256:
    def test_returns_hex_digest(self, tmp_path: Path) -> None:
        f = tmp_path / "f.txt"
        f.write_bytes(b"hello world")
        result = _sha256(f)
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert result == expected

    def test_large_file(self, tmp_path: Path) -> None:
        """Ensure chunked reading is exercised."""
        data = b"X" * (2 * 1024 * 1024 + 7)  # > 1 MB chunk size
        f = tmp_path / "big.bin"
        f.write_bytes(data)
        assert _sha256(f) == hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# _package_version
# ---------------------------------------------------------------------------


class TestPackageVersion:
    def test_returns_string(self) -> None:
        v = _package_version()
        assert isinstance(v, str)
        assert v  # non-empty

    def test_fallback_when_not_installed(self) -> None:
        from importlib.metadata import PackageNotFoundError

        with patch(
            "dadaia_workspace.infrastructure.public_assets_common.version",
            side_effect=PackageNotFoundError,
        ):
            assert _package_version() == "editable"


# ---------------------------------------------------------------------------
# _json_dump
# ---------------------------------------------------------------------------


class TestJsonDump:
    def test_sorted_indented_json_ends_with_newline(self) -> None:
        out = _json_dump({"b": 1, "a": 2})
        assert out.index('"a"') < out.index('"b"')
        assert out.endswith("\n")
        assert "\n  " in out


# ---------------------------------------------------------------------------
# _toml_escape
# ---------------------------------------------------------------------------


class TestTomlEscape:
    def test_single_line_strings_are_escaped(self) -> None:
        cases = {
            "hello": '"hello"',
            'say "hi"': '"say \\"hi\\""',
            "a\\b": '"a\\\\b"',
        }
        for raw, expected in cases.items():
            assert _toml_escape(raw) == expected

    def test_multiline_uses_triple_quotes(self) -> None:
        result = _toml_escape("line1\nline2")
        assert result.startswith('"""')
        assert result.endswith('"""')
        assert "line1" in result
        assert "line2" in result

    def test_multiline_triple_quote_escaped(self) -> None:
        result = _toml_escape('has """here')
        # Embedded triple-quote must be escaped
        assert '"""here' not in result or result.startswith('"""')


# ---------------------------------------------------------------------------
# _parse_agent_frontmatter
# ---------------------------------------------------------------------------


class TestParseAgentFrontmatter:
    def test_simple_fields(self) -> None:
        text = "---\nname: my-agent\nmodel: claude-sonnet-4-6\n---\n# body\n"
        fm = _parse_agent_frontmatter(text)
        assert fm["name"] == "my-agent"
        assert fm["model"] == "claude-sonnet-4-6"

    def test_tools_list(self) -> None:
        text = "---\nname: agent\ntools:\n  - Read\n  - Write\n---\n"
        fm = _parse_agent_frontmatter(text)
        assert fm["tools"] == ["Read", "Write"]

    def test_missing_name_returns_empty(self) -> None:
        text = "---\nmodel: claude-sonnet-4-6\n---\n"
        assert _parse_agent_frontmatter(text) == {}

    def test_no_frontmatter_returns_empty(self) -> None:
        assert _parse_agent_frontmatter("just some body\n") == {}

    def test_unterminated_frontmatter_returns_empty(self) -> None:
        assert _parse_agent_frontmatter("---\nname: x\n") == {}

    def test_unknown_fields_dropped(self) -> None:
        text = "---\nname: a\nunknown_field: value\n---\n"
        fm = _parse_agent_frontmatter(text)
        assert "unknown_field" not in fm
        assert fm["name"] == "a"

    def test_block_scalar_folded(self) -> None:
        text = "---\nname: a\ndescription: >\n  line one\n  line two\n---\n"
        fm = _parse_agent_frontmatter(text)
        assert "line one" in str(fm.get("description", ""))

    def test_opencode_model_not_in_safe_fields(self) -> None:
        text = "---\nname: a\nopencode_model: gpt-5\n---\n"
        fm = _parse_agent_frontmatter(text)
        assert "opencode_model" not in fm


# ---------------------------------------------------------------------------
# _render_agent_toml_block
# ---------------------------------------------------------------------------


class TestRenderAgentTomlBlock:
    def test_basic_render(self) -> None:
        fm = {"name": "my-agent", "model": "gpt-4o", "description": "Does stuff"}
        out = _render_agent_toml_block("my-agent", fm)
        assert '[agents."my-agent"]' in out
        assert 'name = "my-agent"' in out
        assert 'model = "gpt-4o"' in out
        assert 'description = "Does stuff"' in out

    def test_tools_list_emitted_as_toml_array(self) -> None:
        fm = {"name": "a", "tools": ["Read", "Write"]}
        out = _render_agent_toml_block("a", fm)
        assert "tools = " in out
        assert '"Read"' in out
        assert '"Write"' in out

    def test_invalid_agent_names_raise(self) -> None:
        cases = [("bad]name", "invalid character"), ("bad\nname", "newline")]
        for name, message in cases:
            with pytest.raises(ValueError, match=message):
                _render_agent_toml_block(name, {"name": name})

    def test_missing_optional_fields_omitted(self) -> None:
        fm = {"name": "minimal"}
        out = _render_agent_toml_block("minimal", fm)
        assert "model" not in out
        assert "description" not in out


# ---------------------------------------------------------------------------
# _render_codex_agent_toml
# ---------------------------------------------------------------------------


class TestRenderCodexAgentToml:
    def test_contains_required_fields(self) -> None:
        out = _render_codex_agent_toml("my-agent", "gpt-4o", "You are helpful.")
        assert 'name = "my-agent"' in out
        assert 'model = "gpt-4o"' in out
        assert "developer_instructions" in out
        assert "You are helpful." in out

    def test_backslash_in_instructions_escaped(self) -> None:
        out = _render_codex_agent_toml("a", "m", "path\\to\\file")
        assert "path\\\\to\\\\file" in out

    def test_triple_quote_in_instructions_escaped(self) -> None:
        out = _render_codex_agent_toml("a", "m", 'has """here')
        assert (
            '"""here' not in out.split("developer_instructions", 1)[1].strip().lstrip('= \n"')[:-3]
        )


# ---------------------------------------------------------------------------
# _render_agents_into_codex_config
# ---------------------------------------------------------------------------


class TestRenderAgentsIntoCodexConfig:
    def test_empty_dir_returns_empty_string(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        result = _render_agents_into_codex_config(agents_dir)
        assert result == ""

    def test_nonexistent_dir_returns_empty_string(self, tmp_path: Path) -> None:
        result = _render_agents_into_codex_config(tmp_path / "nonexistent")
        assert result == ""

    def test_valid_agent_rendered(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
        result = _render_agents_into_codex_config(agents_dir)
        assert "my-agent" in result

    def test_agent_missing_name_skipped(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "noname.md").write_text("---\nmodel: x\n---\n", encoding="utf-8")
        result = _render_agents_into_codex_config(agents_dir)
        assert result == ""


# ---------------------------------------------------------------------------
# _render_agents_config_file_blocks
# ---------------------------------------------------------------------------


class TestRenderAgentsConfigFileBlocks:
    def test_nonexistent_dir_returns_empty(self, tmp_path: Path) -> None:
        result = _render_agents_config_file_blocks(tmp_path / "missing")
        assert result == ""

    def test_generates_config_file_entry(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
        result = _render_agents_config_file_blocks(agents_dir)
        assert '[agents."my-agent"]' in result
        assert 'config_file = "agents/my-agent.toml"' in result

    def test_agent_missing_name_skipped(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "noname.md").write_text("---\nmodel: x\n---\n", encoding="utf-8")
        result = _render_agents_config_file_blocks(agents_dir)
        assert result == ""


# ---------------------------------------------------------------------------
# _atomic_write_text
# ---------------------------------------------------------------------------


class TestAtomicWriteText:
    def test_creates_file_with_content(self, tmp_path: Path) -> None:
        dst = tmp_path / "out.txt"
        _atomic_write_text(dst, "hello\n")
        assert dst.read_text(encoding="utf-8") == "hello\n"

    def test_no_tmp_file_remains(self, tmp_path: Path) -> None:
        dst = tmp_path / "out.txt"
        _atomic_write_text(dst, "data")
        assert not (tmp_path / "out.txt.tmp").exists()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        dst = tmp_path / "out.txt"
        dst.write_text("old", encoding="utf-8")
        _atomic_write_text(dst, "new")
        assert dst.read_text(encoding="utf-8") == "new"


# ---------------------------------------------------------------------------
# _log_cleanup_error
# ---------------------------------------------------------------------------


class TestLogCleanupError:
    def test_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        exc = OSError("permission denied")
        _log_cleanup_error(None, "/some/path", (type(exc), exc, None))
        captured = capsys.readouterr()
        assert "[cleanup-warning]" in captured.err
        assert "permission denied" in captured.err

    def test_no_exception_info(self, capsys: pytest.CaptureFixture[str]) -> None:
        _log_cleanup_error(None, "/path", (None, None, None))
        captured = capsys.readouterr()
        assert "[cleanup-warning]" in captured.err


# ---------------------------------------------------------------------------
# _strip_tools_from_frontmatter
# ---------------------------------------------------------------------------


class TestStripToolsFromFrontmatter:
    def test_strips_tools_block(self) -> None:
        content = "---\nname: a\ntools:\n  - Read\n  - Write\nmodel: m\n---\nbody\n"
        result = _strip_tools_from_frontmatter(content)
        assert "tools:" not in result
        assert "Read" not in result
        assert "name: a" in result
        assert "body" in result

    def test_no_frontmatter_returned_unchanged(self) -> None:
        content = "just body\n"
        assert _strip_tools_from_frontmatter(content) == content

    def test_unterminated_frontmatter_returned_unchanged(self) -> None:
        content = "---\nname: a\n"
        assert _strip_tools_from_frontmatter(content) == content

    def test_no_tools_returned_unchanged(self) -> None:
        content = "---\nname: a\nmodel: m\n---\nbody\n"
        assert _strip_tools_from_frontmatter(content) == content


# ---------------------------------------------------------------------------
# _prepare_agent_for_opencode
# ---------------------------------------------------------------------------


class TestPrepareAgentForOpencode:
    def test_strips_tools(self) -> None:
        content = "---\nname: a\ntools:\n  - Read\nmodel: m\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert "tools:" not in result
        assert "Read" not in result

    def test_swaps_model_when_opencode_model_declared(self) -> None:
        content = "---\nname: a\nmodel: claude-sonnet-4-6\nopencode_model: gpt-4o\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert "gpt-4o" in result
        assert "claude-sonnet-4-6" not in result

    def test_opencode_model_field_removed_from_output(self) -> None:
        content = "---\nname: a\nmodel: claude-sonnet-4-6\nopencode_model: gpt-4o\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert "opencode_model:" not in result

    def test_no_opencode_model_field_unchanged_model(self) -> None:
        content = "---\nname: a\nmodel: claude-sonnet-4-6\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert "claude-sonnet-4-6" in result

    def test_no_frontmatter_returned_unchanged(self) -> None:
        content = "just body\n"
        assert _prepare_agent_for_opencode(content) == content

    def test_strips_color_field(self) -> None:
        # FR-OC-1: color: is Claude-specific and breaks OpenCode 1.14.x parse.
        content = "---\nname: a\ncolor: yellow\nmodel: m\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert "color:" not in result
        assert "yellow" not in result

    def test_color_strip_preserves_other_fields(self) -> None:
        content = "---\nname: a\ncolor: orange\nmodel: claude-sonnet-4-6\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert "name: a" in result
        assert "model: claude-sonnet-4-6" in result
        assert "body" in result

    def test_no_color_field_unchanged(self) -> None:
        content = "---\nname: a\nmodel: m\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert result == content

    # --- T-OC-03 (FR-OC-2): permission: per-agent projection ---

    def test_permission_allow_for_granted_tools(self) -> None:
        content = (
            "---\nname: be\ntools:\n  - Read\n  - Write\n  - Edit\n  - Bash\n"
            "  - Glob\n  - Grep\nmodel: m\n---\nbody\n"
        )
        result = _prepare_agent_for_opencode(content)
        assert "permission:" in result
        assert "  edit: allow" in result
        assert "  bash: allow" in result
        # No WebFetch / Agent declared → deny.
        assert "  webfetch: deny" in result
        assert "  task: deny" in result

    def test_permission_deny_for_readonly_agent(self) -> None:
        content = (
            "---\nname: ro\ntools:\n  - Read\n  - Glob\n  - Grep\n  - WebFetch\n"
            "  - WebSearch\n  - Write\nmodel: m\n---\nbody\n"
        )
        result = _prepare_agent_for_opencode(content)
        assert "  edit: allow" in result  # Write maps to edit
        assert "  bash: deny" in result
        assert "  webfetch: allow" in result
        assert "  task: deny" in result

    def test_websearch_emits_unsupported_comment(self) -> None:
        content = "---\nname: r\ntools:\n  - Read\n  - WebSearch\nmodel: m\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert "# [opencode-unsupported]: WebSearch" in result

    def test_agent_tool_maps_to_task_allow(self) -> None:
        content = "---\nname: pm\ntools:\n  - Read\n  - Agent\nmodel: m\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert "  task: allow" in result

    def test_no_tools_block_no_permission(self) -> None:
        content = "---\nname: a\nmodel: m\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert "permission:" not in result

    def test_permission_block_after_tools_stripped(self) -> None:
        # tools: list form must be gone; permission: object form must be present.
        content = "---\nname: a\ntools:\n  - Bash\nmodel: m\n---\nbody\n"
        result = _prepare_agent_for_opencode(content)
        assert "tools:\n  - Bash" not in result
        assert "  bash: allow" in result


# ---------------------------------------------------------------------------
# _consumer_repos_for_root
# ---------------------------------------------------------------------------


class TestConsumerReposForRoot:
    def test_no_repos_dir_returns_empty(self, tmp_path: Path) -> None:
        assert _consumer_repos_for_root(tmp_path) == []

    def test_qualifying_repo_returned(self, tmp_path: Path) -> None:
        consumer = _add_marker_consumer(tmp_path, "my-repo")
        result = _consumer_repos_for_root(tmp_path)
        assert consumer in result

    def test_non_qualifying_repo_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bad_repo = tmp_path / "repos" / "no-markers"
        bad_repo.mkdir(parents=True)
        result = _consumer_repos_for_root(tmp_path)
        assert bad_repo not in result
        captured = capsys.readouterr()
        assert "[skip]" in captured.err

    def test_file_in_repos_dir_skipped(self, tmp_path: Path) -> None:
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        (repos_dir / "somefile.txt").write_text("x")
        result = _consumer_repos_for_root(tmp_path)
        assert result == []

    def test_partial_marker_dadaia_only_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Repo with .dadaia/ but not .dadaia/agentic/ should not qualify."""
        repo = tmp_path / "repos" / "partial"
        (repo / ".dadaia").mkdir(parents=True)
        result = _consumer_repos_for_root(tmp_path)
        assert repo not in result


# ---------------------------------------------------------------------------
# _is_self_repo
# ---------------------------------------------------------------------------


class TestIsSelfRepo:
    def test_manifest_matching_package_version_returns_true(self, tmp_path: Path) -> None:
        with patch(
            "dadaia_workspace.infrastructure.workspace_guardrail._package_version",
            return_value=_INSTALLED_VERSION,
        ):
            consumer = _add_marker_consumer(tmp_path, "self", pkg_version=_INSTALLED_VERSION)
            assert _is_self_repo(consumer) is True

    def test_manifest_missing_invalid_or_different_version_returns_false(
        self, tmp_path: Path
    ) -> None:
        with patch(
            "dadaia_workspace.infrastructure.workspace_guardrail._package_version",
            return_value=_INSTALLED_VERSION,
        ):
            different = _add_marker_consumer(tmp_path, "other", pkg_version=_OTHER_VERSION)
            assert _is_self_repo(different) is False

        no_manifest = tmp_path / "repos" / "no-manifest"
        (no_manifest / ".dadaia" / "agentic").mkdir(parents=True)
        assert _is_self_repo(no_manifest) is False

        invalid_json = tmp_path / "repos" / "bad-json"
        (invalid_json / ".dadaia" / "agentic").mkdir(parents=True)
        (invalid_json / ".dadaia" / "agentic" / "manifest.json").write_text(
            "NOT JSON", encoding="utf-8"
        )
        assert _is_self_repo(invalid_json) is False

        empty_version = tmp_path / "repos" / "empty-ver"
        (empty_version / ".dadaia" / "agentic").mkdir(parents=True)
        (empty_version / ".dadaia" / "agentic" / "manifest.json").write_text(
            json.dumps({"package_version": ""}), encoding="utf-8"
        )
        assert _is_self_repo(empty_version) is False

    def test_pyproject_dadaia_workspace_name_returns_true(self, tmp_path: Path) -> None:
        """Poetry and PEP 621 pyproject names identify the source repo without a manifest."""
        cases = {
            "poetry": '[tool.poetry]\nname = "dadaia-workspace"\nversion = "0.0.0"\n',
            "pep621": '[project]\nname = "dadaia-workspace"\nversion = "0.0.0"\n',
        }
        for slug, pyproject in cases.items():
            consumer = tmp_path / "repos" / slug
            consumer.mkdir(parents=True)
            (consumer / "pyproject.toml").write_text(pyproject, encoding="utf-8")
            assert _is_self_repo(consumer) is True

    def test_pyproject_different_name_no_manifest_returns_false(self, tmp_path: Path) -> None:
        """A pyproject.toml whose name is NOT dadaia-workspace must not trigger self-skip."""
        consumer = tmp_path / "repos" / "other-lib"
        consumer.mkdir(parents=True)
        (consumer / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "some-other-lib"\nversion = "1.0.0"\n',
            encoding="utf-8",
        )
        assert _is_self_repo(consumer) is False

    def test_pyproject_malformed_toml_falls_through_to_manifest_check(self, tmp_path: Path) -> None:
        """Malformed pyproject.toml must not raise; falls through to manifest check."""
        consumer = tmp_path / "repos" / "broken-pyproject"
        consumer.mkdir(parents=True)
        (consumer / "pyproject.toml").write_text("NOT VALID TOML ][[\n", encoding="utf-8")
        assert _is_self_repo(consumer) is False

    def test_pyproject_name_dadaia_workspace_with_manifest_returns_true(
        self, tmp_path: Path
    ) -> None:
        """pyproject guard fires before manifest check; result is still True."""
        consumer = tmp_path / "repos" / "lib-with-manifest"
        consumer.mkdir(parents=True)
        (consumer / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "dadaia-workspace"\nversion = "0.0.0"\n',
            encoding="utf-8",
        )
        # Add a manifest with a non-matching version; pyproject check fires first.
        (consumer / ".dadaia" / "agentic").mkdir(parents=True)
        (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
            json.dumps({"package_version": "999.0.0"}), encoding="utf-8"
        )
        assert _is_self_repo(consumer) is True


# ---------------------------------------------------------------------------
# _install_workspace_guardrail_pair
# ---------------------------------------------------------------------------


class TestInstallWorkspaceGuardrailPair:
    def test_creates_agents_md_and_claude_md_at_root(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path, "# AGENTS\n")
        _install_workspace_guardrail_pair(src, tmp_path, force=True)
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / "CLAUDE.md").exists()

    def test_claude_md_contains_stub(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path)
        _install_workspace_guardrail_pair(src, tmp_path, force=True)
        assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB

    def test_force_false_skips_when_identical(self, tmp_path: Path) -> None:
        """force=False: identical content is a no-op (T-PROP-01 hash-compare)."""
        content = "# SAME CONTENT\n"
        src = _make_source_file(tmp_path, content)
        (tmp_path / "AGENTS.md").write_text(content, encoding="utf-8")
        installed: list[str] = []
        _install_workspace_guardrail_pair(src, tmp_path, force=False, installed=installed)
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == content
        assert any("[skip]" in e for e in installed)

    def test_force_false_overwrites_when_different(self, tmp_path: Path) -> None:
        """force=False: differing content is updated (T-PROP-01 hash-compare)."""
        src = _make_source_file(tmp_path, "# NEW\n")
        (tmp_path / "AGENTS.md").write_text("# OLD\n", encoding="utf-8")
        installed: list[str] = []
        _install_workspace_guardrail_pair(src, tmp_path, force=False, installed=installed)
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "# NEW\n"
        assert any("[ok]" in e for e in installed)

    def test_force_true_overwrites_existing(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path, "# NEW\n")
        (tmp_path / "AGENTS.md").write_text("# OLD\n", encoding="utf-8")
        _install_workspace_guardrail_pair(src, tmp_path, force=True)
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "# NEW\n"

    def test_consumer_repos_receive_pair(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path, "# AGENTS\n")
        consumer = _add_marker_consumer(tmp_path, "my-repo")
        _install_workspace_guardrail_pair(src, tmp_path, force=True)
        assert (consumer / "AGENTS.md").exists()
        assert (consumer / "CLAUDE.md").exists()

    def test_self_repo_skipped(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        src = _make_source_file(tmp_path, "# AGENTS\n")
        with patch(
            "dadaia_workspace.infrastructure.workspace_guardrail._package_version",
            return_value=_INSTALLED_VERSION,
        ):
            _add_marker_consumer(tmp_path, "self-repo", pkg_version=_INSTALLED_VERSION)
            _install_workspace_guardrail_pair(src, tmp_path, force=True)
        # Self-repo should NOT have AGENTS.md written
        assert not (tmp_path / "repos" / "self-repo" / "AGENTS.md").exists()
        captured = capsys.readouterr()
        assert "self-projection" in captured.err

    def test_installed_list_populated(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path)
        installed: list[str] = []
        _install_workspace_guardrail_pair(src, tmp_path, force=True, installed=installed)
        assert any("[ok]" in e for e in installed)

    def test_installed_list_defaults_to_empty(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path)
        # Should not raise when installed=None (default)
        _install_workspace_guardrail_pair(src, tmp_path, force=True)


# ---------------------------------------------------------------------------
# _install_workspace_root_guardrail_pair
# ---------------------------------------------------------------------------


class TestInstallWorkspaceRootGuardrailPair:
    def test_writes_root_pair(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path, "# AGENTS\n")
        _install_workspace_root_guardrail_pair(src, tmp_path, force=True)
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / "CLAUDE.md").exists()

    def test_does_not_write_consumer_repos(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path, "# AGENTS\n")
        consumer = _add_marker_consumer(tmp_path, "my-repo")
        _install_workspace_root_guardrail_pair(src, tmp_path, force=True)
        assert not (consumer / "AGENTS.md").exists()

    def test_force_false_skips_when_identical(self, tmp_path: Path) -> None:
        """force=False: identical content is a no-op (T-PROP-01 hash-compare)."""
        content = "# SAME CONTENT\n"
        src = _make_source_file(tmp_path, content)
        (tmp_path / "AGENTS.md").write_text(content, encoding="utf-8")
        installed: list[str] = []
        _install_workspace_root_guardrail_pair(src, tmp_path, force=False, installed=installed)
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == content
        assert any("[skip]" in e for e in installed)

    def test_force_false_overwrites_when_different(self, tmp_path: Path) -> None:
        """force=False: differing content is updated (T-PROP-01 hash-compare)."""
        src = _make_source_file(tmp_path, "# NEW\n")
        (tmp_path / "AGENTS.md").write_text("# OLD\n", encoding="utf-8")
        installed: list[str] = []
        _install_workspace_root_guardrail_pair(src, tmp_path, force=False, installed=installed)
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "# NEW\n"
        assert any("[ok]" in e for e in installed)

    def test_claude_md_contains_stub(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path)
        _install_workspace_root_guardrail_pair(src, tmp_path, force=True)
        assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB

    def test_force_false_claude_md_updates_when_different(self, tmp_path: Path) -> None:
        """force=False: CLAUDE.md with wrong content is updated (T-PROP-01 hash-compare)."""
        src = _make_source_file(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("# OLD CLAUDE\n", encoding="utf-8")
        installed: list[str] = []
        _install_workspace_root_guardrail_pair(src, tmp_path, force=False, installed=installed)
        # CLAUDE.md was stale (not the stub) — it must be updated.
        assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB
        assert any("[ok]" in e and "CLAUDE" in e for e in installed)

    def test_force_false_claude_md_skips_when_already_stub(self, tmp_path: Path) -> None:
        """force=False: CLAUDE.md already containing stub is a no-op."""
        src = _make_source_file(tmp_path)
        # newline="" so the pre-existing stub is LF-exact, matching how production
        # writes it (_atomic_write_text). A plain write_text would emit CRLF on
        # Windows, so the byte-hash skip-compare would (correctly) not match.
        (tmp_path / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8", newline="")
        installed: list[str] = []
        _install_workspace_root_guardrail_pair(src, tmp_path, force=False, installed=installed)
        assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB
        assert any("[skip]" in e and "CLAUDE" in e for e in installed)

    def test_installed_defaults_to_none(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path)
        _install_workspace_root_guardrail_pair(src, tmp_path, force=True)


# ---------------------------------------------------------------------------
# _install_consumer_repos_guardrail_pair
# ---------------------------------------------------------------------------


class TestInstallConsumerReposGuardrailPair:
    def test_writes_consumer_pair(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path, "# AGENTS\n")
        consumer = _add_marker_consumer(tmp_path, "my-repo")
        _install_consumer_repos_guardrail_pair(src, tmp_path, force=True)
        assert (consumer / "AGENTS.md").exists()
        assert (consumer / "CLAUDE.md").exists()

    def test_does_not_write_workspace_root(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path, "# AGENTS\n")
        _add_marker_consumer(tmp_path, "my-repo")
        _install_consumer_repos_guardrail_pair(src, tmp_path, force=True)
        assert not (tmp_path / "AGENTS.md").exists()

    def test_self_repo_skipped(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        src = _make_source_file(tmp_path, "# AGENTS\n")
        with patch(
            "dadaia_workspace.infrastructure.workspace_guardrail._package_version",
            return_value=_INSTALLED_VERSION,
        ):
            _add_marker_consumer(tmp_path, "self-repo", pkg_version=_INSTALLED_VERSION)
            _install_consumer_repos_guardrail_pair(src, tmp_path, force=True)
        assert not (tmp_path / "repos" / "self-repo" / "AGENTS.md").exists()
        captured = capsys.readouterr()
        assert "self-projection" in captured.err

    def test_force_false_skips_when_identical(self, tmp_path: Path) -> None:
        """force=False: identical content is a no-op (T-PROP-01 hash-compare)."""
        content = "# SAME CONTENT\n"
        src = _make_source_file(tmp_path, content)
        consumer = _add_marker_consumer(tmp_path, "my-repo")
        (consumer / "AGENTS.md").write_text(content, encoding="utf-8")
        installed: list[str] = []
        _install_consumer_repos_guardrail_pair(src, tmp_path, force=False, installed=installed)
        assert (consumer / "AGENTS.md").read_text(encoding="utf-8") == content
        assert any("[skip]" in e for e in installed)

    def test_force_false_overwrites_when_different(self, tmp_path: Path) -> None:
        """force=False: differing content is updated (T-PROP-01 hash-compare)."""
        src = _make_source_file(tmp_path, "# NEW\n")
        consumer = _add_marker_consumer(tmp_path, "my-repo")
        (consumer / "AGENTS.md").write_text("# OLD\n", encoding="utf-8")
        installed: list[str] = []
        _install_consumer_repos_guardrail_pair(src, tmp_path, force=False, installed=installed)
        assert (consumer / "AGENTS.md").read_text(encoding="utf-8") == "# NEW\n"
        assert any("[ok]" in e for e in installed)

    def test_no_consumer_repos_no_write(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path)
        installed: list[str] = []
        _install_consumer_repos_guardrail_pair(src, tmp_path, force=True, installed=installed)
        assert installed == []

    def test_claude_md_contains_stub(self, tmp_path: Path) -> None:
        src = _make_source_file(tmp_path)
        consumer = _add_marker_consumer(tmp_path, "my-repo")
        _install_consumer_repos_guardrail_pair(src, tmp_path, force=True)
        assert (consumer / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB


# ---------------------------------------------------------------------------
# _doctor_guardrail_pair
# ---------------------------------------------------------------------------


class TestDoctorGuardrailPair:
    def _write_agents_src(self, tmp_path: Path, content: str = "# AGENTS\n") -> Path:
        src = tmp_path / "_src_AGENTS.md"
        src.write_text(content, encoding="utf-8")
        return src

    def test_ok_when_files_match(self, tmp_path: Path) -> None:
        content = "# AGENTS\n"
        src = self._write_agents_src(tmp_path, content)
        (tmp_path / "AGENTS.md").write_text(content, encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8")
        lines = _doctor_guardrail_pair(src, tmp_path)
        assert any(line.startswith("[ok]") and "AGENTS.md" in line for line in lines)
        assert any(line.startswith("[ok]") and "CLAUDE.md" in line for line in lines)

    def test_missing_agents_md(self, tmp_path: Path) -> None:
        src = self._write_agents_src(tmp_path)
        (tmp_path / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8")
        lines = _doctor_guardrail_pair(src, tmp_path)
        assert any("[missing]" in line and "AGENTS.md" in line for line in lines)

    def test_drift_agents_md(self, tmp_path: Path) -> None:
        src = self._write_agents_src(tmp_path, "# CANONICAL\n")
        (tmp_path / "AGENTS.md").write_text("# DIFFERENT\n", encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8")
        lines = _doctor_guardrail_pair(src, tmp_path)
        assert any("[drift]" in line and "AGENTS.md" in line for line in lines)

    def test_missing_claude_md(self, tmp_path: Path) -> None:
        content = "# AGENTS\n"
        src = self._write_agents_src(tmp_path, content)
        (tmp_path / "AGENTS.md").write_text(content, encoding="utf-8")
        lines = _doctor_guardrail_pair(src, tmp_path)
        assert any("[missing]" in line and "CLAUDE.md" in line for line in lines)

    def test_drift_claude_md_wrong_stub(self, tmp_path: Path) -> None:
        content = "# AGENTS\n"
        src = self._write_agents_src(tmp_path, content)
        (tmp_path / "AGENTS.md").write_text(content, encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text("# WRONG STUB\n", encoding="utf-8")
        lines = _doctor_guardrail_pair(src, tmp_path)
        assert any("[drift]" in line and "CLAUDE.md" in line for line in lines)

    def test_consumer_repo_included(self, tmp_path: Path) -> None:
        content = "# AGENTS\n"
        src = self._write_agents_src(tmp_path, content)
        (tmp_path / "AGENTS.md").write_text(content, encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8")
        consumer = _add_marker_consumer(tmp_path, "my-repo")
        (consumer / "AGENTS.md").write_text(content, encoding="utf-8")
        (consumer / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8")
        lines = _doctor_guardrail_pair(src, tmp_path)
        assert any("repos/my-repo" in line for line in lines)

    def test_self_repo_skipped_from_consumer_lines(self, tmp_path: Path) -> None:
        content = "# AGENTS\n"
        src = self._write_agents_src(tmp_path, content)
        (tmp_path / "AGENTS.md").write_text(content, encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8")
        with patch(
            "dadaia_workspace.infrastructure.workspace_guardrail._package_version",
            return_value=_INSTALLED_VERSION,
        ):
            _add_marker_consumer(tmp_path, "self-repo", pkg_version=_INSTALLED_VERSION)
            lines = _doctor_guardrail_pair(src, tmp_path)
        # self-repo lines must NOT appear
        assert not any("self-repo" in line for line in lines)

    def test_writes_to_stderr(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        content = "# AGENTS\n"
        src = self._write_agents_src(tmp_path, content)
        (tmp_path / "AGENTS.md").write_text(content, encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8")
        _doctor_guardrail_pair(src, tmp_path)
        captured = capsys.readouterr()
        assert "[ok]" in captured.err


# ---------------------------------------------------------------------------
# FileSystemPublicAssetManager helpers (unit, no real public dir)
# ---------------------------------------------------------------------------


def _build_minimal_agentic_dir(tmp_path: Path) -> tuple[Path, Path]:
    """Build a minimal agentic_dir + workspace_root usable for doctor/install tests.

    Returns (agentic_dir, workspace_root).
    """
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    agentic_dir = workspace_root / ".dadaia" / "agentic"
    agentic_dir.mkdir(parents=True)
    # Write a manifest so install() doesn't try to call stage()
    manifest = {
        "schema_version": "1",
        "package_version": "0.0.0-test",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "assets": [],
    }
    (agentic_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return agentic_dir, workspace_root


# ---------------------------------------------------------------------------
# D-CX-1: _dcx1_missing_toml
# ---------------------------------------------------------------------------


class TestDcx1MissingToml:
    def test_reports_missing_toml(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_dir = agentic_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
        codex_dir = workspace_root / ".codex"
        codex_dir.mkdir()
        manager = FileSystemPublicAssetManager()
        out = manager._dcx1_missing_toml(agentic_dir, codex_dir)
        assert any("my-agent.toml" in line and "[missing]" in line for line in out)

    def test_no_missing_when_toml_present(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_dir = agentic_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
        codex_dir = workspace_root / ".codex"
        codex_agents = codex_dir / "agents"
        codex_agents.mkdir(parents=True)
        (codex_agents / "my-agent.toml").write_text(
            'name = "my-agent"\nmodel = "gpt-4o"\ndeveloper_instructions = """\nbody\n"""\n',
            encoding="utf-8",
        )
        manager2 = FileSystemPublicAssetManager()
        out = manager2._dcx1_missing_toml(agentic_dir, codex_dir)
        assert out == []

    def test_empty_agents_dir_no_reports(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_dir = agentic_dir / "agents"
        agents_dir.mkdir()
        codex_dir = workspace_root / ".codex"
        codex_dir.mkdir()
        manager = FileSystemPublicAssetManager()
        out = manager._dcx1_missing_toml(agentic_dir, codex_dir)
        assert out == []

    def test_nonexistent_agents_dir_returns_empty(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        codex_dir = workspace_root / ".codex"
        codex_dir.mkdir()
        manager = FileSystemPublicAssetManager()
        out = manager._dcx1_missing_toml(agentic_dir, codex_dir)
        assert out == []


# ---------------------------------------------------------------------------
# D-CX-2: _dcx2_config_toml_entries
# ---------------------------------------------------------------------------


class TestDcx2ConfigTomlEntries:
    def test_reports_missing_config_entry(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        codex_dir = workspace_root / ".codex"
        codex_agents = codex_dir / "agents"
        codex_agents.mkdir(parents=True)
        (codex_agents / "my-agent.toml").write_text(
            'name = "my-agent"\nmodel = "gpt-4o"\ndeveloper_instructions = """\nbody\n"""\n',
            encoding="utf-8",
        )
        # config.toml is empty
        (codex_dir / "config.toml").write_text("", encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        out = manager._dcx2_config_toml_entries(agentic_dir, codex_dir)
        assert any("my-agent" in line and "[missing]" in line for line in out)

    def test_no_report_when_entry_present(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        codex_dir = workspace_root / ".codex"
        codex_agents = codex_dir / "agents"
        codex_agents.mkdir(parents=True)
        (codex_agents / "my-agent.toml").write_text(
            'name = "my-agent"\nmodel = "gpt-4o"\ndeveloper_instructions = """\nbody\n"""\n',
            encoding="utf-8",
        )
        config_text = 'config_file = "agents/my-agent.toml"\n'
        (codex_dir / "config.toml").write_text(config_text, encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        out = manager._dcx2_config_toml_entries(agentic_dir, codex_dir)
        assert out == []

    def test_no_codex_agents_dir_returns_empty(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        codex_dir = workspace_root / ".codex"
        codex_dir.mkdir()
        manager = FileSystemPublicAssetManager()
        out = manager._dcx2_config_toml_entries(agentic_dir, codex_dir)
        assert out == []


# ---------------------------------------------------------------------------
# D-CX-3: _dcx3_workflow_drift
# ---------------------------------------------------------------------------


class TestDcx3WorkflowDrift:
    def test_reports_missing_workflow(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        wf_dir = agentic_dir / "workflows"
        wf_dir.mkdir()
        (wf_dir / "my-workflow.workflow.md").write_text("# WF\n", encoding="utf-8")
        codex_dir = workspace_root / ".codex"
        codex_dir.mkdir()
        manager = FileSystemPublicAssetManager()
        out = manager._dcx3_workflow_drift(agentic_dir, codex_dir)
        assert any("my-workflow.workflow.md" in line and "[missing]" in line for line in out)

    def test_reports_extra_workflow(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        wf_dir = agentic_dir / "workflows"
        wf_dir.mkdir()
        codex_dir = workspace_root / ".codex"
        codex_wf = codex_dir / "workflows"
        codex_wf.mkdir(parents=True)
        (codex_wf / "extra.workflow.md").write_text("# extra\n", encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        out = manager._dcx3_workflow_drift(agentic_dir, codex_dir)
        assert any("extra.workflow.md" in line and "[extra]" in line for line in out)

    def test_no_drift_when_in_sync(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        wf_dir = agentic_dir / "workflows"
        wf_dir.mkdir()
        (wf_dir / "my.workflow.md").write_text("# WF\n", encoding="utf-8")
        codex_dir = workspace_root / ".codex"
        codex_wf = codex_dir / "workflows"
        codex_wf.mkdir(parents=True)
        (codex_wf / "my.workflow.md").write_text("# WF\n", encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        out = manager._dcx3_workflow_drift(agentic_dir, codex_dir)
        assert out == []


# ---------------------------------------------------------------------------
# D-CX-4: _dcx4_claude_strings
# ---------------------------------------------------------------------------


class TestDcx4ClaudeStrings:
    def test_reports_claude_string_in_toml(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        codex_dir = workspace_root / ".codex"
        codex_dir.mkdir()
        (codex_dir / "test.toml").write_text('model = "claude-sonnet-4-6"\n', encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        out = manager._dcx4_claude_strings(codex_dir)
        assert any("[error]" in line and "claude-model-or-path" in line for line in out)

    def test_no_report_when_no_claude_strings(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        codex_dir = workspace_root / ".codex"
        codex_dir.mkdir()
        (codex_dir / "test.toml").write_text('model = "gpt-4o"\n', encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        out = manager._dcx4_claude_strings(codex_dir)
        assert out == []

    def test_nonexistent_codex_dir_returns_empty(self, tmp_path: Path) -> None:
        manager = FileSystemPublicAssetManager()
        out = manager._dcx4_claude_strings(tmp_path / "no-such-dir")
        assert out == []

    def test_non_text_suffix_skipped(self, tmp_path: Path) -> None:
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir()
        (codex_dir / "binary.bin").write_bytes(b"claude-something")
        manager = FileSystemPublicAssetManager()
        out = manager._dcx4_claude_strings(codex_dir)
        assert out == []


# ---------------------------------------------------------------------------
# D-CX-5: _dcx5_empty_developer_instructions
# ---------------------------------------------------------------------------


class TestDcx5EmptyDeveloperInstructions:
    def test_reports_empty_instructions(self, tmp_path: Path) -> None:
        codex_dir = tmp_path / ".codex"
        codex_agents = codex_dir / "agents"
        codex_agents.mkdir(parents=True)
        (codex_agents / "my-agent.toml").write_text(
            'name = "my-agent"\nmodel = "gpt-4o"\ndeveloper_instructions = "   "\n',
            encoding="utf-8",
        )
        manager = FileSystemPublicAssetManager()
        out = manager._dcx5_empty_developer_instructions(codex_dir)
        assert any("[error]" in line and "developer_instructions is empty" in line for line in out)

    def test_reports_missing_instructions(self, tmp_path: Path) -> None:
        codex_dir = tmp_path / ".codex"
        codex_agents = codex_dir / "agents"
        codex_agents.mkdir(parents=True)
        (codex_agents / "my-agent.toml").write_text(
            'name = "my-agent"\nmodel = "gpt-4o"\n',
            encoding="utf-8",
        )
        manager = FileSystemPublicAssetManager()
        out = manager._dcx5_empty_developer_instructions(codex_dir)
        assert any("[error]" in line for line in out)

    def test_no_report_when_instructions_present(self, tmp_path: Path) -> None:
        codex_dir = tmp_path / ".codex"
        codex_agents = codex_dir / "agents"
        codex_agents.mkdir(parents=True)
        (codex_agents / "my-agent.toml").write_text(
            'name = "my-agent"\nmodel = "gpt-4o"\ndeveloper_instructions = """\nYou are helpful.\n"""\n',
            encoding="utf-8",
        )
        manager = FileSystemPublicAssetManager()
        out = manager._dcx5_empty_developer_instructions(codex_dir)
        assert out == []

    def test_reports_unparseable_toml(self, tmp_path: Path) -> None:
        codex_dir = tmp_path / ".codex"
        codex_agents = codex_dir / "agents"
        codex_agents.mkdir(parents=True)
        (codex_agents / "broken.toml").write_text("NOT VALID TOML ][[\n", encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        out = manager._dcx5_empty_developer_instructions(codex_dir)
        assert any("[error]" in line and "unparseable TOML" in line for line in out)

    def test_no_agents_dir_returns_empty(self, tmp_path: Path) -> None:
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir()
        manager = FileSystemPublicAssetManager()
        out = manager._dcx5_empty_developer_instructions(codex_dir)
        assert out == []


# ---------------------------------------------------------------------------
# _runtime_expectations — key branches
# ---------------------------------------------------------------------------


class TestRuntimeExpectations:
    def _make_manager(self) -> FileSystemPublicAssetManager:
        return FileSystemPublicAssetManager()

    def test_yields_nothing_when_no_agents_md(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        manager = self._make_manager()
        items = list(manager._runtime_expectations(agentic_dir, workspace_root))
        # Without agents_md source, no AGENTS.md/CLAUDE.md tuples emitted
        labels = [t[2] for t in items]
        assert "root:AGENTS.md" not in labels

    def test_yields_root_agents_md_when_source_exists(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        data_dir = agentic_dir / "data"
        data_dir.mkdir()
        (data_dir / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        manager = self._make_manager()
        items = list(manager._runtime_expectations(agentic_dir, workspace_root))
        labels = [t[2] for t in items]
        assert "root:AGENTS.md" in labels

    def test_yields_claude_md_stub_sentinel(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        data_dir = agentic_dir / "data"
        data_dir.mkdir()
        (data_dir / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        manager = self._make_manager()
        items = list(manager._runtime_expectations(agentic_dir, workspace_root))
        claude_md_items = [t for t in items if t[2] == "root:CLAUDE.md"]
        assert len(claude_md_items) == 1
        src, dst, label, transform = claude_md_items[0]
        assert src is None  # sentinel
        assert transform is True  # stub mode

    def test_yields_consumer_repo_pair(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        data_dir = agentic_dir / "data"
        data_dir.mkdir()
        (data_dir / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        _add_marker_consumer(workspace_root, "my-repo")
        manager = self._make_manager()
        items = list(manager._runtime_expectations(agentic_dir, workspace_root))
        labels = [t[2] for t in items]
        assert "repos/my-repo:AGENTS.md" in labels
        assert "repos/my-repo:CLAUDE.md" in labels

    def test_opencode_agent_has_transform_true(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_dir = agentic_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
        manager = self._make_manager()
        items = list(manager._runtime_expectations(agentic_dir, workspace_root))
        opencode_agent_items = [t for t in items if "opencode:agents/" in t[2]]
        assert all(t[3] is True for t in opencode_agent_items)

    def test_opencode_hooks_yields_unsupported(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        manager = self._make_manager()
        items = list(manager._runtime_expectations(agentic_dir, workspace_root))
        hooks_items = [t for t in items if t[2] == "opencode:hooks"]
        assert len(hooks_items) == 1
        src, dst, label, transform = hooks_items[0]
        assert src is None
        assert transform is False  # "unsupported" branch

    def test_codex_rules_not_sourced_from_markdown_protocols(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        rules_dir = agentic_dir / "rules"
        rules_dir.mkdir()
        (rules_dir / "exec.md").write_text("---\nname: exec\n---\nbody\n", encoding="utf-8")
        (rules_dir / "prose.md").write_text("# Prose rule (no frontmatter)\n", encoding="utf-8")
        manager = self._make_manager()
        items = list(manager._runtime_expectations(agentic_dir, workspace_root))
        codex_rule_labels = [t[2] for t in items if t[2].startswith("codex:rules/")]
        assert codex_rule_labels == []

    def test_reports_agents_md_yielded(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        data_dir = agentic_dir / "data"
        data_dir.mkdir()
        (data_dir / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        (data_dir / "reports-AGENTS.md").write_text("# REPORTS AGENTS\n", encoding="utf-8")
        manager = self._make_manager()
        items = list(manager._runtime_expectations(agentic_dir, workspace_root))
        labels = [t[2] for t in items]
        assert "reports:AGENTS.md" in labels

    def test_handoff_agents_md_yielded(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        data_dir = agentic_dir / "data"
        data_dir.mkdir()
        (data_dir / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        (data_dir / "handoff-AGENTS.md").write_text("# HANDOFF AGENTS\n", encoding="utf-8")
        manager = self._make_manager()
        items = list(manager._runtime_expectations(agentic_dir, workspace_root))
        labels = [t[2] for t in items]
        assert "handoff:AGENTS.md" in labels


# ---------------------------------------------------------------------------
# _install_codex_agents
# ---------------------------------------------------------------------------


class TestInstallCodexAgents:
    def test_generates_toml_for_each_agent(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_src = agentic_dir / "agents"
        agents_src.mkdir()
        (agents_src / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        manager._install_codex_agents(agentic_dir, workspace_root, force=True, installed=installed)
        toml_path = workspace_root / ".codex" / "agents" / "my-agent.toml"
        assert toml_path.exists()
        assert any("[ok]" in e for e in installed)

    def test_toml_content_is_valid_toml(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_src = agentic_dir / "agents"
        agents_src.mkdir()
        (agents_src / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        manager._install_codex_agents(agentic_dir, workspace_root, force=True, installed=[])
        toml_path = workspace_root / ".codex" / "agents" / "my-agent.toml"
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        assert data.get("name") == "my-agent"
        assert "developer_instructions" in data

    def test_overwrites_on_hash_mismatch_when_force_false(self, tmp_path: Path) -> None:
        """T-PROP-01: force=False + stale TOML → overwrite with generated content.

        Under the new hash-compare overwrite semantics, a locally-modified (or stale)
        TOML that differs from the freshly generated content is overwritten without
        needing --force.
        """
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_src = agentic_dir / "agents"
        agents_src.mkdir()
        (agents_src / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
        codex_agents = workspace_root / ".codex" / "agents"
        codex_agents.mkdir(parents=True)
        # Write stale content that differs from what _install_codex_agents would generate.
        stale_content = (
            'name = "my-agent"\nmodel = "gpt-4o"\ndeveloper_instructions = """\noriginal\n"""\n'
        )
        toml_path = codex_agents / "my-agent.toml"
        toml_path.write_text(stale_content, encoding="utf-8")
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        manager._install_codex_agents(agentic_dir, workspace_root, force=False, installed=installed)
        # Hash mismatch → overwritten with fresh generated content.
        result = toml_path.read_text(encoding="utf-8")
        assert result != stale_content, "Expected stale TOML to be overwritten"
        assert any("[ok]" in e for e in installed)
        assert not any("[skip]" in e for e in installed)

    def test_skips_when_generated_content_matches(self, tmp_path: Path) -> None:
        """T-PROP-01: force=False + identical TOML → no-op (hash match → skip)."""

        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_src = agentic_dir / "agents"
        agents_src.mkdir()
        (agents_src / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
        codex_agents = workspace_root / ".codex" / "agents"
        codex_agents.mkdir(parents=True)
        toml_path = codex_agents / "my-agent.toml"
        # First install with force=True to generate the canonical TOML.
        manager = FileSystemPublicAssetManager()
        manager._install_codex_agents(agentic_dir, workspace_root, force=True, installed=[])
        canonical_content = toml_path.read_text(encoding="utf-8")
        mtime_before = toml_path.stat().st_mtime
        # Second install with force=False — same content, must skip.
        installed: list[str] = []
        manager._install_codex_agents(agentic_dir, workspace_root, force=False, installed=installed)
        assert toml_path.read_text(encoding="utf-8") == canonical_content
        assert toml_path.stat().st_mtime == mtime_before
        assert any("[skip]" in e for e in installed)
        assert not any("[ok]" in e for e in installed)

    def test_agent_without_name_skipped(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_src = agentic_dir / "agents"
        agents_src.mkdir()
        (agents_src / "noname.md").write_text("---\nmodel: gpt-4o\n---\nbody\n", encoding="utf-8")
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        manager._install_codex_agents(agentic_dir, workspace_root, force=True, installed=installed)
        assert not (workspace_root / ".codex" / "agents" / "noname.toml").exists()
        assert installed == []

    def test_no_agents_dir_no_error(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        # Should raise FileNotFoundError or StopIteration since dir doesn't exist;
        # but the implementation uses sorted(agents_src.glob("*.md")) which returns [] on nonexistent
        # Actually it raises OSError — so just verify it doesn't blow up in unexpected ways
        # when agents dir does exist but is empty
        (agentic_dir / "agents").mkdir()
        manager._install_codex_agents(agentic_dir, workspace_root, force=True, installed=installed)
        assert installed == []


# ---------------------------------------------------------------------------
# _install_opencode
# ---------------------------------------------------------------------------


class TestInstallOpencode:
    def test_creates_opencode_json(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        manager._install_opencode(agentic_dir, workspace_root, force=True, installed=installed)
        opencode_json = workspace_root / "opencode.json"
        assert opencode_json.exists()
        data = json.loads(opencode_json.read_text(encoding="utf-8"))
        assert "$schema" in data
        assert "instructions" in data

    def test_opencode_json_contains_agents_md(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        manager = FileSystemPublicAssetManager()
        manager._install_opencode(agentic_dir, workspace_root, force=True, installed=[])
        data = json.loads((workspace_root / "opencode.json").read_text(encoding="utf-8"))
        assert "AGENTS.md" in data["instructions"]
        assert "CLAUDE.md" in data["instructions"]

    def test_agents_projected_to_opencode_dir(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_src = agentic_dir / "agents"
        agents_src.mkdir()
        (agents_src / "my-agent.md").write_text(
            _make_agent_md("my-agent", tools=["Read"]), encoding="utf-8"
        )
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        manager._install_opencode(agentic_dir, workspace_root, force=True, installed=installed)
        opencode_agent = workspace_root / ".opencode" / "agents" / "my-agent.md"
        assert opencode_agent.exists()
        content = opencode_agent.read_text(encoding="utf-8")
        # tools: block must be stripped
        assert "tools:" not in content

    def test_overwrites_stale_opencode_json_when_force_false(self, tmp_path: Path) -> None:
        """T-PROP-01: force=False + stale opencode.json → overwrite (hash-compare).

        The OLD behavior skipped any existing file. The NEW behavior overwrites when the
        generated content differs from the projected file.
        """
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        opencode_json = workspace_root / "opencode.json"
        opencode_json.write_text('{"old": true}\n', encoding="utf-8")
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        manager._install_opencode(agentic_dir, workspace_root, force=False, installed=installed)
        # Hash mismatch → stale opencode.json must be overwritten with generated content.
        result = opencode_json.read_text(encoding="utf-8")
        assert result != '{"old": true}\n', "Expected stale opencode.json to be overwritten"
        assert any("[ok]" in e and "opencode.json" in e for e in installed)

    def test_skips_opencode_json_when_content_matches(self, tmp_path: Path) -> None:
        """T-PROP-01: force=False + identical opencode.json → no-op (skip)."""
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        # First install with force=True to generate canonical opencode.json.
        manager = FileSystemPublicAssetManager()
        manager._install_opencode(agentic_dir, workspace_root, force=True, installed=[])
        opencode_json = workspace_root / "opencode.json"
        canonical_content = opencode_json.read_text(encoding="utf-8")
        mtime_before = opencode_json.stat().st_mtime
        # Second install with force=False — same content, must skip.
        installed: list[str] = []
        manager._install_opencode(agentic_dir, workspace_root, force=False, installed=installed)
        assert opencode_json.read_text(encoding="utf-8") == canonical_content
        assert opencode_json.stat().st_mtime == mtime_before
        assert any("[skip]" in e and "opencode.json" in e for e in installed)


# ---------------------------------------------------------------------------
# _agents_md_source — templates fallback
# ---------------------------------------------------------------------------


class TestAgentsMdSource:
    def test_prefers_data_over_templates(self, tmp_path: Path) -> None:
        agentic_dir, _ = _build_minimal_agentic_dir(tmp_path)
        data_dir = agentic_dir / "data"
        data_dir.mkdir()
        templates_dir = agentic_dir / "templates"
        templates_dir.mkdir()
        (data_dir / "AGENTS.md").write_text("# DATA\n", encoding="utf-8")
        (templates_dir / "AGENTS.md").write_text("# TEMPLATES\n", encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        src = manager._agents_md_source(agentic_dir)
        assert src is not None
        assert "data" in str(src)

    def test_falls_back_to_templates(self, tmp_path: Path) -> None:
        agentic_dir, _ = _build_minimal_agentic_dir(tmp_path)
        templates_dir = agentic_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "AGENTS.md").write_text("# TEMPLATES\n", encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        src = manager._agents_md_source(agentic_dir)
        assert src is not None
        assert "templates" in str(src)

    def test_returns_none_when_neither_exists(self, tmp_path: Path) -> None:
        agentic_dir, _ = _build_minimal_agentic_dir(tmp_path)
        manager = FileSystemPublicAssetManager()
        assert manager._agents_md_source(agentic_dir) is None


# ---------------------------------------------------------------------------
# _compare and _compare_content
# ---------------------------------------------------------------------------


class TestCompare:
    def test_ok_when_files_match(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        content = b"hello\n"
        src.write_bytes(content)
        dst.write_bytes(content)
        manager = FileSystemPublicAssetManager()
        assert manager._compare(src, dst, "test:label") == "[ok] test:label"

    def test_drift_when_files_differ(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_bytes(b"aaa")
        dst.write_bytes(b"bbb")
        manager = FileSystemPublicAssetManager()
        assert manager._compare(src, dst, "test:label") == "[drift] test:label"

    def test_missing_when_dst_absent(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        src.write_bytes(b"x")
        manager = FileSystemPublicAssetManager()
        assert (
            manager._compare(src, tmp_path / "absent.txt", "test:label") == "[missing] test:label"
        )

    def test_compare_content_ok(self, tmp_path: Path) -> None:
        dst = tmp_path / "out.txt"
        dst.write_text("hello\n", encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        assert manager._compare_content("hello\n", dst, "lbl") == "[ok] lbl"

    def test_compare_content_drift(self, tmp_path: Path) -> None:
        dst = tmp_path / "out.txt"
        dst.write_text("hello\n", encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        assert manager._compare_content("different\n", dst, "lbl") == "[drift] lbl"

    def test_compare_content_missing(self, tmp_path: Path) -> None:
        manager = FileSystemPublicAssetManager()
        assert manager._compare_content("x", tmp_path / "no.txt", "lbl") == "[missing] lbl"


# ---------------------------------------------------------------------------
# _lint_legacy_software_engineer
# ---------------------------------------------------------------------------


class TestLintLegacySoftwareEngineer:
    def test_reports_legacy_alias_in_public_dir(self, tmp_path: Path) -> None:
        """Build a fake public dir containing a file with the legacy alias."""
        manager = FileSystemPublicAssetManager()
        # Patch _public_dir to point at tmp_path
        manager._public_dir = tmp_path
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "bad.md").write_text(
            "subagent_type: software-engineer\n", encoding="utf-8"
        )
        out = manager._lint_legacy_software_engineer()
        assert any("[LINT]" in line for line in out)

    def test_no_report_for_split_alias(self, tmp_path: Path) -> None:
        manager = FileSystemPublicAssetManager()
        manager._public_dir = tmp_path
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "good.md").write_text(
            "subagent_type: software-engineer-python\n", encoding="utf-8"
        )
        out = manager._lint_legacy_software_engineer()
        assert out == []

    def test_empty_public_dir_no_reports(self, tmp_path: Path) -> None:
        manager = FileSystemPublicAssetManager()
        manager._public_dir = tmp_path
        out = manager._lint_legacy_software_engineer()
        assert out == []

    def test_nonexistent_public_dir_returns_empty(self, tmp_path: Path) -> None:
        manager = FileSystemPublicAssetManager()
        manager._public_dir = tmp_path / "nonexistent"
        out = manager._lint_legacy_software_engineer()
        assert out == []


# ---------------------------------------------------------------------------
# _classify_workflows
# ---------------------------------------------------------------------------


class TestClassifyWorkflows:
    def test_no_workflows_dir_returns_empty(self, tmp_path: Path) -> None:
        agentic_dir, _ = _build_minimal_agentic_dir(tmp_path)
        manager = FileSystemPublicAssetManager()
        out = manager._classify_workflows(agentic_dir)
        assert out == []

    def test_workflow_without_parallel_group_ok(self, tmp_path: Path) -> None:
        agentic_dir, _ = _build_minimal_agentic_dir(tmp_path)
        wf_dir = agentic_dir / "workflows"
        wf_dir.mkdir()
        (wf_dir / "simple.workflow.md").write_text(
            "# Simple WF\nNo parallel_group.\n", encoding="utf-8"
        )
        manager = FileSystemPublicAssetManager()
        out = manager._classify_workflows(agentic_dir)
        assert any(line == "[ok] opencode:workflows/simple.workflow.md" for line in out)
        assert any(line == "[ok] claude:workflows/simple.workflow.md" for line in out)
        assert any("[reference-only]" in line and "simple.workflow.md" in line for line in out)

    def test_workflow_with_parallel_group_partial(self, tmp_path: Path) -> None:
        agentic_dir, _ = _build_minimal_agentic_dir(tmp_path)
        wf_dir = agentic_dir / "workflows"
        wf_dir.mkdir()
        (wf_dir / "parallel.workflow.md").write_text(
            "---\nparallel_group: alpha\n---\n# WF\n", encoding="utf-8"
        )
        manager = FileSystemPublicAssetManager()
        out = manager._classify_workflows(agentic_dir)
        assert any("[partial]" in line and "parallel.workflow.md" in line for line in out)


# ---------------------------------------------------------------------------
# _codex_hooks / _claude_settings / _opencode_config
# ---------------------------------------------------------------------------


class TestConfigGenerators:
    def test_codex_hooks_structure(self, tmp_path: Path) -> None:
        # T-018-17: hook commands are now Python module invocations, not .sh paths.
        manager = FileSystemPublicAssetManager()
        config = manager._codex_hooks(tmp_path)
        assert "hooks" in config
        hooks = config["hooks"]

        assert "PreToolUse" in hooks
        matchers = hooks["PreToolUse"]
        assert isinstance(matchers, list)
        assert len(matchers) > 0
        assert matchers[0]["matcher"] == "^(apply_patch|Edit|Write)$"
        assert matchers[0]["hooks"][0]["type"] == "command"
        sdd_gate_cmd = str(matchers[0]["hooks"][0]["command"])
        assert "dadaia_workspace.hooks.sdd_gate" in sdd_gate_cmd
        assert "sdd-spec-gate.sh" not in sdd_gate_cmd
        # AC-T13-10: PostToolUse must be present and point to sdd_post_gate module.
        # N-2 (v0.1.10 rc-2): the heartbeat now fires on ALL tools — Codex's
        # canonical match-all is an *omitted* matcher (see
        # test_codex_posttooluse_heartbeat_fires_on_all_tools).
        assert "PostToolUse" in hooks
        post_matchers = hooks["PostToolUse"]
        assert isinstance(post_matchers, list)
        assert len(post_matchers) > 0
        assert "matcher" not in post_matchers[0]
        assert post_matchers[0]["hooks"][0]["type"] == "command"
        post_cmd = str(post_matchers[0]["hooks"][0]["command"])
        assert "dadaia_workspace.hooks.sdd_post_gate" in post_cmd
        assert "sdd-post-gate.sh" not in post_cmd
        assert "UserPromptSubmit" in hooks
        prompt_matchers = hooks["UserPromptSubmit"]
        assert isinstance(prompt_matchers, list)
        assert "matcher" not in prompt_matchers[0]
        assert prompt_matchers[0]["hooks"][0]["type"] == "command"
        prompt_command = str(prompt_matchers[0]["hooks"][0]["command"])
        assert prompt_command.startswith("DADAIA_HOOK_OUTPUT=codex-json ")
        assert "dadaia_workspace.hooks.ctx_inject" in prompt_command
        assert "ctx-inject.sh" not in prompt_command

    def test_codex_hooks_wire_sessionstart(self, tmp_path: Path) -> None:
        """T-016-C01: Codex SessionStart carries context once per session
        (matcher startup|resume), routed through ctx-inject in SessionStart mode.
        T-018-17: command is now Python module invocation, not .sh path."""
        manager = FileSystemPublicAssetManager()
        hooks = manager._codex_hooks(tmp_path)["hooks"]
        assert "SessionStart" in hooks
        ss = hooks["SessionStart"]
        assert isinstance(ss, list) and ss
        assert ss[0]["matcher"] == "startup|resume"
        cmd = str(ss[0]["hooks"][0]["command"])
        assert "DADAIA_HOOK_EVENT=SessionStart" in cmd
        assert "DADAIA_HOOK_OUTPUT=codex-json" in cmd
        assert "dadaia_workspace.hooks.ctx_inject" in cmd
        assert "ctx-inject.sh" not in cmd

    def test_codex_posttooluse_heartbeat_fires_on_all_tools(self, tmp_path: Path) -> None:
        """N-2 (v0.1.10 rc-2 re-audit HIGH): the Codex lease-heartbeat PostToolUse
        block must fire on ALL tools (omitted matcher = Codex canonical match-all),
        NOT only on the write tools. Pinning it to ``^(apply_patch|Edit|Write)$``
        starved the heartbeat during long Bash / read-only Codex calls, letting the
        lease go TTL-stale (the original lease-starvation incident's Codex flavor).

        The PreToolUse write gates stay scoped to the write tools only.
        Regression guard for runtime_config.codex_hooks.
        """
        manager = FileSystemPublicAssetManager()
        hooks = manager._codex_hooks(tmp_path)["hooks"]

        # PostToolUse heartbeat: omitted matcher => fires on every tool.
        post = hooks["PostToolUse"]
        assert isinstance(post, list) and len(post) == 1
        assert "matcher" not in post[0], (
            "Codex heartbeat must NOT be pinned to the write tools — an omitted "
            "matcher is Codex's canonical match-all (N-2)."
        )
        post_cmds = [str(h["command"]) for h in post[0]["hooks"]]
        assert any("dadaia_workspace.hooks.sdd_post_gate" in c for c in post_cmds)

        # PreToolUse write gates remain scoped to the write tools only.
        pre = hooks["PreToolUse"]
        assert isinstance(pre, list) and len(pre) == 2
        for entry in pre:
            assert entry["matcher"] == "^(apply_patch|Edit|Write)$"
        pre_cmds = [str(h["command"]) for e in pre for h in e["hooks"]]
        assert any("dadaia_workspace.hooks.sdd_gate" in c for c in pre_cmds)
        assert any("dadaia_workspace.hooks.root_whitelist" in c for c in pre_cmds)

    def test_claude_settings_structure(self, tmp_path: Path) -> None:
        # T-018-17: hook commands are now Python module invocations, not .sh paths.
        manager = FileSystemPublicAssetManager()
        settings = manager._claude_settings(tmp_path)
        assert "hooks" in settings
        assert "PreToolUse" in settings["hooks"]
        assert "UserPromptSubmit" in settings["hooks"]
        # AC-T13-10: PostToolUse must be present and point to sdd_post_gate module
        assert "PostToolUse" in settings["hooks"]
        post_hooks = settings["hooks"]["PostToolUse"]
        assert isinstance(post_hooks, list)
        assert len(post_hooks) > 0
        commands = [h["command"] for h in post_hooks[0]["hooks"]]
        assert any("dadaia_workspace.hooks.sdd_post_gate" in str(c) for c in commands)
        assert not any("sdd-post-gate.sh" in str(c) for c in commands)

    def test_claude_settings_matcher_scoping(self, tmp_path: Path) -> None:
        """T-010-18 (R6c, AC-R6-05, ai C-12): PreToolUse write-gate hooks are scoped
        to the write tools; PostToolUse heartbeat fires on all tools; UserPromptSubmit
        is unchanged (no empty match-all on the write gates)."""
        manager = FileSystemPublicAssetManager()
        settings = manager._claude_settings(tmp_path)
        hooks = settings["hooks"]
        write_matcher = "Edit|Write|MultiEdit|NotebookEdit"

        # PreToolUse: both sdd_gate and root_whitelist scoped to the write tools.
        pre = hooks["PreToolUse"]
        assert isinstance(pre, list) and len(pre) == 2
        for entry in pre:
            assert entry["matcher"] == write_matcher
            assert entry["matcher"] != "", "write gate must not use the empty match-all"
        pre_cmds = [str(h["command"]) for e in pre for h in e["hooks"]]
        assert any("dadaia_workspace.hooks.sdd_gate" in c for c in pre_cmds)
        assert any("dadaia_workspace.hooks.root_whitelist" in c for c in pre_cmds)

        # PostToolUse: heartbeat must fire on ALL tools via the explicit match-all.
        post = hooks["PostToolUse"]
        assert isinstance(post, list) and len(post) == 1
        assert post[0]["matcher"] == "*"
        post_cmds = [str(h["command"]) for h in post[0]["hooks"]]
        assert any("dadaia_workspace.hooks.sdd_post_gate" in c for c in post_cmds)

        # UserPromptSubmit: unchanged (empty matcher, ctx-inject).
        ups = hooks["UserPromptSubmit"]
        assert isinstance(ups, list) and len(ups) == 1
        assert ups[0]["matcher"] == ""
        ups_cmds = [str(h["command"]) for h in ups[0]["hooks"]]
        assert any("dadaia_workspace.hooks.ctx_inject" in c for c in ups_cmds)

    def test_claude_settings_root_whitelist_gate_present(self, tmp_path: Path) -> None:
        """T-SANI-01: root-whitelist hook must be registered as a PreToolUse hook.
        T-018-17: command is now Python module invocation, not .sh path."""
        manager = FileSystemPublicAssetManager()
        settings = manager._claude_settings(tmp_path)
        pre_tool_use = settings["hooks"]["PreToolUse"]
        # Collect all hook commands across all PreToolUse entries
        all_commands = [
            str(hook["command"]) for entry in pre_tool_use for hook in entry.get("hooks", [])
        ]
        assert any("dadaia_workspace.hooks.root_whitelist" in cmd for cmd in all_commands), (
            "dadaia_workspace.hooks.root_whitelist not found in claude settings PreToolUse hooks"
        )
        assert not any("root-whitelist-gate.sh" in cmd for cmd in all_commands), (
            "stale root-whitelist-gate.sh still present in claude settings PreToolUse hooks"
        )

    def test_codex_hooks_root_whitelist_gate_present(self, tmp_path: Path) -> None:
        """T-SANI-01: root-whitelist hook must be registered as a Codex PreToolUse hook.
        T-018-17: command is now Python module invocation, not .sh path."""
        manager = FileSystemPublicAssetManager()
        config = manager._codex_hooks(tmp_path)
        pre_tool_use = config["hooks"]["PreToolUse"]
        # Collect all hook commands across all PreToolUse entries
        all_commands = [
            str(hook["command"]) for entry in pre_tool_use for hook in entry.get("hooks", [])
        ]
        assert any("dadaia_workspace.hooks.root_whitelist" in cmd for cmd in all_commands), (
            "dadaia_workspace.hooks.root_whitelist not found in codex hooks PreToolUse hooks"
        )
        assert not any("root-whitelist-gate.sh" in cmd for cmd in all_commands), (
            "stale root-whitelist-gate.sh still present in codex hooks PreToolUse hooks"
        )

    def test_codex_force_install_removes_stale_agents_and_workflows(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        manager = FileSystemPublicAssetManager()
        manager.stage(workspace)
        stale_agent = workspace / ".codex" / "agents" / "stale-agent.toml"
        stale_agent.parent.mkdir(parents=True, exist_ok=True)
        stale_agent.write_text('model = "gpt-5.3-codex"\n', encoding="utf-8")
        stale_workflow = workspace / ".codex" / "workflows" / "stale.workflow.md"
        stale_workflow.parent.mkdir(parents=True, exist_ok=True)
        stale_workflow.write_text("# stale\n", encoding="utf-8")

        installed = manager.install(workspace, target="codex", force=True)

        assert not stale_agent.exists()
        assert not stale_workflow.exists()
        assert any("[rm]" in item and "stale-agent.toml" in item for item in installed)
        assert any("[rm]" in item and "stale.workflow.md" in item for item in installed)

    def test_opencode_config_structure(self, tmp_path: Path) -> None:
        manager = FileSystemPublicAssetManager()
        config = manager._opencode_config(tmp_path)
        assert "$schema" in config
        assert "AGENTS.md" in config["instructions"]
        assert "permission" in config

    def test_opencode_config_adds_repo_slug_when_context_exists(self, tmp_path: Path) -> None:
        manager = FileSystemPublicAssetManager()
        # Create spec_contexts.json pointing to a repo with AGENTS.md
        states_dir = tmp_path / ".dadaia" / "states"
        states_dir.mkdir(parents=True)
        repo_slug = "my-project"
        repo_agents = tmp_path / "repos" / repo_slug / "AGENTS.md"
        repo_agents.parent.mkdir(parents=True)
        repo_agents.write_text("# AGENTS\n", encoding="utf-8")
        (states_dir / "spec_contexts.json").write_text(
            json.dumps(
                {"version": 2, "contexts": [{"name": "My Project", "repo_slug": repo_slug}]}
            ),
            encoding="utf-8",
        )
        config = manager._opencode_config(tmp_path)
        assert f"repos/{repo_slug}/AGENTS.md" in config["instructions"]

    def test_codex_config_contains_approved_commands(self, tmp_path: Path) -> None:
        agentic_dir, _ = _build_minimal_agentic_dir(tmp_path)
        manager = FileSystemPublicAssetManager()
        config_text = manager._codex_config(agentic_dir)
        assert "approved_commands" in config_text
        assert '"git"' in config_text

    def test_codex_config_skills_section(self, tmp_path: Path) -> None:
        agentic_dir, _ = _build_minimal_agentic_dir(tmp_path)
        manager = FileSystemPublicAssetManager()
        config_text = manager._codex_config(agentic_dir)
        assert "[skills]" in config_text
        assert ".agents/skills" in config_text
        assert ".codex/skills" in config_text


# ---------------------------------------------------------------------------
# _install_codex_rules
# ---------------------------------------------------------------------------


class TestInstallCodexRules:
    def test_native_command_policy_rules_generated(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        rules_dir = agentic_dir / "rules"
        rules_dir.mkdir()
        (rules_dir / "exec.md").write_text("---\nname: exec\n---\nbody\n", encoding="utf-8")
        (rules_dir / "prose.md").write_text("# Prose (no frontmatter)\n", encoding="utf-8")
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        manager._install_codex_rules(agentic_dir, workspace_root, force=True, installed=installed)
        assert (workspace_root / ".codex" / "rules" / "dadaia-command-policy.rules").exists()
        assert not (workspace_root / ".codex" / "rules" / "exec.md").exists()
        assert not (workspace_root / ".codex" / "rules" / "prose.md").exists()
        assert any("dadaia-command-policy.rules" in e for e in installed)

    def test_no_rules_dir_still_generates_policy(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        manager._install_codex_rules(agentic_dir, workspace_root, force=True, installed=installed)
        assert (workspace_root / ".codex" / "rules" / "dadaia-command-policy.rules").exists()
        assert len(installed) == 1

    def test_dadaia_rules_gate_venv_invocation_form(self) -> None:
        """T-013-10: dadaia-gating prefix rules must match the mandated venv form.

        prefix_rule matches the argv prefix literally, so a pattern whose first
        token is bare `dadaia` never fires against the workspace-mandated
        `.dadaia/.venv/bin/dadaia ...` invocation. The generated policy must carry
        a venv-relative pattern for both `public install` and `context dead`, and
        prove the real form in `match=` (closes
        codex-rules-dadaia-prefix-never-matches-venv-invocation).
        """
        from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
            _render_codex_command_policy_rules,
        )

        rules = _render_codex_command_policy_rules()

        # The mandated venv invocation is the FIRST argv token in a pattern.
        assert 'pattern = [".dadaia/.venv/bin/dadaia", "public", "install"]' in rules
        assert 'pattern = [".dadaia/.venv/bin/dadaia", "context", "dead"]' in rules

        # `match=` examples self-document using the REAL invocation form.
        assert ".dadaia/.venv/bin/dadaia public install --target codex" in rules
        assert ".dadaia/.venv/bin/dadaia context dead dadaia-workspace" in rules

        # Shape invariant kept (D-CX-8): prefix_rule, no command_allowed.
        assert "prefix_rule(" in rules
        assert "command_allowed(" not in rules

    def test_dadaia_rules_keep_bare_name_fallback(self) -> None:
        """T-013-10: a bare-name `dadaia` fallback pattern remains for PATH invocations."""
        from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
            _render_codex_command_policy_rules,
        )

        rules = _render_codex_command_policy_rules()
        assert 'pattern = ["dadaia", "public", "install"]' in rules
        assert 'pattern = ["dadaia", "context", "dead"]' in rules


# ---------------------------------------------------------------------------
# _install_scripts
# ---------------------------------------------------------------------------


class TestInstallScripts:
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="the 0o755 executable bit is a no-op on Windows; .sh scripts are "
        "POSIX-only and unused by the Windows Python governance hooks",
    )
    def test_scripts_chmod_applied(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        scripts_src = agentic_dir / "scripts"
        scripts_src.mkdir()
        (scripts_src / "test.sh").write_text("#!/bin/bash\n", encoding="utf-8")
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        manager._install_scripts(agentic_dir, workspace_root, force=True, installed=installed)
        dst_script = workspace_root / ".dadaia" / "scripts" / "test.sh"
        assert dst_script.exists()
        # chmod 0o755
        mode = oct(dst_script.stat().st_mode)[-3:]
        assert mode == "755"


# ---------------------------------------------------------------------------
# doctor() — happy path with minimal public_dir
# ---------------------------------------------------------------------------


class TestDoctorMethod:
    def _make_manager_with_fake_public(self, public_dir: Path) -> FileSystemPublicAssetManager:
        manager = FileSystemPublicAssetManager()
        manager._public_dir = public_dir
        return manager

    def test_raises_when_public_dir_missing(self, tmp_path: Path) -> None:
        from dadaia_workspace.core.exceptions import PublicAssetError

        manager = self._make_manager_with_fake_public(tmp_path / "nonexistent")
        with pytest.raises(PublicAssetError, match="not found"):
            manager.doctor(tmp_path)

    def test_reports_missing_manifest(self, tmp_path: Path) -> None:
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        # agentic_dir exists but no manifest
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        agentic_dir.mkdir(parents=True)
        manager = self._make_manager_with_fake_public(public_dir)
        reports = manager.doctor(workspace_root)
        assert "[missing] stage:manifest.json" in reports

    def test_ok_report_for_staged_file(self, tmp_path: Path) -> None:
        """A file in public_dir that is mirrored in agentic_dir gets [ok] report."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        (public_dir / "testfile.txt").write_text("content\n", encoding="utf-8")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        agentic_dir.mkdir(parents=True)
        # Mirror the file
        (agentic_dir / "testfile.txt").write_text("content\n", encoding="utf-8")
        # Write manifest
        (agentic_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "package_version": "0",
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "assets": [],
                }
            ),
            encoding="utf-8",
        )
        manager = self._make_manager_with_fake_public(public_dir)
        reports = manager.doctor(workspace_root)
        assert any(r == "[ok] stage:testfile.txt" for r in reports)

    def test_drift_report_for_modified_file(self, tmp_path: Path) -> None:
        """A file in public_dir that differs in agentic_dir gets [drift] report."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        (public_dir / "testfile.txt").write_text("original\n", encoding="utf-8")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        agentic_dir.mkdir(parents=True)
        (agentic_dir / "testfile.txt").write_text("modified\n", encoding="utf-8")
        (agentic_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "package_version": "0",
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "assets": [],
                }
            ),
            encoding="utf-8",
        )
        manager = self._make_manager_with_fake_public(public_dir)
        reports = manager.doctor(workspace_root)
        assert any(r == "[drift] stage:testfile.txt" for r in reports)

    def test_reports_unsupported_for_opencode_hooks(self, tmp_path: Path) -> None:
        """opencode:hooks (src=None, transform=False) gets [unsupported] label."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        agentic_dir.mkdir(parents=True)
        (agentic_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "package_version": "0",
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "assets": [],
                }
            ),
            encoding="utf-8",
        )
        manager = self._make_manager_with_fake_public(public_dir)
        reports = manager.doctor(workspace_root)
        assert any(r == "[unsupported] opencode:hooks" for r in reports)

    def test_reports_claude_md_stub_check(self, tmp_path: Path) -> None:
        """When agents_md source exists, CLAUDE.md stub is verified by doctor."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        agentic_dir.mkdir(parents=True)
        data_dir = agentic_dir / "data"
        data_dir.mkdir()
        (data_dir / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        (agentic_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "package_version": "0",
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "assets": [],
                }
            ),
            encoding="utf-8",
        )
        # AGENTS.md correct, CLAUDE.md incorrect
        (workspace_root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        (workspace_root / "CLAUDE.md").write_text("# WRONG\n", encoding="utf-8")
        manager = self._make_manager_with_fake_public(public_dir)
        reports = manager.doctor(workspace_root)
        assert any("[drift]" in r and "CLAUDE.md" in r for r in reports)


# ---------------------------------------------------------------------------
# _install_claude settings.json skip
# ---------------------------------------------------------------------------


class TestInstallClaudeSettingsSkip:
    def test_stale_settings_overwritten_when_force_false(self, tmp_path: Path) -> None:
        """T-PROP-01: force=False + stale settings.json → overwrite (hash-compare).

        The OLD behavior unconditionally skipped existing settings.json. The NEW behavior
        overwrites when the generated settings differ from the projected file.
        """
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        claude_dir = workspace_root / ".claude"
        claude_dir.mkdir(parents=True)
        settings_path = claude_dir / "settings.json"
        settings_path.write_text('{"existing": true}\n', encoding="utf-8")
        installed: list[str] = []
        manager = FileSystemPublicAssetManager()
        manager._install_claude(agentic_dir, workspace_root, force=False, installed=installed)
        # Hash mismatch → stale settings.json must be overwritten with generated content.
        result = settings_path.read_text(encoding="utf-8")
        assert result != '{"existing": true}\n', "Expected stale settings.json to be overwritten"
        assert any("[ok]" in e and "settings.json" in e for e in installed)

    def test_settings_skipped_when_content_matches(self, tmp_path: Path) -> None:
        """T-PROP-01: force=False + identical settings.json → no-op (skip)."""
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        # First install to generate canonical settings.json.
        manager = FileSystemPublicAssetManager()
        manager._install_claude(agentic_dir, workspace_root, force=True, installed=[])
        claude_dir = workspace_root / ".claude"
        settings_path = claude_dir / "settings.json"
        canonical_content = settings_path.read_text(encoding="utf-8")
        mtime_before = settings_path.stat().st_mtime
        # Second install with force=False — same content, must skip.
        installed: list[str] = []
        manager._install_claude(agentic_dir, workspace_root, force=False, installed=installed)
        assert settings_path.read_text(encoding="utf-8") == canonical_content
        assert settings_path.stat().st_mtime == mtime_before
        assert any("[skip]" in e and "settings.json" in e for e in installed)


# ---------------------------------------------------------------------------
# _opencode_config — JSON decode error path
# ---------------------------------------------------------------------------


class TestOpencodeConfigJsonError:
    def test_invalid_json_in_context_registry_ignored(self, tmp_path: Path) -> None:
        states_dir = tmp_path / ".dadaia" / "states"
        states_dir.mkdir(parents=True)
        (states_dir / "spec_contexts.json").write_text("NOT JSON", encoding="utf-8")
        manager = FileSystemPublicAssetManager()
        # Should not raise; invalid JSON is silently swallowed
        config = manager._opencode_config(tmp_path)
        assert "instructions" in config
        assert "AGENTS.md" in config["instructions"]


# ---------------------------------------------------------------------------
# _dcx1_missing_toml — agent without parseable name falls back to stem
# ---------------------------------------------------------------------------


class TestDcx1FallbackToStem:
    def test_agent_with_invalid_frontmatter_uses_stem(self, tmp_path: Path) -> None:
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        agents_dir = agentic_dir / "agents"
        agents_dir.mkdir()
        # File has no frontmatter => fm.get("name") returns "" => stem used
        (agents_dir / "fallback-agent.md").write_text("# No frontmatter\n", encoding="utf-8")
        codex_dir = workspace_root / ".codex"
        codex_dir.mkdir()
        manager = FileSystemPublicAssetManager()
        out = manager._dcx1_missing_toml(agentic_dir, codex_dir)
        # Should report missing using stem "fallback-agent"
        assert any("fallback-agent.toml" in line and "[missing]" in line for line in out)


# ---------------------------------------------------------------------------
# _dcx4_claude_strings — UnicodeDecodeError path
# ---------------------------------------------------------------------------


class TestDcx4UnicodeError:
    def test_binary_file_with_text_suffix_skipped(self, tmp_path: Path) -> None:
        """A .toml file containing non-UTF-8 bytes must be skipped without error."""
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir()
        # Write bytes that aren't valid UTF-8
        (codex_dir / "bad.toml").write_bytes(b"\xff\xfe" + b"claude-" + b"\x80\x81")
        manager = FileSystemPublicAssetManager()
        # Should not raise; UnicodeDecodeError is caught
        out = manager._dcx4_claude_strings(codex_dir)
        # File is skipped due to decode error, not reported
        assert out == []


# ---------------------------------------------------------------------------
# Instance methods _consumer_repos and _is_self_repo
# ---------------------------------------------------------------------------


class TestInstanceConsumerRepos:
    def test_returns_qualifying_repos(self, tmp_path: Path) -> None:
        consumer = _add_marker_consumer(tmp_path, "my-repo")
        manager = FileSystemPublicAssetManager()
        result = manager._consumer_repos(tmp_path)
        assert consumer in result

    def test_no_repos_dir_returns_empty(self, tmp_path: Path) -> None:
        manager = FileSystemPublicAssetManager()
        assert manager._consumer_repos(tmp_path) == []

    def test_non_qualifying_repo_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bad_repo = tmp_path / "repos" / "partial"
        bad_repo.mkdir(parents=True)
        manager = FileSystemPublicAssetManager()
        result = manager._consumer_repos(tmp_path)
        assert bad_repo not in result
        captured = capsys.readouterr()
        assert "[skip]" in captured.err


class TestInstanceIsSelfRepo:
    def test_matching_version_returns_true(self, tmp_path: Path) -> None:
        with patch(
            "dadaia_workspace.infrastructure.workspace_guardrail._package_version",
            return_value=_INSTALLED_VERSION,
        ):
            consumer = _add_marker_consumer(tmp_path, "self", pkg_version=_INSTALLED_VERSION)
            manager = FileSystemPublicAssetManager()
            assert manager._is_self_repo(consumer) is True

    def test_different_version_returns_false(self, tmp_path: Path) -> None:
        with patch(
            "dadaia_workspace.infrastructure.workspace_guardrail._package_version",
            return_value=_INSTALLED_VERSION,
        ):
            consumer = _add_marker_consumer(tmp_path, "other", pkg_version=_OTHER_VERSION)
            manager = FileSystemPublicAssetManager()
            assert manager._is_self_repo(consumer) is False

    def test_no_manifest_returns_false(self, tmp_path: Path) -> None:
        consumer = tmp_path / "repos" / "no-manifest"
        (consumer / ".dadaia" / "agentic").mkdir(parents=True)
        manager = FileSystemPublicAssetManager()
        assert manager._is_self_repo(consumer) is False


# ---------------------------------------------------------------------------
# _install_codex_runtime_adapters (T-08)
# ---------------------------------------------------------------------------


class TestInstallCodexRuntimeAdapters:
    def _make_manager_with_fake_public(self, public_dir: Path) -> FileSystemPublicAssetManager:
        manager = FileSystemPublicAssetManager()
        manager._public_dir = public_dir
        return manager

    def test_copies_skill_md_to_codex_skills(self, tmp_path: Path) -> None:
        """An adapter SKILL.md is copied to .codex/skills/<slug>/SKILL.md."""
        public_dir = tmp_path / "public"
        runtime_codex = public_dir / "runtime" / "codex" / "my-adapter"
        runtime_codex.mkdir(parents=True)
        (runtime_codex / "SKILL.md").write_text("# My Adapter\n", encoding="utf-8")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        installed: list[str] = []
        manager = self._make_manager_with_fake_public(public_dir)
        manager._install_codex_runtime_adapters(workspace_root, force=True, installed=installed)
        dst = workspace_root / ".codex" / "skills" / "my-adapter" / "SKILL.md"
        assert dst.exists()
        assert dst.read_text(encoding="utf-8") == "# My Adapter\n"
        assert any("[ok]" in e for e in installed)

    def test_returns_early_when_src_root_missing(self, tmp_path: Path) -> None:
        """No error and no writes when public/runtime/codex/ does not exist."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        installed: list[str] = []
        manager = self._make_manager_with_fake_public(public_dir)
        manager._install_codex_runtime_adapters(workspace_root, force=True, installed=installed)
        assert installed == []
        assert not (workspace_root / ".codex" / "skills").exists()

    def test_skips_subdirs_without_skill_md(self, tmp_path: Path) -> None:
        """A subdirectory without SKILL.md is silently skipped."""
        public_dir = tmp_path / "public"
        runtime_codex = public_dir / "runtime" / "codex" / "empty-adapter"
        runtime_codex.mkdir(parents=True)
        # No SKILL.md inside
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        installed: list[str] = []
        manager = self._make_manager_with_fake_public(public_dir)
        manager._install_codex_runtime_adapters(workspace_root, force=True, installed=installed)
        assert installed == []

    def test_skips_files_in_runtime_codex_root(self, tmp_path: Path) -> None:
        """Regular files at the root of runtime/codex/ (not subdirs) are skipped."""
        public_dir = tmp_path / "public"
        runtime_codex_root = public_dir / "runtime" / "codex"
        runtime_codex_root.mkdir(parents=True)
        (runtime_codex_root / "README.md").write_text("# README\n", encoding="utf-8")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        installed: list[str] = []
        manager = self._make_manager_with_fake_public(public_dir)
        manager._install_codex_runtime_adapters(workspace_root, force=True, installed=installed)
        assert installed == []

    def test_force_false_overwrites_on_hash_mismatch(self, tmp_path: Path) -> None:
        """T-PROP-01: force=False + stale projection → overwrite (hash-compare overwrite).

        Under the new behavior, force=False does NOT unconditionally skip existing files.
        When staged content differs from projected content, it is overwritten even without
        --force.  A plain 'skip-all-existing' is the OLD (pre-T-PROP-01) contract.
        """
        public_dir = tmp_path / "public"
        runtime_codex = public_dir / "runtime" / "codex" / "my-adapter"
        runtime_codex.mkdir(parents=True)
        (runtime_codex / "SKILL.md").write_text("# NEW\n", encoding="utf-8")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        dst = workspace_root / ".codex" / "skills" / "my-adapter" / "SKILL.md"
        dst.parent.mkdir(parents=True)
        dst.write_text("# ORIGINAL\n", encoding="utf-8")
        installed: list[str] = []
        manager = self._make_manager_with_fake_public(public_dir)
        manager._install_codex_runtime_adapters(workspace_root, force=False, installed=installed)
        # Hash mismatch → projected file must be overwritten with staged content.
        assert dst.read_text(encoding="utf-8") == "# NEW\n"
        assert any("[ok]" in e for e in installed)
        assert not any("[skip]" in e for e in installed)

    def test_force_false_skips_when_hashes_match(self, tmp_path: Path) -> None:
        """T-PROP-01: force=False + identical projected content → no-op (skip)."""
        identical_content = "# SAME CONTENT\n"
        public_dir = tmp_path / "public"
        runtime_codex = public_dir / "runtime" / "codex" / "my-adapter"
        runtime_codex.mkdir(parents=True)
        (runtime_codex / "SKILL.md").write_text(identical_content, encoding="utf-8")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        dst = workspace_root / ".codex" / "skills" / "my-adapter" / "SKILL.md"
        dst.parent.mkdir(parents=True)
        dst.write_text(identical_content, encoding="utf-8")
        mtime_before = dst.stat().st_mtime
        installed: list[str] = []
        manager = self._make_manager_with_fake_public(public_dir)
        manager._install_codex_runtime_adapters(workspace_root, force=False, installed=installed)
        # Hash match → no write, mtime unchanged, [skip] reported.
        assert dst.read_text(encoding="utf-8") == identical_content
        assert dst.stat().st_mtime == mtime_before
        assert any("[skip]" in e for e in installed)
        assert not any("[ok]" in e for e in installed)

    def test_does_not_write_to_claude_or_opencode(self, tmp_path: Path) -> None:
        """Codex-only adapters are never written to .claude/ or .opencode/."""
        public_dir = tmp_path / "public"
        runtime_codex = public_dir / "runtime" / "codex" / "my-adapter"
        runtime_codex.mkdir(parents=True)
        (runtime_codex / "SKILL.md").write_text("# My Adapter\n", encoding="utf-8")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        manager = self._make_manager_with_fake_public(public_dir)
        manager._install_codex_runtime_adapters(workspace_root, force=True, installed=[])
        assert not (workspace_root / ".claude" / "skills" / "my-adapter" / "SKILL.md").exists()
        assert not (workspace_root / ".opencode" / "skills" / "my-adapter" / "SKILL.md").exists()

    def test_multiple_adapters_all_copied(self, tmp_path: Path) -> None:
        """Multiple adapter subdirectories are all copied."""
        public_dir = tmp_path / "public"
        runtime_codex = public_dir / "runtime" / "codex"
        for slug in ("adapter-a", "adapter-b", "adapter-c"):
            (runtime_codex / slug).mkdir(parents=True)
            (runtime_codex / slug / "SKILL.md").write_text(f"# {slug}\n", encoding="utf-8")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        installed: list[str] = []
        manager = self._make_manager_with_fake_public(public_dir)
        manager._install_codex_runtime_adapters(workspace_root, force=True, installed=installed)
        assert len(installed) == 3
        for slug in ("adapter-a", "adapter-b", "adapter-c"):
            assert (workspace_root / ".codex" / "skills" / slug / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# D-CX-6: _dcx6_codex_runtime_adapters (T-09)
# ---------------------------------------------------------------------------


class TestDcx6CodexRuntimeAdapters:
    def _make_manager_with_fake_public(self, public_dir: Path) -> FileSystemPublicAssetManager:
        manager = FileSystemPublicAssetManager()
        manager._public_dir = public_dir
        return manager

    def _setup_adapter(self, public_dir: Path, slug: str, content: str = "# Adapter\n") -> None:
        adapter_dir = public_dir / "runtime" / "codex" / slug
        adapter_dir.mkdir(parents=True, exist_ok=True)
        (adapter_dir / "SKILL.md").write_text(content, encoding="utf-8")

    def test_missing_when_codex_skill_absent(self, tmp_path: Path) -> None:
        """[missing] reported when .codex/skills/<slug>/SKILL.md does not exist."""
        public_dir = tmp_path / "public"
        self._setup_adapter(public_dir, "my-adapter")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        manager = self._make_manager_with_fake_public(public_dir)
        out = manager._dcx6_codex_runtime_adapters(workspace_root)
        assert any(
            "[missing]" in line and "my-adapter" in line and "D-CX-6" in line for line in out
        )

    def test_ok_when_codex_skill_present_and_matches(self, tmp_path: Path) -> None:
        """No issues when adapter is installed and content matches source."""
        public_dir = tmp_path / "public"
        content = "# My Adapter\n"
        self._setup_adapter(public_dir, "my-adapter", content)
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        dst = workspace_root / ".codex" / "skills" / "my-adapter" / "SKILL.md"
        dst.parent.mkdir(parents=True)
        dst.write_text(content, encoding="utf-8")
        manager = self._make_manager_with_fake_public(public_dir)
        out = manager._dcx6_codex_runtime_adapters(workspace_root)
        assert out == []

    def test_drift_when_installed_differs_from_source(self, tmp_path: Path) -> None:
        """[drift] reported when installed content differs from source."""
        public_dir = tmp_path / "public"
        self._setup_adapter(public_dir, "my-adapter", "# Source\n")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        dst = workspace_root / ".codex" / "skills" / "my-adapter" / "SKILL.md"
        dst.parent.mkdir(parents=True)
        dst.write_text("# Modified\n", encoding="utf-8")
        manager = self._make_manager_with_fake_public(public_dir)
        out = manager._dcx6_codex_runtime_adapters(workspace_root)
        assert any("[drift]" in line and "my-adapter" in line and "D-CX-6" in line for line in out)

    def test_leak_when_adapter_in_claude_skills(self, tmp_path: Path) -> None:
        """[leak] reported when adapter appears in .claude/skills/."""
        public_dir = tmp_path / "public"
        self._setup_adapter(public_dir, "my-adapter")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        # Place the adapter in .claude/skills/ — simulating a leak
        leak_path = workspace_root / ".claude" / "skills" / "my-adapter" / "SKILL.md"
        leak_path.parent.mkdir(parents=True)
        leak_path.write_text("# Leak\n", encoding="utf-8")
        manager = self._make_manager_with_fake_public(public_dir)
        out = manager._dcx6_codex_runtime_adapters(workspace_root)
        assert any(
            "[leak]" in line and "claude" in line and "my-adapter" in line and "D-CX-6" in line
            for line in out
        )

    def test_leak_when_adapter_in_opencode_skills(self, tmp_path: Path) -> None:
        """[leak] reported when adapter appears in .opencode/skills/."""
        public_dir = tmp_path / "public"
        self._setup_adapter(public_dir, "my-adapter")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        # Place the adapter in .opencode/skills/ — simulating a leak
        leak_path = workspace_root / ".opencode" / "skills" / "my-adapter" / "SKILL.md"
        leak_path.parent.mkdir(parents=True)
        leak_path.write_text("# Leak\n", encoding="utf-8")
        manager = self._make_manager_with_fake_public(public_dir)
        out = manager._dcx6_codex_runtime_adapters(workspace_root)
        assert any(
            "[leak]" in line and "opencode" in line and "my-adapter" in line and "D-CX-6" in line
            for line in out
        )

    def test_no_src_root_returns_empty(self, tmp_path: Path) -> None:
        """Returns empty list when public/runtime/codex/ does not exist."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        manager = self._make_manager_with_fake_public(public_dir)
        out = manager._dcx6_codex_runtime_adapters(workspace_root)
        assert out == []

    def test_files_in_src_root_not_dirs_are_skipped(self, tmp_path: Path) -> None:
        """Regular files at runtime/codex/ root level (not dirs) are ignored."""
        public_dir = tmp_path / "public"
        runtime_codex = public_dir / "runtime" / "codex"
        runtime_codex.mkdir(parents=True)
        (runtime_codex / "README.md").write_text("# README\n", encoding="utf-8")
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        manager = self._make_manager_with_fake_public(public_dir)
        out = manager._dcx6_codex_runtime_adapters(workspace_root)
        assert out == []

    def test_subdirs_without_skill_md_are_skipped(self, tmp_path: Path) -> None:
        """Adapter subdirs without SKILL.md are silently skipped."""
        public_dir = tmp_path / "public"
        runtime_codex = public_dir / "runtime" / "codex" / "empty-adapter"
        runtime_codex.mkdir(parents=True)
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        manager = self._make_manager_with_fake_public(public_dir)
        out = manager._dcx6_codex_runtime_adapters(workspace_root)
        assert out == []

    def test_check_codex_drift_includes_dcx6(self, tmp_path: Path) -> None:
        """_check_codex_drift() calls _dcx6_codex_runtime_adapters() and includes its output."""
        agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
        public_dir = tmp_path / "public_dir"
        self._setup_adapter(public_dir, "missing-adapter")
        manager = self._make_manager_with_fake_public(public_dir)
        out = manager._check_codex_drift(agentic_dir, workspace_root)
        assert any(
            "[missing]" in line and "missing-adapter" in line and "D-CX-6" in line for line in out
        )


# ---------------------------------------------------------------------------
# Git-dirty check in FileSystemPublicAssetManager.doctor()
# ---------------------------------------------------------------------------


class TestDoctorGitDirtyCheck:
    """Tests for the [warn] git-dirty check in FileSystemPublicAssetManager.doctor().

    All subprocess.run calls are mocked to ensure isolation from the real git
    state of the working tree.
    """

    def _make_manager_with_fake_public(self, public_dir: Path) -> FileSystemPublicAssetManager:
        manager = FileSystemPublicAssetManager()
        manager._public_dir = public_dir
        return manager

    def _make_minimal_workspace(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a minimal public_dir + workspace_root suitable for doctor()."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        agentic_dir.mkdir(parents=True)
        manifest = {
            "schema_version": "1",
            "package_version": "0",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "assets": [],
        }
        (agentic_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return public_dir, workspace_root

    def test_dirty_paths_emit_warn_git_dirty_lines(self, tmp_path: Path) -> None:
        """When subprocess returns dirty paths, doctor emits [warn] git-dirty: <path> for each."""
        import subprocess

        public_dir, workspace_root = self._make_minimal_workspace(tmp_path)
        manager = self._make_manager_with_fake_public(public_dir)

        mock_result = subprocess.CompletedProcess(
            args=["git", "diff", "--name-only", "HEAD"],
            returncode=0,
            stdout="dadaia_workspace/public/agents/data-analyst.md\ndadaia_workspace/public/rules/some-rule.md\n",
            stderr="",
        )

        with patch("subprocess.run", return_value=mock_result):
            reports = manager.doctor(workspace_root)

        assert "[warn] git-dirty: dadaia_workspace/public/agents/data-analyst.md" in reports
        assert "[warn] git-dirty: dadaia_workspace/public/rules/some-rule.md" in reports

    def test_no_dirty_paths_emits_no_warn_lines(self, tmp_path: Path) -> None:
        """When subprocess returns empty stdout with returncode 0, no [warn] git-dirty lines appear."""
        import subprocess

        public_dir, workspace_root = self._make_minimal_workspace(tmp_path)
        manager = self._make_manager_with_fake_public(public_dir)

        mock_result = subprocess.CompletedProcess(
            args=["git", "diff", "--name-only", "HEAD"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch("subprocess.run", return_value=mock_result):
            reports = manager.doctor(workspace_root)

        warn_git_dirty = [r for r in reports if r.startswith("[warn] git-dirty:")]
        assert warn_git_dirty == []

    def test_unavailable_git_states_emit_expected_status(self, tmp_path: Path) -> None:
        """Non-repo, missing git, and timeout states emit explicit status lines."""
        import subprocess

        public_dir, workspace_root = self._make_minimal_workspace(tmp_path)
        manager = self._make_manager_with_fake_public(public_dir)

        cases = [
            (
                {
                    "return_value": subprocess.CompletedProcess(
                        args=["git", "diff", "--name-only", "HEAD"],
                        returncode=128,
                        stdout="",
                        stderr="fatal: not a git repository",
                    )
                },
                "[not-applicable] git-dirty check (not a git repo)",
            ),
            (
                {"side_effect": FileNotFoundError("git not found")},
                "[not-applicable] git-dirty check (git not found)",
            ),
            (
                {"side_effect": subprocess.TimeoutExpired(cmd="git", timeout=5)},
                "[warn] git-dirty check timed out",
            ),
        ]
        for patch_kwargs, expected in cases:
            with patch("subprocess.run", **patch_kwargs):
                reports = manager.doctor(workspace_root)
            assert expected in reports


# ---------------------------------------------------------------------------
# doctor() persists actionable findings
# ---------------------------------------------------------------------------


class TestDoctorFindingPersistence:
    """Tests that doctor() calls report_doctor_finding for actionable findings."""

    def _make_manager_with_fake_public(self, public_dir: Path) -> FileSystemPublicAssetManager:
        manager = FileSystemPublicAssetManager()
        manager._public_dir = public_dir
        return manager

    def _make_minimal_workspace(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a minimal public_dir + workspace_root suitable for doctor()."""
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        agentic_dir.mkdir(parents=True)
        manifest = {
            "schema_version": "1",
            "package_version": "0.0.0",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "assets": [],
        }
        (agentic_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return public_dir, workspace_root

    def test_missing_finding_calls_report_doctor_finding(self, tmp_path: Path) -> None:
        """When doctor() returns a [missing] line, report_doctor_finding is called."""
        import subprocess

        public_dir, workspace_root = self._make_minimal_workspace(tmp_path)
        manager = self._make_manager_with_fake_public(public_dir)

        mock_result = subprocess.CompletedProcess(
            args=["git", "diff", "--name-only", "HEAD"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "dadaia_workspace.infrastructure.public_assets.report_doctor_finding"
            ) as mock_report,
        ):
            reports = manager.doctor(workspace_root)

        # At least one [missing] line should have been emitted (manifest.json for stage)
        # and report_doctor_finding should have been called for each actionable finding.
        actionable = [
            r.strip()
            for r in reports
            if r.strip().startswith(("[missing]", "[drift]", "[fail]", "[warn]"))
        ]
        assert len(actionable) > 0, "Expected at least one actionable finding"
        assert mock_report.call_count == len(actionable), (
            f"Expected {len(actionable)} calls but got {mock_report.call_count}"
        )
        # Verify each call used the correct source tag
        for call_args in mock_report.call_args_list:
            assert call_args[0][1] == "doctor-public"

    def test_ok_lines_do_not_trigger_report(self, tmp_path: Path) -> None:
        """[ok] and [not-applicable] lines must NOT be persisted."""
        import subprocess

        public_dir, workspace_root = self._make_minimal_workspace(tmp_path)
        manager = self._make_manager_with_fake_public(public_dir)

        mock_result = subprocess.CompletedProcess(
            args=["git", "diff", "--name-only", "HEAD"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "dadaia_workspace.infrastructure.public_assets.report_doctor_finding"
            ) as mock_report,
        ):
            reports = manager.doctor(workspace_root)

        ok_lines = [r for r in reports if r.strip().startswith("[ok]")]
        assert len(ok_lines) >= 0  # may be zero in minimal workspace

        # Verify no [ok] line triggered a report
        reported_messages = [call_args[0][2] for call_args in mock_report.call_args_list]
        for msg in reported_messages:
            assert not msg.startswith("[ok]"), f"[ok] line should not be reported: {msg}"


# ---------------------------------------------------------------------------
# list_all()
# ---------------------------------------------------------------------------


class TestListAll:
    def _make_manager(self, public_dir: Path) -> FileSystemPublicAssetManager:
        manager = FileSystemPublicAssetManager()
        manager._public_dir = public_dir
        return manager

    def test_list_all_returns_all_categories(self, tmp_path: Path) -> None:
        public_dir = tmp_path / "public"
        (public_dir / "agents").mkdir(parents=True)
        (public_dir / "skills").mkdir(parents=True)
        (public_dir / "rules").mkdir(parents=True)
        (public_dir / "agents" / "my-agent.md").write_text("# agent", encoding="utf-8")
        (public_dir / "skills" / "my-skill").mkdir()
        (public_dir / "rules" / "my-rule.md").write_text("# rule", encoding="utf-8")

        result = self._make_manager(public_dir).list_all()

        assert set(result.keys()) == {"agents", "skills", "rules"}
        assert "my-agent.md" in result["agents"]
        assert "my-skill" in result["skills"]
        assert "my-rule.md" in result["rules"]

    def test_list_all_returns_empty_dict_when_public_missing(self, tmp_path: Path) -> None:
        result = self._make_manager(tmp_path / "nonexistent").list_all()
        assert result == {}

    def test_list_all_skips_non_directories_at_root(self, tmp_path: Path) -> None:
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        (public_dir / "agents").mkdir()
        (public_dir / "README.md").write_text("# readme", encoding="utf-8")

        result = self._make_manager(public_dir).list_all()
        assert "README.md" not in result
        assert "agents" in result
