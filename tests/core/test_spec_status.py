"""sa-status-line-has-two-parsers; 0.4.7 FR4 (T-047-58)."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

import dadaia_workspace
from dadaia_workspace.core.spec_status import APPROVED, CANONICAL_STATUS, extract_status

_SCRIPTS = Path(dadaia_workspace.__file__).parent / "public/skills/dd-release-implementation"
_script_extract_status = runpy.run_path(str(_SCRIPTS / "scripts/_release_schema.py"))[
    "extract_status"
]


def test_vocabulary_is_the_canonical_triple() -> None:
    assert {"Draft", "In review", "Approved"} == CANONICAL_STATUS
    assert APPROVED == "Approved"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# SPEC\n\n**Status:**   Approved\n", "Approved"),
        ("# SPEC\n\n**Status:** Approved (pending)\n", "Approved (pending)"),
        ("# TASKS\n\n**Status:** approved\n" + "- t\n" * 170, "approved"),
        ("# PLAN\n" + "text\n" * 36 + "**Status:** Approved\n", "Approved"),
        ("# SPEC\n\n**Status:** Draft\n\n**Status:** Approved\n", "Draft"),
        ("# SPEC\n\n- **Status:** Approved\n", None),
        ("# SPEC\n\n> **Status:** Approved\n", None),
        ("# SPEC\n\nthe line reads **Status:** Approved here\n", None),
        ("# SPEC\n\nno status here\n", None),
    ],
)
def test_both_status_readers_return_the_same_token(text: str, expected: str | None) -> None:
    """sa-status-line-has-two-parsers#B26-1 sa-status-line-has-two-parsers#B26-2
    sa-status-line-has-two-parsers#B26-4: first anchored line anywhere; bullet, blockquote,
    mid-line quote never count; absent is None — both readers agree."""
    assert extract_status(text) == _script_extract_status(text) == expected
