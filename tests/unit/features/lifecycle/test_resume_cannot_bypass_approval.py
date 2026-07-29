"""Reaching the commit gate is the claim that the definition is DONE.

Bug ``r22-release-completes-with-unapproved-plan-tasks`` (validator R22, item P-01 /
R-01, the live Codex chain). The sequence on the ground was:

1. a driver returned while its live worker was still writing;
2. ``lifecycle status`` sealed the non-terminal run BLOCKED and printed a recovery;
3. the operator pasted that recovery, which RESUMED from a step after
   ``definition_review``;
4. the run completed at ``definition_commit_gate``, ACTIVE.md was repointed to
   IMPLEMENTATION — with PLAN.md and TASKS.md carrying no ``**Status:**`` line at all;
5. implementation preflight then correctly refused to start, and the release was stuck
   in a phase it was never entitled to enter.

The hole was that the terminal gate scoped its requirements to *this run's* steps:
approval was demanded only when ``definition_review`` happened to be in the sequence.
A resume that starts after the review therefore carried no approval requirement, and
the gate that exists precisely to stop an unapproved release waved it through.

Run-scoping is wrong here for the same reason it was wrong for the definition lints
(``r13-release-plan-validation-bypassed-on-resume``): the commit gate is not a step in
a run, it is the moment the release becomes binding on everyone downstream. What it
must check is DISK truth — what the next reader will actually find — not the itinerary
of whichever run happened to arrive.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.features.lifecycle.test_release_definition_workflow import (
    _CONTEXT,
    _RELEASE,
    _SEQUENCE,
    _approved,
    _KindFake,
    _MemoryRunStore,
    _step,
    _workflow,
)

pytestmark = pytest.mark.unit

#: The sequence a `--resume-from definition_commit_gate` produces: the review the
#: approval depends on is simply not in it.
_RESUMED_PAST_REVIEW = tuple(s for s in _SEQUENCE if s.label == "definition_commit_gate")


def _write(specs: Path, name: str, body: str) -> None:
    (specs / "releases" / _RELEASE / name).write_text(body, encoding="utf-8")


def test_a_resume_past_the_review_still_cannot_complete_an_unapproved_release(
    tmp_path: Path,
) -> None:
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    _write(specs, "SPEC.md", "# spec\n\n> **Status:** Aprovado\n")
    # Exactly what the validator found on disk: no Status line whatsoever.
    _write(specs, "PLAN.md", "# plan\n\nbody\n")
    _write(specs, "TASKS.md", "# tasks\n\nbody\n")

    blocked = wf._terminal_semantic_block(  # noqa: SLF001
        None,  # type: ignore[arg-type]
        _step("definition_commit_gate"),
        _RESUMED_PAST_REVIEW,
    )

    assert blocked is not None, (
        "a run that skipped the review completed the definition and repointed ACTIVE.md "
        "to IMPLEMENTATION over PLAN/TASKS that were never approved"
    )
    assert "PLAN.md" in blocked.reason and "TASKS.md" in blocked.reason
    assert blocked.operator_command is not None
    assert "--resume-from definition_review" in blocked.operator_command, (
        "the remedy must run the review that was skipped"
    )


def test_a_resume_past_the_draft_still_cannot_complete_without_the_artifacts(
    tmp_path: Path,
) -> None:
    """Existence was run-scoped by the same rule, so it had the same hole.

    A resume that starts after ``definition_draft`` demanded nothing exist at all — the
    gate would have completed a release whose PLAN.md was simply absent from disk.
    """
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    _write(specs, "SPEC.md", "# spec\n\n> **Status:** Aprovado\n")
    (specs / "releases" / _RELEASE / "PLAN.md").unlink(missing_ok=True)
    (specs / "releases" / _RELEASE / "TASKS.md").unlink(missing_ok=True)

    blocked = wf._terminal_semantic_block(  # noqa: SLF001
        None,  # type: ignore[arg-type]
        _step("definition_commit_gate"),
        _RESUMED_PAST_REVIEW,
    )

    assert blocked is not None and "absent" in blocked.reason
    assert blocked.operator_command is not None


def test_a_fully_approved_release_still_completes(tmp_path: Path) -> None:
    """Guard against fixing the hole by refusing everything.

    The gate has one job on the happy path: get out of the way. If this stops passing,
    the fix above has made the whole verb unusable rather than safe.
    """
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, lambda kind: _KindFake(kind, _approved()))
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        _write(specs, name, f"# {name}\n\n> **Status:** Aprovado\n")

    assert (
        wf._terminal_semantic_block(  # noqa: SLF001
            None,  # type: ignore[arg-type]
            _step("definition_commit_gate"),
            _RESUMED_PAST_REVIEW,
        )
        is None
    )
