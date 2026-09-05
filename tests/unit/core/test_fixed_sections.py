"""Intent: CONTRACT — 0.4.6 AC11 (fixed law sections: marker grammar, render, extract).

Size: SMALL. The leaf is pure: text in, text out; every expected value is a literal.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.fixed_sections import (
    FIXED_SECTIONS,
    extract_fixed_section,
    render_fixed_section,
)

_FRAGMENT = "### Slop — tests (fixed)\n- A test is born with `Intent:`.\n- A mock exists only at the boundary.\n"
_UPDATED = "### Slop — tests (fixed)\n- A test is born with `Intent:`.\n"
_BLOCK = (
    "<!-- dadaia:fixed slop-tests -->\n"
    "### Slop — tests (fixed)\n"
    "- A test is born with `Intent:`.\n"
    "- A mock exists only at the boundary.\n"
    "<!-- /dadaia:fixed slop-tests -->\n"
)


def test_fixed_sections_table_maps_the_three_files_to_their_fragment_ids() -> None:
    assert FIXED_SECTIONS == (
        ("constitution.md", "slop-law"),
        ("memory/ARCHITECTURE.md", "slop-code"),
        ("memory/QUALITY.md", "slop-tests"),
    )


def test_render_appends_a_marked_block_after_one_blank_line_when_absent() -> None:
    text = "# Quality\n\n## Part 2\n\n### Last subsection\nbody\n"
    rendered = render_fixed_section(text, "slop-tests", _FRAGMENT)
    assert rendered == text + "\n" + _BLOCK


def test_render_on_empty_text_yields_only_the_block() -> None:
    assert render_fixed_section("", "slop-tests", _FRAGMENT) == _BLOCK


def test_render_normalizes_a_missing_trailing_newline_before_appending() -> None:
    rendered = render_fixed_section("# Quality\nbody", "slop-tests", _FRAGMENT)
    assert rendered == "# Quality\nbody\n\n" + _BLOCK


def test_render_fills_an_empty_marker_pair_in_place() -> None:
    template = "# Quality\n\n<!-- dadaia:fixed slop-tests -->\n<!-- /dadaia:fixed slop-tests -->\n"
    assert render_fixed_section(template, "slop-tests", _FRAGMENT) == "# Quality\n\n" + _BLOCK


def test_render_replaces_a_drifted_body_and_keeps_the_surrounding_text() -> None:
    drifted = (
        "# Quality\n\n"
        + _BLOCK.replace("- A mock exists only at the boundary.\n", "")
        + "\n## After\n"
    )
    rendered = render_fixed_section(drifted, "slop-tests", _FRAGMENT)
    assert rendered == "# Quality\n\n" + _BLOCK + "\n## After\n"


def test_render_is_idempotent() -> None:
    once = render_fixed_section("# Quality\n", "slop-tests", _FRAGMENT)
    assert render_fixed_section(once, "slop-tests", _FRAGMENT) == once


def test_render_of_a_new_fragment_replaces_only_the_body() -> None:
    once = render_fixed_section("# Quality\n", "slop-tests", _FRAGMENT)
    twice = render_fixed_section(once, "slop-tests", _UPDATED)
    assert extract_fixed_section(twice, "slop-tests") == _UPDATED
    assert twice.count("<!-- dadaia:fixed slop-tests -->") == 1


def test_render_leaves_a_block_of_another_id_untouched() -> None:
    other = "<!-- dadaia:fixed slop-code -->\n### Code\n<!-- /dadaia:fixed slop-code -->\n"
    rendered = render_fixed_section(other, "slop-tests", _FRAGMENT)
    assert rendered == other + "\n" + _BLOCK


@pytest.mark.parametrize(
    "text, expected",
    [
        ("# Quality\n", None),
        ("<!-- dadaia:fixed slop-tests -->\n<!-- /dadaia:fixed slop-tests -->\n", ""),
        ("# Quality\n\n" + _BLOCK, _FRAGMENT),
        ("# Quality\n\n" + _BLOCK + "\n## After\n", _FRAGMENT),
        ("<!-- dadaia:fixed slop-code -->\n### Code\n<!-- /dadaia:fixed slop-code -->\n", None),
    ],
    ids=["absent", "empty-pair", "present", "present-then-more", "other-id-only"],
)
def test_extract_returns_the_body_between_the_markers(text: str, expected: str | None) -> None:
    assert extract_fixed_section(text, "slop-tests") == expected


def test_extract_requires_the_markers_on_their_own_lines() -> None:
    inline = "x <!-- dadaia:fixed slop-tests -->\nbody\n<!-- /dadaia:fixed slop-tests -->\n"
    assert extract_fixed_section(inline, "slop-tests") is None
