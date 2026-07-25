"""The SPEC-authoring prompt must demand the one line Python actually parses.

Bug live-release-spec-never-declares-consumes.

Found by inspecting the consumer-side validator's LIVE workspace on disk: a real Codex
chain completed backlog-definition, release-definition and implementation-reviews, wrote
CLOSURE.md — and consumed NOTHING. The SPEC had no ``**Consumes:**`` line and the authored
backlog item was still sitting in ``specs/backlog/``.

The cause was not code. Not one ``release_definition`` fragment mentioned ``Consumes``:
``spec-create`` asked for a prose traceability table but never for the machine-readable
line that drives the consumed_backlog ledger and the closure removal. Before the scope
check existed a live release silently dropped its backlog; after it, a live release
BLOCKS — so the operator's real flow could not complete either way.

The fake chain could never expose this, because the driving fake was taught to write the
line directly. Only the live path depends on the prompt saying so. This test is that
dependency, made explicit: a prompt obligation nothing asserts is a prompt obligation that
silently disappears.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_FRAGMENTS = (
    Path(__file__).resolve().parents[2]
    / "dadaia_workspace"
    / "public"
    / "lifecycle_fragments"
    / "release_definition"
)


def test_spec_create_demands_the_consumes_line() -> None:
    text = (_FRAGMENTS / "spec-create.md").read_text(encoding="utf-8")
    assert "**Consumes:**" in text, (
        "spec-create must instruct the author to write the `**Consumes:**` line; without "
        "it a live release consumes nothing and the commit gate refuses the definition."
    )
    lowered = text.lower()
    # It must be framed as mandatory and machine-read, not as an optional nicety.
    assert "mandatory" in lowered, text[:0] or "spec-create must mark the line mandatory"
    assert "authoritative-backlog-definition" in text, (
        "the instruction must tie the list to the injected scope block, or the author has "
        "no way to know WHICH slugs to name"
    )


def test_spec_review_checks_the_consumes_line() -> None:
    text = (_FRAGMENTS / "spec-review.md").read_text(encoding="utf-8")
    assert "**Consumes:**" in text, (
        "the SPEC review must verify the Consumes line — an authoring instruction with no "
        "reviewer check is how it drifts back out"
    )


def test_the_parser_and_the_prompt_agree_on_the_token() -> None:
    """The exact token the prompt teaches must be the token the parser matches.

    A prompt that teaches ``Consumed:`` while the parser reads ``**Consumes:**`` would
    look correct in review and fail silently in production — the two-sources-of-truth
    class, one source being English.
    """
    from dadaia_workspace.features.backlog.consumes import parse_consumes_line

    text = (_FRAGMENTS / "spec-create.md").read_text(encoding="utf-8")
    example = next(
        (line for line in text.splitlines() if line.strip().startswith("**Consumes:**")),
        None,
    )
    assert example is not None, "spec-create must show a literal example line"
    parsed = parse_consumes_line(example.replace("<slug>", "example-slug"))
    assert parsed, f"the parser reads nothing from the line the prompt teaches: {example!r}"


def test_plan_review_requires_the_contract_bindings_tasks_cannot_invent() -> None:
    """The PLAN review must catch a missing contract binding, where it is still fixable.

    Bug plan-review-approves-a-plan-missing-its-contract-bindings. ``plan-create``
    requires exact signatures, field types and module paths for every caller-facing
    surface; ``tasks-create`` FORBIDS inventing a binding the PLAN omitted; and
    ``tasks-review-implementability`` REQUIRES them present. A PLAN approved without them
    therefore traps the TASKS author between two rules it cannot both satisfy — observed
    live as five consecutive TASKS rejections that stopped narrowing and began restating.

    A downstream gate must never be the first place an upstream omission is detected when
    the downstream step is forbidden from repairing it.
    """
    review = (_FRAGMENTS / "plan-review.md").read_text(encoding="utf-8")
    create = (_FRAGMENTS / "plan-create.md").read_text(encoding="utf-8")
    assert "signature" in create, "plan-create must demand the bindings in the first place"
    assert "Contract bindings present" in review, (
        "plan-review must have a check for the contract bindings, or the omission is only "
        "detected at tasks_implementability_review, which cannot repair it"
    )
    assert "REJECTED" in review
