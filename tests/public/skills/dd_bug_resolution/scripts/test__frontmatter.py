"""The kernel's one frontmatter grammar (ADR 0246): a stdlib strict subset of YAML that
equals ``yaml.safe_load`` or refuses. ``split(text)`` returns ``(block, body)`` or ``None``;
``parse(block)`` returns the mapping or raises ``ValueError`` naming ``line N``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.skill_owner import load_owner

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
    lf = _PERSONA.read_text(encoding="utf-8")
    parsed = _load(lf.replace("\n", "\r\n"))
    assert parsed == _load(lf)
    assert parsed["dispatch_band"] == 3
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
