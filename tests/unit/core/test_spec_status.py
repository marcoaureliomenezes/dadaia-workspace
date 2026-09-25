"""``core.spec_status`` — the one definition of the SDD status vocabulary.

These tests pin the behaviour the four former copies disagreed on. Three sites used
``"**Status:** Approved" in text``; that substring test is wrong in both directions, and
the doctor (which parsed the line properly) enforced something different — the drift that
makes a gate look too-permissive and too-strict at the same time.

The vocabulary is English-only since 0.4.7 FR4 (T-047-58): the retired Portuguese tokens
are not a second accepted spelling — ``specs upgrade`` rewrites a live tree instead.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.spec_status import (
    APPROVED,
    CANONICAL_STATUS,
    extract_status,
)

pytestmark = pytest.mark.unit


def test_vocabulary_is_the_canonical_triple() -> None:
    assert {"Draft", "In review", "Approved"} == CANONICAL_STATUS
    assert APPROVED == "Approved"


@pytest.mark.parametrize("retired", ["Aprovado", "Em revisão", "Em revisao", "Rascunho"])
def test_the_retired_portuguese_tokens_are_not_canonical(retired: str) -> None:
    """No compatibility branch: a tree still carrying them is migrated by
    ``dadaia specs upgrade``, never quietly accepted by a second spelling."""
    assert retired not in CANONICAL_STATUS
    assert extract_status(f"# SPEC\n\n> **Status:** {retired}\n") == retired


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# SPEC\n\n> **Status:** Approved\n", "Approved"),
        ("# SPEC\n\n**Status:**   Approved\n", "Approved"),  # substring test would miss
        ("# SPEC\n\n> **Status:** Approved (pending)\n", "Approved (pending)"),
        ("# SPEC\n\n> **Status:** Draft\n", "Draft"),
        ("# SPEC\n\nno status here\n", None),
    ],
)
def test_extract_status_returns_the_token_verbatim(text: str, expected: str | None) -> None:
    """Verbatim so a caller can distinguish 'absent' from 'declared but not canonical'."""
    assert extract_status(text) == expected
