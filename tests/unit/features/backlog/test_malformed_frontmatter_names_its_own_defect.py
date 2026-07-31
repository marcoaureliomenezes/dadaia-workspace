"""Each way of breaking frontmatter must be diagnosed as the thing it actually is.

Recipe item R-24, which the consumer-side validator has never managed to observe: in round
24 all three malformed variants blocked on a nested-container sandbox limit before the
parser was ever reached, so R-24 returned EXCEPTION with no product conclusion. It costs a
live worker every round and has yet to produce one.

There is no reason for that. The parser is pure text in, text out. Proving it here takes
milliseconds and holds on every run, which is what the recipe wanted in the first place —
the live item can then be about the *workflow* reaching the parser, not about the parser.

Both directions are covered, and the second matters as much as the first. Recipe R-27: a
gate must name the defect it found AND must accept the honest answer to its own question. A
Markdown horizontal rule after prose is an ordinary thing to write, and calling it malformed
would be worse than missing a real one — nothing the author changes would make it go away.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.backlog.preview import _parse_frontmatter

pytestmark = pytest.mark.unit


def test_an_unterminated_block_is_called_unterminated() -> None:
    data, error = _parse_frontmatter("---\nslug: a\ntitle: b\n\n# body\n")

    assert data is None
    assert error is not None and "unterminated" in error, error


def test_a_closing_delimiter_with_no_opening_one_says_so() -> None:
    """Distinct from the above: the same file, broken at the other end.

    Bug ``r22-live-backlog-author-accepts-unterminated-frontmatter`` was fixed for one of
    these shapes; this pins that the other shape is diagnosed as itself, not folded into
    the first message. An author told the wrong half is looking at the wrong line.
    """
    data, error = _parse_frontmatter("slug: a\ntitle: b\n---\n\n# body\n")

    assert data is None
    assert error is not None and "opening delimiter" in error, error


def test_unparseable_yaml_carries_the_line_and_column() -> None:
    data, error = _parse_frontmatter("---\nslug: a\n  bad: [unclosed\ntitle: b\n---\n\n# body\n")

    assert data is None
    assert error is not None
    assert "line 3" in error and "column" in error, (
        f"the author has to be sent to the offending line, not just told 'invalid': {error}"
    )


def test_a_horizontal_rule_in_the_body_is_not_a_broken_block() -> None:
    """The false-positive guard. A gate with no correct input has no escape."""
    data, error = _parse_frontmatter(
        "---\nslug: a\ntitle: b\n---\n\n# body\n\nprose\n\n---\n\nmore prose\n"
    )

    assert error is None, error
    assert data == {"slug": "a", "title": "b"}


def test_a_well_formed_item_parses() -> None:
    data, error = _parse_frontmatter("---\nslug: a\ntitle: b\n---\n\n# body\n")

    assert error is None and data == {"slug": "a", "title": "b"}
