"""Unit contract for ``tests.helpers.golden_platform.norm_stderr`` — the one helper with a
caller (tests/contract/cli/test_cli_specs_init_symlink_refused.py): width-independent stderr
(the v0.1.57 Rich-width law). The other helpers have no caller; their tests were deleted
(DELETE-HOLLOW, survey cli-features).
"""

from __future__ import annotations

import pytest

from tests.helpers.golden_platform import norm_stderr

pytestmark = pytest.mark.unit


_BOXED = (
    "\x1b[31m╭─ Error ─╮\x1b[0m\n"
    "\x1b[31m│\x1b[0m No such option:  \x1b[31m│\x1b[0m\n"
    "\x1b[31m│\x1b[0m --model          \x1b[31m│\x1b[0m\n"
    "\x1b[31m╰─────────╯\x1b[0m\n"
)


def test_norm_stderr_collapses_rich_box_wrapped_output() -> None:
    out = norm_stderr(_BOXED)
    assert "No such option: --model" in out
    assert "\x1b[" not in out
    assert "│" not in out and "╭" not in out
    # The 7-site variant: box chars → space, ``\s+`` → single space (no strip).
    assert norm_stderr("│ a  b │") == " a b "
    # The policy-CLI variant: wide glyph range incl. smart quotes, stripped.
    assert norm_stderr("│ ‘a’  “b” │", wide_glyphs=True) == "a b"
    assert "No such option: --model" in norm_stderr(_BOXED, wide_glyphs=True)
