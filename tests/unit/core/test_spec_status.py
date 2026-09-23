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
    ANY_STATUS_LINE,
    APPROVED,
    APPROVED_LINE,
    CANONICAL_STATUS,
    extract_status,
    is_approved,
)

pytestmark = pytest.mark.unit


def test_vocabulary_is_the_canonical_triple() -> None:
    assert {"Draft", "In review", "Approved"} == CANONICAL_STATUS
    assert APPROVED == "Approved"
    assert APPROVED_LINE == "> **Status:** Approved"


@pytest.mark.parametrize("retired", ["Aprovado", "Em revisão", "Em revisao", "Rascunho"])
def test_the_retired_portuguese_tokens_are_not_canonical(retired: str) -> None:
    """No compatibility branch: a tree still carrying them is migrated by
    ``dadaia specs upgrade``, never quietly accepted by a second spelling."""
    assert retired not in CANONICAL_STATUS
    assert extract_status(f"# SPEC\n\n> **Status:** {retired}\n") == retired
    assert is_approved(f"# SPEC\n\n> **Status:** {retired}\n") is False


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


def test_is_approved_is_a_token_comparison_not_a_substring_test() -> None:
    # Was rejected by the substring copies, accepted by the doctor — now consistently ok.
    assert is_approved("# SPEC\n\n**Status:**  Approved\n") is True
    # Was ACCEPTED by the substring copies — an unapproved artifact passing the gate.
    assert is_approved("# SPEC\n\n> **Status:** Approved (pending review)\n") is False
    assert is_approved("# SPEC\n\n> **Status:** Draft\n") is False
    assert is_approved("# SPEC\n\nno status line\n") is False


def test_status_line_is_only_read_from_the_document_head() -> None:
    """A status token quoted deep inside prose is not the artifact's status."""
    body = "# SPEC\n" + "filler\n" * 60 + "> **Status:** Approved\n"
    assert is_approved(body) is False


@pytest.mark.parametrize(
    "line",
    [
        "> **Status:** Draft",
        "**Status:** In review",  # accent-stripped worker spelling
        "- **Status**: Approved",
        "status: draft",
        "  > **Status:**  In review  ",
    ],
)
def test_any_status_line_recognizes_every_worker_authored_variant(line: str) -> None:
    """The single-writer normalizer must strip what a worker actually writes.

    A variant it fails to strip survives into the artifact next to the Python-owned line,
    leaving two contradictory status declarations in one file.
    """
    assert ANY_STATUS_LINE.sub("", f"# SPEC\n{line}\nbody\n") == "# SPEC\n\nbody\n"


def test_any_status_line_leaves_unrelated_prose_alone() -> None:
    text = "# SPEC\n\nStatus: unknown to the vocabulary\n"
    assert ANY_STATUS_LINE.sub("", text) == text
