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
