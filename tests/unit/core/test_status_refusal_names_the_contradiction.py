"""Refusing an artifact must say what is wrong WITH THE ARTIFACT, not just "not Aprovado".

Recipe R-27 — the item no round has ever proven — asks whether a gate names the defect it
actually found. Driving the terminal gate against a self-contradicting PLAN.md gave:

    definition_commit_gate: release artifacts are not persisted/approved on disk:
    PLAN.md (not Aprovado)

while the file's line 3 reads ``> **Status:** Aprovado``. An author opens it, sees Aprovado
at the top, and concludes the gate is wrong. The real defect — a second, contradictory
``## **Status:** Draft`` further down — is never mentioned, so nothing they can see explains
the refusal.

This is the same class that deadlocked a live release in round 24, where the plan lint
reported "every row must contain all five non-empty cells" about a row whose cells were all
populated. A message the author cannot act on turns a correct refusal into a loop, because
each retry rewrites the part that was already right.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.spec_status import contradicting_status_lines, is_approved

pytestmark = pytest.mark.unit

_CONTRADICTORY = "# PLAN\n\n> **Status:** Aprovado\n\n## **Status:** Draft\n\nbody\n"


def test_the_contradiction_is_reported_with_its_line_and_token() -> None:
    assert is_approved(_CONTRADICTORY) is False

    found = contradicting_status_lines(_CONTRADICTORY)

    assert found, "the document declares two different statuses and nothing said so"
    line_no, token = found[0]
    assert line_no == 5, f"the author has to be sent to the offending line, got {line_no}"
    assert token == "Draft"


def test_a_consistent_document_reports_no_contradiction() -> None:
    """The false-positive guard: a normal approved artifact must stay silent."""
    assert contradicting_status_lines("# PLAN\n\n> **Status:** Aprovado\n\nbody\n") == []


def test_prose_mentioning_a_token_is_not_a_contradiction() -> None:
    """A sentence about Draft is not a status declaration."""
    doc = "# PLAN\n\n> **Status:** Aprovado\n\nThe Draft phase ends when review starts.\n"

    assert contradicting_status_lines(doc) == []
    assert is_approved(doc) is True


def test_an_unapproved_document_reports_nothing_extra() -> None:
    """Only a CONTRADICTION is reported; a plainly-Draft artifact is not confusing."""
    assert contradicting_status_lines("# PLAN\n\n> **Status:** Draft\n") == []
