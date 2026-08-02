"""A document must not be able to say two different things about its own status.

Bug ``r23-live-release-definition-completes-with-draft-artifacts`` (validator R23, F-26,
live Codex chain): the release completed, ``final_phase`` was ``implementation``, and
SPEC.md and PLAN.md both still read ``## Status: Draft``. The validator called it a false
completed state, which is exactly what it is.

The single-writer law over the status token was written for the shapes a worker had
produced so far — bulleted, blockquoted, bold or not. A live model then wrote it as a
Markdown HEADING, which is a completely ordinary thing to do, and the strip did not see
it. Python inserted its canonical ``> **Status:** Aprovado`` and left the heading sitting
above it, so the file simultaneously claimed Draft to a human and Aprovado to the gate.

Two failures, one root: the normalizer enumerated prefixes instead of ruling on them, and
the reader could not see the form the normalizer had missed. Fixing only the first would
leave a document that lies to whichever reader looks at the other line, so both move:
strip the heading form, and — for anything that still slips through — refuse to call a
document approved while it also declares something else.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.spec_status import (
    ANY_STATUS_LINE,
    APPROVED_LINE,
    extract_status,
    is_approved,
)

pytestmark = pytest.mark.unit

_HEADING_FORMS = (
    "# Status: Draft",
    "## Status: Draft",
    "### Status: Em revisão",
    "## **Status:** Draft",
    "##   Status:   Draft",
)


@pytest.mark.parametrize("line", _HEADING_FORMS)
def test_a_heading_status_is_a_status_line(line: str) -> None:
    """The normalizer must recognise it, or it cannot strip it."""
    assert ANY_STATUS_LINE.search(line), (
        f"{line!r} was invisible to the single-writer normalizer, so Python's canonical "
        "line was inserted ALONGSIDE it and the artifact carried two contradictory claims"
    )


@pytest.mark.parametrize("line", _HEADING_FORMS)
def test_stripping_leaves_only_pythons_canonical_line(line: str) -> None:
    document = f"# SPEC\n\n{line}\n\nbody\n"
    stripped = ANY_STATUS_LINE.sub("", document)
    assert "Draft" not in stripped and "Em revisão" not in stripped, stripped
    assert is_approved(f"{stripped}\n{APPROVED_LINE}\n")


def test_a_document_claiming_both_is_not_approved() -> None:
    """The backstop, for any prefix nobody has thought of yet.

    An enumerated list of shapes is always one live worker behind. If a status form does
    slip past the normalizer again, the answer to "is this approved?" must be NO — a
    document that contradicts itself is not evidence of a completed review, and letting it
    through is precisely how a release reached IMPLEMENTATION over artifacts that read
    Draft.
    """
    document = f"# SPEC\n\n## Status: Draft\n\n{APPROVED_LINE}\n\nbody\n"
    assert not is_approved(document), (
        "the gate read the canonical line and ignored the Draft heading above it, so it "
        "approved a document a human reads as unapproved"
    )


def test_the_ordinary_approved_document_still_passes() -> None:
    """Guard: the whole point is to stop a contradiction, not to stop approval."""
    assert is_approved(f"# SPEC\n\n{APPROVED_LINE}\n\nbody\n")
    assert extract_status(f"# SPEC\n\n{APPROVED_LINE}\n") == "Aprovado"


def test_prose_mentioning_a_status_word_is_not_a_status_line() -> None:
    """Guard against widening the rule until ordinary text trips it.

    A false positive here blocks a legitimate artifact over a sentence, which the operator
    cannot fix by changing anything that matters.
    """
    document = (
        f"# SPEC\n\n{APPROVED_LINE}\n\n"
        "## Rollout\n\nThe Draft phase ends when review completes. Status: see above.\n"
    )
    assert is_approved(document), document
