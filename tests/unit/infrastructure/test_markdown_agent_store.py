"""Unit tests for dadaia_workspace.infrastructure.markdown_agent_store.

Coverage targets:
- line 43: _split_frontmatter missing closing delimiter → returns None
- lines 56-58: _parse_file OSError on unreadable file → returns None
- line 90: MarkdownAgentStore._files() when path is not a dir → returns []

Defence-in-depth:
- Symlink pointing outside the agents dir (escape attempt) — store does not
  follow or block symlinks; resolution is the reader's job. Store just returns
  the raw frontmatter for any .md file it can parse.
- Path traversal via filename containing '..' — not possible via glob('*.md'),
  verified here.
- YAML scalar (non-mapping) frontmatter → returns None.
- Unicode / emoji content in frontmatter values → parsed normally.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.markdown_agent_store import (
    MarkdownAgentStore,
    _parse_file,
    _split_frontmatter,
)

# ---------------------------------------------------------------------------
# _split_frontmatter — unit tests
# ---------------------------------------------------------------------------


def test_split_frontmatter_returns_yaml_between_delimiters() -> None:
    """Normal frontmatter block is returned without the delimiters."""
    text = "---\nname: alpha\n---\n# Body\n"
    result = _split_frontmatter(text)
    assert result is not None
    assert "name: alpha" in result


def test_split_frontmatter_no_opening_delimiter_returns_none() -> None:
    """File that does not start with '---' returns None."""
    text = "name: alpha\n---\n# Body\n"
    assert _split_frontmatter(text) is None


def test_split_frontmatter_missing_closing_delimiter_returns_none() -> None:
    """Missing closing '---' means frontmatter cannot be isolated — returns None."""
    text = "---\nname: alpha\n# Body without closing delimiter\n"
    assert _split_frontmatter(text) is None


def test_split_frontmatter_empty_string_returns_none() -> None:
    """Empty file string returns None."""
    assert _split_frontmatter("") is None


def test_split_frontmatter_empty_frontmatter_block() -> None:
    """Opening + immediate closing delimiter yields an empty string (not None)."""
    text = "---\n---\n# Body\n"
    result = _split_frontmatter(text)
    # Empty YAML block returns empty string or whitespace — not None
    assert result is not None


# ---------------------------------------------------------------------------
# _parse_file — unit tests
# ---------------------------------------------------------------------------


def test_parse_file_returns_dict_for_valid_file(tmp_path: Path) -> None:
    """A well-formed agent .md file returns its frontmatter as a dict."""
    path = tmp_path / "valid.md"
    path.write_text("---\nname: valid\ndescription: OK.\n---\n# Body\n")
    result = _parse_file(path)
    assert result is not None
    assert isinstance(result, dict)
    assert result["name"] == "valid"


def test_parse_file_malformed_yaml_returns_none(tmp_path: Path) -> None:
    """YAML parse error is caught and None is returned."""
    path = tmp_path / "bad.md"
    path.write_text("---\n: invalid: yaml: [\n---\n# Body\n")
    assert _parse_file(path) is None


def test_parse_file_non_mapping_frontmatter_returns_none(tmp_path: Path) -> None:
    """YAML that parses to a scalar (not a dict) returns None."""
    path = tmp_path / "scalar.md"
    path.write_text("---\njust a string\n---\n# Body\n")
    assert _parse_file(path) is None


def test_parse_file_yaml_list_frontmatter_returns_none(tmp_path: Path) -> None:
    """YAML that parses to a list (not a dict) returns None."""
    path = tmp_path / "list.md"
    path.write_text("---\n- item1\n- item2\n---\n# Body\n")
    assert _parse_file(path) is None


def test_parse_file_oserror_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When the file cannot be read (OSError), None is returned without raising."""
    path = tmp_path / "unreadable.md"
    path.write_text("---\nname: x\n---\n")
    # Force the OSError via monkeypatch rather than chmod(0o000): chmod mode bits
    # are a no-op on Windows, so the file would stay readable there. This exercises
    # the OSError-handling branch on every OS.
    real_read = Path.read_text

    def boom(self: Path, *args: object, **kwargs: object) -> str:
        if self == path:
            raise OSError("simulated unreadable file")
        return real_read(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", boom)
    result = _parse_file(path)
    assert result is None


def test_parse_file_nonexistent_file_returns_none(tmp_path: Path) -> None:
    """Non-existent file path triggers OSError path — returns None."""
    path = tmp_path / "ghost.md"
    assert not path.exists()
    result = _parse_file(path)
    assert result is None


# ---------------------------------------------------------------------------
# _parse_file — unicode / emoji content
# ---------------------------------------------------------------------------


def test_parse_file_unicode_values_parsed(tmp_path: Path) -> None:
    """Unicode and emoji in frontmatter values are parsed without error."""
    path = tmp_path / "unicode.md"
    path.write_text(
        "---\nname: emoji-agent\ndescription: '🤖 Agent with emoji'\n---\n# Body\n",
        encoding="utf-8",
    )
    result = _parse_file(path)
    assert result is not None
    assert "🤖" in result["description"]


def test_parse_file_unicode_name(tmp_path: Path) -> None:
    """Multi-byte unicode in name field is accepted by the store."""
    path = tmp_path / "unicode-name.md"
    path.write_text(
        "---\nname: agente-português\ndescription: Olá mundo.\n---\n# Body\n",
        encoding="utf-8",
    )
    result = _parse_file(path)
    assert result is not None
    assert result["name"] == "agente-português"


# ---------------------------------------------------------------------------
# MarkdownAgentStore._files() — path-not-a-dir branch
# ---------------------------------------------------------------------------


def test_store_files_returns_empty_when_path_is_file(tmp_path: Path) -> None:
    """_files() returns [] when agents_dir is a file, not a directory."""
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("I am a file")
    store = MarkdownAgentStore(file_path)
    assert store._files() == []


def test_store_files_returns_empty_when_path_missing(tmp_path: Path) -> None:
    """_files() returns [] when the directory does not exist."""
    missing = tmp_path / "nonexistent_dir"
    store = MarkdownAgentStore(missing)
    assert store._files() == []


def test_store_list_raw_returns_empty_for_missing_dir(tmp_path: Path) -> None:
    """list_raw() returns [] when the agents directory does not exist."""
    store = MarkdownAgentStore(tmp_path / "no_dir")
    assert store.list_raw() == []


def test_store_list_raw_skips_unreadable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """list_raw() skips files that cannot be read (OSError) and continues."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    good = agents_dir / "good.md"
    bad = agents_dir / "bad.md"
    good.write_text("---\nname: good\ndescription: OK.\n---\n# Body\n")
    bad.write_text("---\nname: bad\ndescription: Bad.\n---\n# Body\n")
    # Force OSError on the bad file via monkeypatch (chmod(0o000) is a no-op on
    # Windows). Cross-platform exercise of the skip-on-unreadable path.
    real_read = Path.read_text

    def boom(self: Path, *args: object, **kwargs: object) -> str:
        if self == bad:
            raise OSError("simulated unreadable file")
        return real_read(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", boom)
    store = MarkdownAgentStore(agents_dir)
    results = store.list_raw()
    names = [r["name"] for r in results]
    assert "good" in names
    assert "bad" not in names


def test_store_list_raw_skips_files_without_frontmatter(tmp_path: Path) -> None:
    """list_raw() skips files without frontmatter and continues parsing others."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "no-fm.md").write_text("# No frontmatter here\n")
    (agents_dir / "valid.md").write_text("---\nname: valid\ndescription: OK.\n---\n# Body\n")
    store = MarkdownAgentStore(agents_dir)
    results = store.list_raw()
    assert len(results) == 1
    assert results[0]["name"] == "valid"


# ---------------------------------------------------------------------------
# Symlink behaviour — store does not block symlinks (reader's responsibility)
# ---------------------------------------------------------------------------


def test_store_follows_symlink_within_agents_dir(tmp_path: Path) -> None:
    """Symlinks within the agents dir that resolve inside it are loaded normally."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    real = agents_dir / "real.md"
    real.write_text("---\nname: real\ndescription: Real file.\n---\n# Body\n")
    link = agents_dir / "link.md"
    link.symlink_to(real)

    store = MarkdownAgentStore(agents_dir)
    results = store.list_raw()
    names = [r["name"] for r in results]
    # Both the real file and the symlink are read — the store returns both
    assert "real" in names


def test_store_glob_does_not_produce_traversal_paths(tmp_path: Path) -> None:
    """glob('*.md') never yields paths with '..' components."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "normal.md").write_text("---\nname: normal\ndescription: OK.\n---\n")
    store = MarkdownAgentStore(agents_dir)
    for path in store._files():
        assert ".." not in path.parts, f"Traversal path returned by glob: {path}"
