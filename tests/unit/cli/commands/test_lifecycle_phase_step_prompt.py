"""Unit test for the CLI single-step worker prompt's step-kind awareness.

Relocated from tests/integration/cli/test_lifecycle_command_skeletons.py (T-7,
v0.1.75): ``_phase_step_prompt`` is a pure function — no fs/subprocess/CLI
invocation — so it belongs in the unit tier.
"""

from __future__ import annotations

from dadaia_workspace.cli.commands.lifecycle import _phase_step_prompt


def test_phase_step_prompt_is_step_kind_aware() -> None:
    """The CLI single-step worker prompt (the THIRD prompt surface) is review/create aware.

    v0.1.32 D-2/L1: a review step is told to emit a verdict; a create step is NOT
    (instructing a create step to self-verdict is the Drift-1 incoherence this release
    eliminated on the other two surfaces). v0.1.78 T-A / FR-A: ``is_review`` is now an
    EXPLICIT caller-supplied step-kind signal, independent of the step's transition target
    — ``implement`` targets QA_REVIEW (a review *phase*) purely to advance the release, but
    is itself a create *step*, so it must get the create-step instruction. Guards the entry
    point for ``dadaia lifecycle implement``/``close`` against re-introducing the
    universal-self-verdict text.
    """
    review = _phase_step_prompt("review qa", "v0.1.99", "ctx", is_review=True)
    # implement is a create step even though its transition target is QA_REVIEW.
    create = _phase_step_prompt("implement", "v0.1.99", "ctx", is_review=False)
    close = _phase_step_prompt("close", "v0.1.99", "ctx", is_review=False)

    assert "verdict is APPROVED or REJECTED" in review
    assert "Do not self-verdict" not in review
    for prompt in (create, close):
        assert "Do not self-verdict" in prompt
        assert "is APPROVED or REJECTED" not in prompt
