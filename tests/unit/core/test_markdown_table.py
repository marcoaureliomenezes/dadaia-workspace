"""A table cell that holds a command is still one cell.

Bug ``r24-live-definition-draft-fails-validation-table`` (validator R24 / F-26, R-01,
R-02). The row below is the one the live Codex worker actually wrote into
``f26/repos/canary/specs/releases/v0.1.0/PLAN.md``. Splitting it on every ``|``
produced seven cells, and the lint reported five-non-empty-cells as the failure even
though every cell it found was populated. The run blocked at ``definition_draft``,
retried, was told the same false thing, and never converged.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.markdown_table import split_row

pytestmark = pytest.mark.unit

_LIVE_ROW = (
    "| WS-2 | README contains `greet` usage and `Hello, Ada!` sample output section "
    '| `rg -n "\\bgreet\\b|python -m canary greet|Hello, Ada!" README.md` '
    "| WS-1 | Snapshot of updated docs section in review diff |"
)


def test_the_row_that_deadlocked_a_release_has_five_cells() -> None:
    cells = split_row(_LIVE_ROW)

    assert len(cells) == 5, (
        "the pipes live inside a code span holding an rg command; counting them as "
        "delimiters is what produced the false 'empty cells' diagnostic"
    )
    assert cells[0] == "WS-2"
    assert cells[2].startswith("`rg -n") and cells[2].endswith("README.md`")
    assert cells[3] == "WS-1"


def test_a_plain_row_is_unchanged() -> None:
    assert split_row("| WS-1 | board | unit | None | None |") == [
        "WS-1",
        "board",
        "unit",
        "None",
        "None",
    ]


def test_an_escaped_pipe_stays_inside_its_cell() -> None:
    assert split_row(r"| WS-1 | a \| b | unit | None | None |") == [
        "WS-1",
        "a | b",
        "unit",
        "None",
        "None",
    ]


def test_a_genuinely_empty_cell_is_still_empty() -> None:
    """The tolerance must not paper over the failure the gate was built to catch."""
    assert split_row("| WS-1 | board |  | None | None |") == [
        "WS-1",
        "board",
        "",
        "None",
        "None",
    ]


def test_an_unterminated_backtick_is_literal_text_not_a_span() -> None:
    """Swallowing the rest of the row into one cell would invent a cell nobody wrote."""
    assert split_row("| WS-1 | a `b | c | d | e |") == ["WS-1", "a `b", "c", "d", "e"]


def test_a_double_backtick_span_may_contain_a_single_backtick() -> None:
    cells = split_row("| WS-1 | ``a ` b|c`` | unit | None | None |")
    assert len(cells) == 5
    assert cells[1] == "``a ` b|c``"
