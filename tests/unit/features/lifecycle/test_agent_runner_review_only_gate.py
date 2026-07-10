"""Review-only verdict gate distinction (v0.1.31 Wave A — T-31-A-01).

Pins the documented design (GRILL D-1/D-2, SPEC Cluster 1): the
``structured_output["verdict"] == "APPROVED"`` requirement applies to **review**
steps only. A *create* step passes on a schema-valid payload (which populates
``artifact_refs``) + in-scope paths, **regardless of** the ``verdict`` field — but a
no-op worker (empty ``artifact_refs``) still BLOCKs (L2 / OQ-1).

CRITICAL: the review-only APPROVED gate + create-step pass-regardless-of-verdict + no-op-worker
still blocks. The full matrix is one parametrized decision table (was 9 near-duplicate fns,
including a Wave-C trio that restated case (a) verbatim through the same ``_gate`` helper).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)
from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime

_ARTIFACT = ".dadaia/handoff/dadaia-workspace/step.handoff.json"
_VERDICT_REASON = "agent result missing APPROVED verdict"
_ARTIFACT_REASON = "agent result missing artifact evidence"


def _run() -> LifecycleRun:
    return LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.31",
        command="release_define",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.RUNNING,
        current_step="step",
        idempotency_key="resume-1",
    )


def _request() -> AgentRunRequest:
    return AgentRunRequest(
        role="product-engineer",
        prompt="run the step",
        runtime=AgentRuntimeKind.FAKE,
        context="dadaia-workspace",
        release_id="v0.1.31",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def _result(*, verdict: str | None, artifact_refs: tuple[str, ...]) -> AgentRunResult:
    structured: dict[str, str] = {}
    if verdict is not None:
        structured["verdict"] = verdict
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="step output",
        artifact_refs=artifact_refs,
        structured_output=structured,
    )


def _gate(result: AgentRunResult, *, is_review: bool) -> object:
    runner = LifecycleAgentRunner(runtime=FakeAgentRuntime(result=result))
    return runner.evaluate_gate(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.RELEASE_DEFINITION,
            current_step="step",
            is_review=is_review,
        ),
    )


# -- ① verdict × is_review gate matrix + no-op-empty-refs block -------------------------

_MATRIX = (
    # (case_id, verdict, artifact_refs, is_review, expect_blocked, expect_reason)
    ("review-missing-blocks", None, (_ARTIFACT,), True, True, _VERDICT_REASON),
    ("review-rejected-blocks", "REJECTED", (_ARTIFACT,), True, True, _VERDICT_REASON),
    ("review-approved-passes", "APPROVED", (_ARTIFACT,), True, False, None),
    ("create-approved-passes", "APPROVED", (_ARTIFACT,), False, False, None),
    # "regardless of verdict" pinned adversarially: create passes even REJECTED/absent.
    ("create-rejected-passes", "REJECTED", (_ARTIFACT,), False, False, None),
    ("create-absent-passes", None, (_ARTIFACT,), False, False, None),
    # a no-op worker (no schema-matching payload) still BLOCKs — not made permissive (OQ-1).
    ("create-noop-empty-refs-blocks", "APPROVED", (), False, True, _ARTIFACT_REASON),
)


@pytest.mark.parametrize(
    "verdict,artifact_refs,is_review,expect_blocked,expect_reason",
    [c[1:] for c in _MATRIX],
    ids=[c[0] for c in _MATRIX],
)
def test_verdict_review_gate_matrix(
    verdict: str | None,
    artifact_refs: tuple[str, ...],
    is_review: bool,
    expect_blocked: bool,
    expect_reason: str | None,
) -> None:
    blocked = _gate(_result(verdict=verdict, artifact_refs=artifact_refs), is_review=is_review)
    if expect_blocked:
        assert blocked is not None
        assert blocked.reason == expect_reason
    else:
        assert blocked is None


# -- ② ladder review steps carry is_review flags -----------------------------------------


def test_ladder_review_steps_marked_is_review_implement_step_is_not() -> None:
    ladder = implementation_ladder(AgentRuntimeKind.FAKE)
    review_labels = {"review_qa", "review_security", "review_code"}
    review_steps = tuple(s for s in ladder if s.label in review_labels)
    assert len(review_steps) == 3
    for step in review_steps:
        assert step.is_review is True

    implement = next(s for s in ladder if s.label == "implement")
    assert implement.is_review is False


# -- ③ ladder-driven review-step block param (missing / REJECTED) -----------------------


@pytest.mark.parametrize("verdict", [None, "REJECTED"], ids=["missing", "rejected"])
def test_pipeline_review_steps_block_on_missing_or_rejected_verdict(verdict: str | None) -> None:
    ladder = implementation_ladder(AgentRuntimeKind.FAKE)
    review_labels = {"review_qa", "review_security", "review_code"}
    review_steps = tuple(s for s in ladder if s.label in review_labels)
    for step in review_steps:
        blocked = _gate(
            _result(verdict=verdict, artifact_refs=(_ARTIFACT,)),
            is_review=step.is_review,
        )
        assert blocked is not None, f"{step.label} should block on {verdict!r} verdict"
        assert blocked.reason == _VERDICT_REASON
