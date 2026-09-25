"""Intent: CONTRACT — AC6.2 (T-050-11): the constitution gitflow reads back; one merge-writer
keeps every other key and the body byte-identical."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.gitflow import DEFAULT, Gitflow
from dadaia_workspace.core.specs_version import (
    merge_frontmatter,
    read_gitflow,
    read_pattern_version,
)

_CUSTOM = Gitflow(principal="trunk", integration="next", work_prefix="work/")


def _write(tmp_path: Path, text: str) -> Path:
    (tmp_path / "constitution.md").write_text(text, encoding="utf-8")
    return tmp_path


def test_gitflow_round_trips(tmp_path: Path) -> None:
    specs = _write(tmp_path, "---\nspecs_pattern_version: 7\n---\n# C\n")
    merge_frontmatter(specs, gitflow=_CUSTOM)
    assert read_gitflow(specs) == (_CUSTOM, None)
    assert read_pattern_version(specs) == 7


def test_merge_preserves_unknown_keys_and_body(tmp_path: Path) -> None:
    body = "\n# Constitution\n\n  weird   spacing: kept\n---\ntrailing\n"
    specs = _write(
        tmp_path,
        "---\nspecs_pattern_version: 6\nconstitution_version: 6.0.0  # note\n"
        "owner:\n  - a\n  - b\n---" + body,
    )
    merge_frontmatter(specs, specs_pattern_version=7, gitflow=DEFAULT)
    text = (specs / "constitution.md").read_text(encoding="utf-8")
    assert text.endswith("---" + body)
    assert "constitution_version: 6.0.0  # note\nowner:\n  - a\n  - b\n" in text
    assert read_pattern_version(specs) == 7
    assert read_gitflow(specs) == (DEFAULT, None)


def test_merge_is_idempotent(tmp_path: Path) -> None:
    specs = _write(tmp_path, "---\nx: 1\n---\nbody\n")
    merge_frontmatter(specs, gitflow=_CUSTOM)
    once = (specs / "constitution.md").read_text(encoding="utf-8")
    merge_frontmatter(specs, gitflow=_CUSTOM)
    assert (specs / "constitution.md").read_text(encoding="utf-8") == once


def test_merge_replaces_a_block_style_gitflow(tmp_path: Path) -> None:
    specs = _write(
        tmp_path,
        "---\ngitflow:\n  principal: main\n  integration: develop\n  work: feature/\nz: 2\n---\nb\n",
    )
    merge_frontmatter(specs, gitflow=_CUSTOM)
    text = (specs / "constitution.md").read_text(encoding="utf-8")
    assert text.count("principal") == 1
    assert "\nz: 2\n" in text
    assert read_gitflow(specs) == (_CUSTOM, None)


def test_merge_prepends_a_block_when_absent(tmp_path: Path) -> None:
    specs = _write(tmp_path, "# no frontmatter\n")
    merge_frontmatter(specs, specs_pattern_version=7)
    assert (specs / "constitution.md").read_text(encoding="utf-8") == (
        "---\nspecs_pattern_version: 7\n---\n# no frontmatter\n"
    )


def test_absent_block_is_default_with_warning(tmp_path: Path) -> None:
    specs = _write(tmp_path, "---\nspecs_pattern_version: 7\n---\n")
    flow, warning = read_gitflow(specs)
    assert flow == DEFAULT
    assert warning is not None and "gitflow" in warning


def test_missing_constitution_is_default_with_warning(tmp_path: Path) -> None:
    flow, warning = read_gitflow(tmp_path)
    assert flow == DEFAULT
    assert warning is not None


def test_malformed_block_is_default_with_warning(tmp_path: Path) -> None:
    specs = _write(tmp_path, "---\ngitflow: {principal: main, integration: main, work: x/}\n---\n")
    flow, warning = read_gitflow(specs)
    assert flow == DEFAULT
    assert warning is not None and "integration" in warning
