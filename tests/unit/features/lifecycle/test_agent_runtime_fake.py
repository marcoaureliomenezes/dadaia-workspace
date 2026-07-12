"""Unit tests for lifecycle agent runner using a fake AgentRuntimePort.

These all exercise a REVIEW step (a qa-engineer step targeting ``QA_REVIEW``), so every
``AgentRunnerInput`` sets ``is_review=True``. Under the v0.1.31 review-only gate the verdict
requirement keys on the explicit ``is_review`` flag (not the target phase): a review step
still BLOCKs on a missing/REJECTED verdict, missing artifact evidence, and out-of-scope
paths. Create-step (``is_review=False``) gate behavior is covered by
``test_agent_runner_review_only_gate.py``.

CRITICAL: structured-verdict-not-prose + artifact-evidence + scope gate.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
    GateRequirement,
    GateVerdict,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)


@dataclass(frozen=True)
class FakeAgentRuntime:
    result: AgentRunResult

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return self.result


def _run() -> LifecycleRun:
    return LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.15",
        command="implement",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="implementation",
        idempotency_key="resume-1",
    )


def _request() -> AgentRunRequest:
    return AgentRunRequest(
        role="qa-engineer",
        prompt="review task",
        runtime=AgentRuntimeKind.FAKE,
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="T-015-16",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        forbidden_paths=("repos/dadaia-workspace/src/secrets.py",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def _decision(
    result: AgentRunResult,
    *,
    requirements: tuple[GateRequirement, ...] = (),
    is_review: bool = True,
):
    runtime: AgentRuntimePort = FakeAgentRuntime(result)
    return LifecycleAgentRunner(runtime=runtime).run(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            requirements=requirements,
            current_step="qa-review",
            is_review=is_review,
        ),
    )


def test_approved_verdict_with_scope_evidence_advances() -> None:
    requirement = GateRequirement(
        evidence_kind=GateEvidenceKind.HANDOFF,
        required_agent="qa-engineer",
        required_verdict=GateVerdict.APPROVED,
        release_id="v0.1.15",
        task_group="T-015-16",
    )
    decision = _decision(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="qa approved",
            artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
            structured_output={
                "verdict": "APPROVED",
                "task_group": "T-015-16",
                "changed_paths": ".dadaia/handoff/dadaia-workspace/qa.handoff.json",
            },
        ),
        requirements=(requirement,),
    )

    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.QA_REVIEW
    assert decision.run.blocked is None


def test_prose_verdict_and_missing_artifact_evidence_both_block_the_gate() -> None:
    prose_decision = _decision(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="APPROVED by qa",
            artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        )
    )
    assert prose_decision.accepted is True
    assert prose_decision.run.phase is LifecyclePhase.BLOCKED
    assert prose_decision.run.blocked is not None
    assert prose_decision.run.blocked.reason == "agent result missing APPROVED verdict"

    no_evidence_decision = _decision(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="approved",
            structured_output={"verdict": "APPROVED"},
        )
    )
    assert no_evidence_decision.accepted is True
    assert no_evidence_decision.run.phase is LifecyclePhase.BLOCKED
    assert no_evidence_decision.run.blocked is not None
    assert no_evidence_decision.run.blocked.reason == "agent result missing artifact evidence"


# -- out-of-scope detector: 3 input variants of the same `out_of_scope` block reason -----

# Review steps scope-check their WRITES (changed_paths) only — artifact_refs are the
# reviewed-artifact citations the handoff schema demands (bug
# review-step-out-of-scope-blocks-cited-reviewed-artifact). The citation variants of the
# out-of-scope cases therefore assert on is_review=False (create-step deliverables).
_OUT_OF_SCOPE_CASES = (
    (
        "artifact-ref-outside-scope",
        ("repos/dadaia-workspace/src/secrets.py",),
        None,
        False,
        "repos/dadaia-workspace/src/secrets.py",
    ),
    (
        "sibling-prefix-does-not-match",
        (".dadaia/handoff/dadaia-workspace-secret/qa.handoff.json",),
        None,
        False,
        ".dadaia/handoff/dadaia-workspace-secret/qa.handoff.json",
    ),
    (
        "changed-paths-validated-against-write-scope",
        (".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        ".dadaia/handoff/dadaia-workspace/qa.handoff.json,repos/dadaia-workspace/src/secrets.py",
        True,
        "repos/dadaia-workspace/src/secrets.py",
    ),
)


@pytest.mark.parametrize(
    "artifact_refs,changed_paths,is_review,expected_out_of_scope",
    [c[1:] for c in _OUT_OF_SCOPE_CASES],
    ids=[c[0] for c in _OUT_OF_SCOPE_CASES],
)
def test_out_of_scope_paths_block_before_transition(
    artifact_refs: tuple[str, ...],
    changed_paths: str | None,
    is_review: bool,
    expected_out_of_scope: str,
) -> None:
    structured = {"verdict": "APPROVED"}
    if changed_paths is not None:
        structured["changed_paths"] = changed_paths
    decision = _decision(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="approved",
            artifact_refs=artifact_refs,
            structured_output=structured,
        ),
        is_review=is_review,
    )

    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.BLOCKED
    assert decision.run.blocked is not None
    assert decision.run.blocked.reason == "agent result contains out-of-scope paths"
    assert decision.run.blocked.detail["out_of_scope"] == expected_out_of_scope


def test_review_citation_of_reviewed_artifact_outside_allowlist_passes() -> None:
    """An APPROVED review citing the reviewed artifact (no writes) is NOT out-of-scope."""
    decision = _decision(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="approved",
            artifact_refs=("repos/dadaia-workspace/specs/releases/r1/TASKS.md",),
            structured_output={"verdict": "APPROVED"},
        ),
        is_review=True,
    )
    assert decision.run.blocked is None
