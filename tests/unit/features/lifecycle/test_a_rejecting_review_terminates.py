"""A worker that never approves must not run forever.

Recipe item R-20 asks for exactly this — "the required always-REJECT review loop" — and the
consumer-side validator has never once been able to finish it: R-20 came back EXCEPTION in
round 24 with the loop unproven, having run out of its time budget. An item that keeps
timing out is not evidence of a bound; it is what an unbounded loop looks like from the
outside, and it is the operator's stated requirement in their own words: *no locks, no
infinite tasks*.

So the bound is proved here, cheaply and deterministically, instead of being paid for in
worker-minutes every round. The fake review below returns ``REJECTED`` every single time it
is asked, forever. The workflow must still stop.

What the bound actually is: each review gets ONE revision. After that its verdict turns
advisory — a further ``REJECTED`` is recorded as a warning and never blocks again — and a
review with no create step to revise is advisory immediately, since blocking on a revision
that cannot happen is a deadlock rather than a gate. Both halves are asserted, because
"terminates" is not enough: it must terminate having done the revision it promised, and it
must say what it accepted over.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from tests.unit.features.lifecycle.test_fragment_workflow_bodies import (
    _CONTEXT,
    _resolver,
    _selector,
    _workspace,
)

pytestmark = pytest.mark.unit

_RELEASE = "v0.1.30"


@dataclass
class _NeverApproves:
    """Answers REJECTED to every review, and counts how many times it is asked.

    The call counter is the actual assertion target. A workflow that terminated because a
    later gate happened to fail would look identical from the outside; only the number of
    times the rejecting worker was invoked shows the revision budget doing its job.
    """

    kind: AgentRuntimeKind
    calls: dict[str, int]

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        step = (request.task_id or "").rsplit(":", 1)[-1]
        self.calls[step] = self.calls.get(step, 0) + 1
        if self.calls[step] > 20:
            raise AssertionError(
                f"step {step!r} was re-run {self.calls[step]} times — the revision budget "
                "is not bounding the loop; this is the infinite task the operator asked "
                "never to be possible"
            )
        is_review = "review" in step
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="rejected on purpose",
            artifact_refs=(f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/{step}.step-output.json",),
            structured_output=(
                {"verdict": "REJECTED", "verdict_reason": "withholding approval forever"}
                if is_review
                else {"verdict": "APPROVED"}
            ),
        )


def test_release_definition_stops_when_the_review_never_approves(tmp_path: Path) -> None:
    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionWorkflow,
    )
    from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore

    _workspace(tmp_path)
    calls: dict[str, int] = {}
    workflow = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _NeverApproves(kind, calls),
        context_selector=_selector(tmp_path),
        handoff_resolver=_resolver(tmp_path),
    )

    result = workflow.run("never-approves")

    # Terminating at all is the first thing: _NeverApproves raises above 20 invocations, so
    # reaching this line already proves the loop is bounded.
    assert result is not None
    assert calls.get("definition_draft", 0) == 2, (
        "the draft should be authored once and revised exactly once before the review's "
        f"verdict turns advisory; it ran {calls.get('definition_draft', 0)} times"
    )
    assert calls.get("definition_review", 0) == 2, (
        f"the review should be asked twice, not {calls.get('definition_review', 0)}"
    )


def test_the_rejection_it_accepted_over_is_not_swallowed(tmp_path: Path) -> None:
    """Bounding the loop must not hide the objection — that would trade a hang for a lie."""
    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionWorkflow,
    )
    from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore

    _workspace(tmp_path)
    workflow = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _NeverApproves(kind, {}),
        context_selector=_selector(tmp_path),
        handoff_resolver=_resolver(tmp_path),
    )

    result = workflow.run("never-approves-warn")

    surfaced = " ".join(result.warnings) + (
        result.blocked.reason if result.blocked is not None else ""
    )
    assert surfaced.strip(), (
        "the run ended with the reviewer still objecting and said nothing about it — an "
        "operator reading this result would believe the review passed"
    )


def test_a_blocked_run_still_hands_back_something_to_run(tmp_path: Path) -> None:
    """If it stops by blocking, the block must carry a command, per the always-on ratchet."""
    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionWorkflow,
    )
    from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore

    _workspace(tmp_path)
    workflow = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _NeverApproves(kind, {}),
        context_selector=_selector(tmp_path),
        handoff_resolver=_resolver(tmp_path),
    )

    result = workflow.run("never-approves-recovery")

    if result.blocked is not None:
        assert result.blocked.operator_command, result.blocked.reason
        assert "dadaia " in result.blocked.operator_command
