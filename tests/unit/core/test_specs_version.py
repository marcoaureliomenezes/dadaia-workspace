"""Intent: CONTRACT — AC6.2 (T-050-11): the constitution gitflow reads back; one merge-writer
keeps every other key and the body byte-identical. Bug
upgrade-leaves-project-specs-unmigrated-and-silent: the canon a tree must meet is pinned
to ``CANONICAL_SPECS_VERSION``."""

from __future__ import annotations

import hashlib
from pathlib import Path

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.fixed_sections import FIXED_SECTIONS
from dadaia_workspace.core.gitflow import DEFAULT, Gitflow, merge_frontmatter, read_gitflow
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION, state

_CUSTOM = Gitflow(principal="trunk", integration="next", work_prefix="work/")


def _write(tmp_path: Path, text: str) -> Path:
    (tmp_path / "constitution.md").write_text(text, encoding="utf-8")
    return tmp_path


#: The canon fingerprint each stamp was cut at — re-pinned only together with a stamp bump.
_CANON_AT = {8: "ebc460dd444fd523"}


def test_a_canon_change_bumps_the_stamp() -> None:
    """The stamp and the doctor's canon are one decision: what the doctor judges on an
    existing tree — the fixed fragments and FIXED_SECTIONS, the refreshed area laws
    (TREE-5), the canon registry and the default gitflow block. The copy-once seeds
    (memory documents, product index) are never re-judged, so they are not pinned."""
    public = workspace_layout.public_scripts_dir().parent
    laws = [public / "templates" / "specs-AGENTS.md"] + [
        public / "scaffold" / area / "AGENTS.md" for area in workspace_layout.SCOPED_LAW_AREAS
    ]
    digest = hashlib.sha256()
    fixed = sorted((public / "data" / "fixed").glob("*.md"), key=Path.as_posix)
    for path in [*fixed, *laws]:
        digest.update(f"{path.relative_to(public).as_posix()}\n".encode() + path.read_bytes())
    digest.update(
        repr((workspace_layout.specs_canon_table_rows(), FIXED_SECTIONS, DEFAULT)).encode()
    )
    assert {CANONICAL_SPECS_VERSION: digest.hexdigest()[:16]} == _CANON_AT, (
        "the canon changed: bump CANONICAL_SPECS_VERSION, then pin under the new key; "
        "never re-pin an existing key"
    )


def test_gitflow_round_trips(tmp_path: Path) -> None:
    specs = _write(tmp_path, "---\nspecs_pattern_version: 8\n---\n# C\n")
    merge_frontmatter(specs, gitflow=_CUSTOM)
    assert read_gitflow(specs) == (_CUSTOM, None)
    assert state(specs)[0] == "canonical"


def test_merge_preserves_unknown_keys_and_body(tmp_path: Path) -> None:
    body = "\n# Constitution\n\n  weird   spacing: kept\n---\ntrailing\n"
    specs = _write(
        tmp_path,
        "---\nspecs_pattern_version: 6\nconstitution_version: 6.0.0  # note\n"
        "owner:\n  - a\n  - b\n---" + body,
    )
    merge_frontmatter(specs, specs_pattern_version=8, gitflow=DEFAULT)
    text = (specs / "constitution.md").read_text(encoding="utf-8")
    assert text.endswith("---" + body)
    assert "constitution_version: 6.0.0  # note\nowner:\n  - a\n  - b\n" in text
    assert state(specs)[0] == "canonical"
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
