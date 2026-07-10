"""Unit tests for dadaia_workspace.infrastructure.markdown_agent_store.

Coverage targets:
- _split_frontmatter delimiter matrix (missing open/close, empty, empty block).
- _parse_file malformed/non-mapping/OSError/unicode matrix.
- MarkdownAgentStore._files()/list_raw() path-not-a-dir, skip-unreadable,
  skip-no-frontmatter, and symlink-follow behaviors.

Defence-in-depth notes:
- Symlink pointing outside the agents dir (escape attempt) — store does not
  follow or block symlinks; resolution is the reader's job. Store just returns
  the raw frontmatter for any .md file it can parse.
- Unicode / emoji content in frontmatter values is parsed normally.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.markdown_agent_store import (
    MarkdownAgentStore,
    _parse_file,
    _split_frontmatter,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("---\nname: alpha\n---\n# Body\n", "name: alpha", id="normal-block"),
        pytest.param("name: alpha\n---\n# Body\n", None, id="no-opening-delimiter"),
        pytest.param(
            "---\nname: alpha\n# Body without closing delimiter\n",
            None,
            id="missing-closing-delimiter",
        ),
        pytest.param("", None, id="empty-string"),
        pytest.param("---\n---\n# Body\n", "", id="empty-frontmatter-block"),
    ],
)
def test_split_frontmatter(text: str, expected: str | None) -> None:
    result = _split_frontmatter(text)
    if expected is None:
        assert result is None
    elif expected == "":
        # Empty YAML block returns empty/whitespace string — not None.
        assert result is not None
    else:
        assert result is not None
        assert expected in result


def test_parse_file_shape_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A well-formed file parses to a dict; malformed YAML, a non-mapping (scalar or
    list) frontmatter, an OSError while reading (including a nonexistent file), and
    unicode/emoji values are all exercised in one function."""
    valid = tmp_path / "valid.md"
    valid.write_text("---\nname: valid\ndescription: OK.\n---\n# Body\n")
    result = _parse_file(valid)
    assert result is not None and isinstance(result, dict)
    assert result["name"] == "valid"

    bad_yaml = tmp_path / "bad.md"
    bad_yaml.write_text("---\n: invalid: yaml: [\n---\n# Body\n")
    assert _parse_file(bad_yaml) is None

    scalar = tmp_path / "scalar.md"
    scalar.write_text("---\njust a string\n---\n# Body\n")
    assert _parse_file(scalar) is None

    yaml_list = tmp_path / "list.md"
    yaml_list.write_text("---\n- item1\n- item2\n---\n# Body\n")
    assert _parse_file(yaml_list) is None

    ghost = tmp_path / "ghost.md"
    assert not ghost.exists()
    assert _parse_file(ghost) is None

    # Force an OSError via monkeypatch rather than chmod(0o000): chmod mode bits are
    # a no-op on Windows, so the file would stay readable there.
    unreadable = tmp_path / "unreadable.md"
    unreadable.write_text("---\nname: x\n---\n")
    real_read = Path.read_text

    def boom(self: Path, *args: object, **kwargs: object) -> str:
        if self == unreadable:
            raise OSError("simulated unreadable file")
        return real_read(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", boom)
    assert _parse_file(unreadable) is None
    monkeypatch.undo()

    unicode_path = tmp_path / "unicode.md"
    unicode_path.write_text(
        "---\nname: agente-português\ndescription: '🤖 Agent with emoji'\n---\n# Body\n",
        encoding="utf-8",
    )
    unicode_result = _parse_file(unicode_path)
    assert unicode_result is not None
    assert "🤖" in unicode_result["description"]
    assert unicode_result["name"] == "agente-português"


def test_store_files_and_list_raw_behavior_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_files()/list_raw() return [] when the target path is a file or missing;
    list_raw() skips an unreadable file and a file without frontmatter while still
    returning the valid ones; and a symlink within the agents dir is followed
    normally (store does not block symlinks — that is the reader's job)."""
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("I am a file")
    assert MarkdownAgentStore(file_path)._files() == []

    missing = tmp_path / "nonexistent_dir"
    assert MarkdownAgentStore(missing)._files() == []
    assert MarkdownAgentStore(missing).list_raw() == []

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    good = agents_dir / "good.md"
    bad = agents_dir / "bad.md"
    good.write_text("---\nname: good\ndescription: OK.\n---\n# Body\n")
    bad.write_text("---\nname: bad\ndescription: Bad.\n---\n# Body\n")
    (agents_dir / "no-fm.md").write_text("# No frontmatter here\n")
    real = agents_dir / "real.md"
    real.write_text("---\nname: real\ndescription: Real file.\n---\n# Body\n")
    (agents_dir / "link.md").symlink_to(real)

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
    assert "real" in names  # real.md AND link.md (symlink followed) both resolve to "real"
    assert names.count("real") == 2
    assert "bad" not in names  # unreadable file skipped
    # no-fm.md contributes nothing: total entries = good + real + real(symlink)
    assert len(results) == 3
