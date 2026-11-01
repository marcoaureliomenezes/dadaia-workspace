"""The one frontmatter grammar: a stdlib strict subset of YAML that
equals ``yaml.safe_load`` or refuses. ``split(text)`` returns ``(block, body)`` or ``None``;
``parse(block)`` returns the mapping or raises ``ValueError`` naming ``line N``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import read_text

_PERSONA = (
    Path(__file__).resolve().parents[5] / "dadaia_workspace/public/agents/dd-sw-engineer-sr.md"
)


def _load(doc: str) -> dict[str, Any]:
    fm = load_owner("dd-bug-resolution", "_frontmatter")
    split = fm.split(doc)
    assert split is not None
    parsed: dict[str, Any] = fm.parse(split[0])
    return parsed


def test_a_bom_constitution_keeps_its_gitflow_block() -> None:
    doc = (
        '\ufeff---\nconstitution_version: 7.0.0\ngitflow: {"principal": "main", '
        '"work": "feature/"}\n---\n\n# body\n'
    )
    assert _load(doc) == {
        "constitution_version": "7.0.0",
        "gitflow": {"principal": "main", "work": "feature/"},
    }


def test_a_crlf_persona_keeps_every_field_of_its_lf_twin() -> None:
    lf = read_text(_PERSONA)
    parsed = _load(lf.replace("\n", "\r\n"))
    assert parsed == _load(lf)
    assert parsed["read_only"] is False
    assert parsed["name"] == "dd-sw-engineer-sr"
    assert parsed["tools"][:2] == ["Read", "Write"]


def test_a_folded_last_key_has_no_trailing_newline_and_a_middle_one_has() -> None:
    assert _load("---\na: >\n  one\n  two\nb: >\n  three\n  four\n---\n") == {
        "a": "one two\n",
        "b": "three four",
    }
    assert _load("---\na: >-\n  one\n  two\nb: 1\n---\n") == {"a": "one two", "b": 1}


def test_a_dotted_version_is_a_string_and_typed_scalars_stay_typed() -> None:
    assert _load("---\nv: 7.0.0\nn: 12\nt: true\nz: null\ns: 'it''s'\nd: \"a\\tb\"\n---\n") == {
        "v": "7.0.0",
        "n": 12,
        "t": True,
        "z": None,
        "s": "it's",
        "d": "a\tb",
    }


@pytest.mark.parametrize("scalar", ["yes", "0755", "2026-10-11", "1_000", "~"])
def test_a_yaml_1_1_ambiguous_plain_scalar_is_refused(scalar: str) -> None:
    fm = load_owner("dd-bug-resolution", "_frontmatter")
    with pytest.raises(ValueError, match="line 1"):
        fm.parse(f"k: {scalar}")


@pytest.mark.parametrize(
    "block",
    ["a: 1\na: 2", "a:\t1", "a: &x 1", "a: *x", "a: !!str 1", "a: |\n  x"],
    ids=["duplicate-key", "tab", "anchor", "alias", "tag", "literal-block"],
)
def test_a_shape_outside_the_subset_is_refused(block: str) -> None:
    fm = load_owner("dd-bug-resolution", "_frontmatter")
    with pytest.raises(ValueError, match=r"line [12]"):
        fm.parse(block)


def test_a_trailing_comment_after_a_value_is_dropped_like_safe_load_does() -> None:
    assert _load(
        "---\nv: 6.0.0  # note\nq: \"x\" # c\nl:\n  - a # c\n  - 'b'  # d\nh: a#b\n---\n"
    ) == {
        "v": "6.0.0",
        "q": "x",
        "l": ["a", "b"],
        "h": "a#b",
    }
    fm = load_owner("dd-bug-resolution", "_frontmatter")
    with pytest.raises(ValueError, match="line 1"):
        fm.parse('q: "x"# c')


def test_a_full_line_comment_is_refused() -> None:
    fm = load_owner("dd-bug-resolution", "_frontmatter")
    with pytest.raises(ValueError, match="line 2"):
        fm.parse("a: 1\n# note\nb: 2")


_SPANS_BLOCK = (
    "name: a\n"
    "tools:\n"
    "  - Read\n"
    "  - Edit\n"
    "list:\n"
    "- x\n"
    "- y\n"
    "gitflow:\n"
    "  principal: main\n"
    "\n"
    "flow: [a, b]\n"
    "note: >\n"
    "  folded\n"
    "  text\n"
    "last: 1"
)


def _spans(doc: str) -> list[tuple[str | None, list[str]]]:
    fm = load_owner("dd-bug-resolution", "_frontmatter")
    split = fm.split(doc)
    assert split is not None
    spans: list[tuple[str | None, list[str]]] = fm.key_spans(split[0])
    return spans


def test_a_key_span_is_the_key_line_and_every_line_of_its_block_value() -> None:
    assert _spans(f"---\n{_SPANS_BLOCK}\n---\n") == [
        ("name", ["name: a"]),
        ("tools", ["tools:", "  - Read", "  - Edit"]),
        ("list", ["list:", "- x", "- y"]),
        ("gitflow", ["gitflow:", "  principal: main", ""]),
        ("flow", ["flow: [a, b]"]),
        ("note", ["note: >", "  folded", "  text"]),
        ("last", ["last: 1"]),
    ]


def test_the_key_spans_rejoin_to_the_block_they_came_from() -> None:
    spans = _spans(f"---\n{_SPANS_BLOCK}\n---\n")

    assert "\n".join(line for _key, lines in spans for line in lines) == _SPANS_BLOCK


@pytest.mark.parametrize("prefix", ["", "﻿"])
@pytest.mark.parametrize("eol", ["\n", "\r\n"])
def test_the_key_spans_are_the_same_for_lf_crlf_and_bom_documents(prefix: str, eol: str) -> None:
    doc = f"---\n{_SPANS_BLOCK}\n---\n"
    twin = prefix + doc.replace("\n", eol)

    assert _spans(twin) == _spans(doc)


def test_lines_before_the_first_key_belong_to_no_key() -> None:
    fm = load_owner("dd-bug-resolution", "_frontmatter")

    assert fm.key_spans("  - orphan\na: 1") == [(None, ["  - orphan"]), ("a", ["a: 1"])]
