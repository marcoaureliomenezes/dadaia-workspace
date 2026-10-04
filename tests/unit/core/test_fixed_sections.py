"""Size: SMALL. The leaf is pure: text in, text out; every expected value is a literal."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.fixed_sections import (
    FIXED_SECTIONS,
    extract_fixed_section,
    render_fixed_section,
)

_FRAGMENT = "### Slop — tests (fixed)\n- Assert behaviour.\n- A mock exists only at the boundary.\n"
_UPDATED = "### Slop — tests (fixed)\n- Assert behaviour.\n"
_BLOCK = (
    "<!-- dadaia:fixed slop-tests -->\n"
    "### Slop — tests (fixed)\n"
    "- Assert behaviour.\n"
    "- A mock exists only at the boundary.\n"
    "<!-- /dadaia:fixed slop-tests -->\n"
)


def test_fixed_sections_table_maps_the_three_files_to_their_fragment_ids() -> None:
    assert FIXED_SECTIONS == (
        ("constitution.md", "slop-law"),
        ("memory/ARCHITECTURE.md", "slop-code"),
        ("memory/QUALITY.md", "slop-tests"),
    )


_OTHER = "<!-- dadaia:fixed slop-code -->\n### Code\n<!-- /dadaia:fixed slop-code -->\n"
_EMPTY_PAIR = "<!-- dadaia:fixed slop-tests -->\n<!-- /dadaia:fixed slop-tests -->\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("# Q\n\n### Last\nbody\n", "# Q\n\n### Last\nbody\n\n" + _BLOCK, id="absent-appends-after-a-blank-line"),
        pytest.param("", _BLOCK, id="empty-text-yields-only-the-block"),
        pytest.param("# Q\nbody", "# Q\nbody\n\n" + _BLOCK, id="missing-trailing-newline-normalized"),
        pytest.param("# Q\n\n" + _EMPTY_PAIR, "# Q\n\n" + _BLOCK, id="empty-pair-filled-in-place"),
        pytest.param("# Q\n\n" + _BLOCK.replace("- A mock exists only at the boundary.\n", "") + "\n## After\n", "# Q\n\n" + _BLOCK + "\n## After\n", id="drifted-body-replaced-surroundings-kept"),
        pytest.param(_OTHER, _OTHER + "\n" + _BLOCK, id="another-id-untouched"),
    ],
)  # fmt: skip
def test_render_fixed_section(text: str, expected: str) -> None:
    """The marked block is appended, filled or replaced — never duplicated."""
    assert render_fixed_section(text, "slop-tests", _FRAGMENT) == expected


def test_render_is_idempotent_and_a_new_fragment_replaces_only_the_body() -> None:
    """Re-rendering is a no-op; a new fragment swaps the body under the one marker pair."""
    once = render_fixed_section("# Quality\n", "slop-tests", _FRAGMENT)
    assert render_fixed_section(once, "slop-tests", _FRAGMENT) == once
    twice = render_fixed_section(once, "slop-tests", _UPDATED)
    assert extract_fixed_section(twice, "slop-tests") == _UPDATED
    assert twice.count("<!-- dadaia:fixed slop-tests -->") == 1


@pytest.mark.parametrize(
    "text, expected",
    [
        ("# Quality\n", None),
        ("<!-- dadaia:fixed slop-tests -->\n<!-- /dadaia:fixed slop-tests -->\n", ""),
        ("# Quality\n\n" + _BLOCK, _FRAGMENT),
        ("# Quality\n\n" + _BLOCK + "\n## After\n", _FRAGMENT),
        (_OTHER, None),
        ("x <!-- dadaia:fixed slop-tests -->\nbody\n<!-- /dadaia:fixed slop-tests -->\n", None),
    ],
    ids=["absent", "empty-pair", "present", "present-then-more", "other-id-only", "inline-marker"],
)
def test_extract_returns_the_body_between_the_markers(text: str, expected: str | None) -> None:
    """Only a marker pair on its own lines, of this id, yields a body."""
    assert extract_fixed_section(text, "slop-tests") == expected
