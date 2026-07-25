"""``core.spec_status`` — the one definition of the SDD status vocabulary.

These tests pin the behaviour the four former copies disagreed on. Three sites used
``"**Status:** Aprovado" in text``; that substring test is wrong in both directions, and
the doctor (which parsed the line properly) enforced something different — the drift that
makes a gate look too-permissive and too-strict at the same time.
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
    assert {"Draft", "Em revisão", "Aprovado"} == CANONICAL_STATUS
    assert APPROVED == "Aprovado"
    assert APPROVED_LINE == "> **Status:** Aprovado"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# SPEC\n\n> **Status:** Aprovado\n", "Aprovado"),
        ("# SPEC\n\n**Status:**   Aprovado\n", "Aprovado"),  # substring test would miss
        ("# SPEC\n\n> **Status:** Aprovado (pendente)\n", "Aprovado (pendente)"),
        ("# SPEC\n\n> **Status:** Draft\n", "Draft"),
        ("# SPEC\n\nno status here\n", None),
    ],
)
def test_extract_status_returns_the_token_verbatim(text: str, expected: str | None) -> None:
    """Verbatim so a caller can distinguish 'absent' from 'declared but not canonical'."""
    assert extract_status(text) == expected


def test_is_approved_is_a_token_comparison_not_a_substring_test() -> None:
    # Was rejected by the substring copies, accepted by the doctor — now consistently ok.
    assert is_approved("# SPEC\n\n**Status:**  Aprovado\n") is True
    # Was ACCEPTED by the substring copies — an unapproved artifact passing the gate.
    assert is_approved("# SPEC\n\n> **Status:** Aprovado (pendente de review)\n") is False
    assert is_approved("# SPEC\n\n> **Status:** Draft\n") is False
    assert is_approved("# SPEC\n\nno status line\n") is False


def test_status_line_is_only_read_from_the_document_head() -> None:
    """A status token quoted deep inside prose is not the artifact's status."""
    body = "# SPEC\n" + "filler\n" * 60 + "> **Status:** Aprovado\n"
    assert is_approved(body) is False


@pytest.mark.parametrize(
    "line",
    [
        "> **Status:** Draft",
        "**Status:** Em revisao",  # accent-stripped worker spelling
        "- **Status**: Aprovado",
        "status: draft",
        "  > **Status:**  Em revisão  ",
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
