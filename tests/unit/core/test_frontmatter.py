"""``core.frontmatter`` — the ONE frontmatter parser (v0.5.1 T-051-16, K10).

Table-driven over :func:`parse`'s five outcome shapes: valid, missing delimiter,
invalid YAML (with the line number), missing required field(s) (via
:func:`missing_fields`, the memory-atom 6-field contract), and a present-but-non-dict
block. Regression coverage for bug
``memory-lint-blames-missing-delimiter-for-a-yaml-parse-error`` (kind distinguishes
"no block" from "block present, invalid YAML") and the checker half of bug
``memory-trio-missing-required-frontmatter-fields`` (``missing_fields`` names every
absent field, not just the first).

Intent: CONTRACT — v0.5.1 A10.2/A10.3.
Size: SMALL — pure-function unit tests, no I/O.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.frontmatter import Frontmatter, FrontmatterError, missing_fields, parse

#: The memory-atom 6-field contract (DADAIA.md §6.4).
_MEMORY_REQUIRED_FIELDS: tuple[str, ...] = (
    "slug",
    "title",
    "category",
    "tldr",
    "summary",
    "tags",
)


def test_valid_frontmatter_returns_data_and_body() -> None:
    text = "---\nslug: x\ntitle: X\n---\n\n## Body\n\nHello.\n"

    result = parse(text)

    assert isinstance(result, Frontmatter)
    assert result.data == {"slug": "x", "title": "X"}
    assert result.body == "\n## Body\n\nHello.\n"


def test_frontmatter_block_may_be_the_whole_file_no_trailing_newline() -> None:
    text = "---\nslug: x\n---"

    result = parse(text)

    assert isinstance(result, Frontmatter)
    assert result.data == {"slug": "x"}
    assert result.body == ""


def test_missing_delimiter_is_named_as_missing_delimiter_not_invalid_yaml() -> None:
    text = "# Just a heading\n\nNo frontmatter block here.\n"

    result = parse(text)

    assert isinstance(result, FrontmatterError)
    assert result.kind == "missing_delimiter"
    assert "delimited block" in result.message


def test_invalid_yaml_in_a_present_block_names_the_line_never_the_delimiter() -> None:
    """Bug memory-lint-blames-missing-delimiter-for-a-yaml-parse-error: an unquoted
    scalar containing ': ' breaks the YAML on line 2 of the block; the block itself
    IS present, so the diagnostic must never claim it is missing."""
    text = "---\nslug: x\ntldr: Two-tier memory: 17 principles\n---\n\nBody.\n"

    result = parse(text)

    assert isinstance(result, FrontmatterError)
    assert result.kind == "invalid_yaml"
    assert "delimited block" not in result.message
    assert result.line == 2


def test_non_mapping_frontmatter_is_named_not_a_mapping() -> None:
    text = "---\n- just\n- a\n- list\n---\n\nBody.\n"

    result = parse(text)

    assert isinstance(result, FrontmatterError)
    assert result.kind == "not_a_mapping"


def test_missing_fields_reports_every_absent_field_not_just_the_first() -> None:
    """Checker half of bug memory-trio-missing-required-frontmatter-fields."""
    data = {"category": "core"}

    absent = missing_fields(data, _MEMORY_REQUIRED_FIELDS)

    assert absent == ["slug", "title", "tldr", "summary", "tags"]


def test_missing_fields_is_empty_when_the_six_field_contract_is_satisfied() -> None:
    data = {
        "slug": "x",
        "title": "X",
        "category": "core",
        "tldr": "t",
        "summary": "s",
        "tags": [],
    }

    assert missing_fields(data, _MEMORY_REQUIRED_FIELDS) == []


@pytest.mark.parametrize(
    ("text", "expected_kind"),
    [
        pytest.param("no delimiter at all\n", "missing_delimiter", id="no-delimiter"),
        pytest.param("---\nkey: [unterminated\n---\n", "invalid_yaml", id="bad-yaml"),
        pytest.param("---\nscalar-not-a-mapping\n---\n", "not_a_mapping", id="scalar"),
    ],
)
def test_parse_error_kinds_table(text: str, expected_kind: str) -> None:
    result = parse(text)

    assert isinstance(result, FrontmatterError)
    assert result.kind == expected_kind
