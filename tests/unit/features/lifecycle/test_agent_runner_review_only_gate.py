"""Review-only verdict gate distinction (v0.1.31 Wave A — T-31-A-01).

Pins the documented design (GRILL D-1/D-2, SPEC Cluster 1): the
``structured_output["verdict"] == "APPROVED"`` requirement applies to **review**
steps only. A *create* step passes on a schema-valid payload (which populates
``artifact_refs``) + in-scope paths, **regardless of** the ``verdict`` field — but a
no-op worker (empty ``artifact_refs``) still BLOCKs (L2 / OQ-1).

These tests are RED against the current always-verdict gate (``_blocked_result``
requires ``verdict == APPROVED`` for every step) until T-31-A-02 (runner branch) and
T-31-A-05 (``PipelineStep.is_review``) land. Case (d) — the pipeline review step —
stays red until T-31-A-05 adds the ``is_review`` field.
"""

from __future__ import annotations

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


def _result(
    *,
    verdict: str | None,
    artifact_refs: tuple[str, ...],
    structured_output: dict[str, str] | None = None,
) -> AgentRunResult:
    structured: dict[str, str] = dict(structured_output or {})
    if verdict is not None:
        structured["verdict"] = verdict
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="step output",
        artifact_refs=artifact_refs,
        structured_output=structured,
    )


def _gate(
    result: AgentRunResult,
    *,
    is_review: bool,
    structured_output_evidence: bool = False,
) -> object:
    runner = LifecycleAgentRunner(runtime=FakeAgentRuntime(result=result))
    return runner.evaluate_gate(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.RELEASE_DEFINITION,
            current_step="step",
            is_review=is_review,
            structured_output_evidence=structured_output_evidence,
        ),
    )


# -- (a) review step BLOCKs on missing / REJECTED verdict -------------------


def test_review_step_blocks_on_missing_verdict() -> None:
    blocked = _gate(
        _result(verdict=None, artifact_refs=(_ARTIFACT,)),
        is_review=True,
    )
    assert blocked is not None
    assert blocked.reason == "agent result missing APPROVED verdict"


def test_review_step_blocks_on_rejected_verdict() -> None:
    blocked = _gate(
        _result(verdict="REJECTED", artifact_refs=(_ARTIFACT,)),
        is_review=True,
    )
    assert blocked is not None
    assert blocked.reason == "agent result missing APPROVED verdict"


def test_review_step_passes_on_approved_verdict() -> None:
    blocked = _gate(
        _result(verdict="APPROVED", artifact_refs=(_ARTIFACT,)),
        is_review=True,
    )
    assert blocked is None


# -- (b) create step PASSES on a valid payload regardless of verdict --------


def test_create_step_passes_on_valid_payload_with_approved_verdict() -> None:
    blocked = _gate(
        _result(verdict="APPROVED", artifact_refs=(_ARTIFACT,)),
        is_review=False,
    )
    assert blocked is None


# -- (b-adversarial / R-A) create step passes even with REJECTED / absent ---


def test_create_step_passes_with_rejected_verdict_when_payload_valid() -> None:
    # The "regardless of verdict" half pinned adversarially: a REJECTED verdict must
    # NOT block a create step that emitted a schema-valid payload (artifact_refs set).
    blocked = _gate(
        _result(verdict="REJECTED", artifact_refs=(_ARTIFACT,)),
        is_review=False,
    )
    assert blocked is None


def test_create_step_passes_with_absent_verdict_when_payload_valid() -> None:
    blocked = _gate(
        _result(verdict=None, artifact_refs=(_ARTIFACT,)),
        is_review=False,
    )
    assert blocked is None


# -- (c) no-op create step still BLOCKs (empty artifact_refs) ---------------


def test_noop_create_step_still_blocks_on_empty_artifact_refs() -> None:
    # A no-op worker emits no schema-matching payload -> empty artifact_refs ->
    # the existing artifact_refs check still BLOCKs (L2 / OQ-1: not made permissive).
    blocked = _gate(
        _result(verdict="APPROVED", artifact_refs=()),
        is_review=False,
    )
    assert blocked is not None
    assert blocked.reason == "agent result missing artifact evidence"


def test_structured_data_create_step_passes_without_artifact_refs_when_opted_in() -> None:
    blocked = _gate(
        _result(
            verdict=None,
            artifact_refs=(),
            structured_output={"proposed_intents": "[]", "open_questions": "[]"},
        ),
        is_review=False,
        structured_output_evidence=True,
    )
    assert blocked is None


def test_structured_data_create_step_blocks_noop_even_when_opted_in() -> None:
    blocked = _gate(
        _result(verdict=None, artifact_refs=(), structured_output={}),
        is_review=False,
        structured_output_evidence=True,
    )
    assert blocked is not None
    assert blocked.reason == "agent result missing artifact evidence"


def test_artifact_create_step_still_blocks_without_artifact_refs_by_default() -> None:
    blocked = _gate(
        _result(
            verdict=None,
            artifact_refs=(),
            structured_output={"proposed_intents": "[]"},
        ),
        is_review=False,
    )
    assert blocked is not None
    assert blocked.reason == "agent result missing artifact evidence"


# -- (d) pipeline review step BLOCKs on missing / REJECTED verdict ----------


def _pipeline_review_steps() -> tuple[object, ...]:
    ladder = implementation_ladder(AgentRuntimeKind.FAKE)
    review_labels = {"review_qa", "review_security", "review_code"}
    return tuple(s for s in ladder if s.label in review_labels)


def test_pipeline_review_steps_are_marked_is_review() -> None:
    steps = _pipeline_review_steps()
    assert len(steps) == 3
    for step in steps:
        assert step.is_review is True  # type: ignore[attr-defined]


def test_pipeline_implement_step_is_not_review() -> None:
    ladder = implementation_ladder(AgentRuntimeKind.FAKE)
    implement = next(s for s in ladder if s.label == "implement")
    assert implement.is_review is False  # type: ignore[attr-defined]


def test_pipeline_review_step_blocks_on_missing_verdict() -> None:
    # Drive each pipeline review step's is_review flag through the gate: a missing
    # verdict must BLOCK (the push-boundary review gate keeps its verdict requirement).
    for step in _pipeline_review_steps():
        blocked = _gate(
            _result(verdict=None, artifact_refs=(_ARTIFACT,)),
            is_review=step.is_review,  # type: ignore[attr-defined]
        )
        assert blocked is not None, f"{step.label} should block on missing verdict"  # type: ignore[attr-defined]
        assert blocked.reason == "agent result missing APPROVED verdict"


def test_pipeline_review_step_blocks_on_rejected_verdict() -> None:
    for step in _pipeline_review_steps():
        blocked = _gate(
            _result(verdict="REJECTED", artifact_refs=(_ARTIFACT,)),
            is_review=step.is_review,  # type: ignore[attr-defined]
        )
        assert blocked is not None, f"{step.label} should block on REJECTED verdict"  # type: ignore[attr-defined]
        assert blocked.reason == "agent result missing APPROVED verdict"


# -- (e) v0.1.32 Wave C — REJECTED-blocks negative via the faked gate path (T-32-C-03) ----
#
# A15 / OQ-2: the live half (test_real_pi_worker_review_step_emits_approved_and_gate_passes)
# proves a real worker's APPROVED verdict PASSES the gate. The REJECTED-blocks negative is
# proven HERE through the same faked gate — no second credit-burning live run, default CI
# stays green. These assert the verdict gate BLOCKs a review step on REJECTED and on a
# missing verdict, even when the payload is otherwise schema-valid (artifact_refs populated),
# mirroring the ``spec_arch_review`` review step the live e2e exercises.


def test_wave_c_review_step_rejected_verdict_blocks_run() -> None:
    # REJECTED on a review step BLOCKs (A15): the gate refuses to advance despite a
    # schema-valid payload (non-empty artifact_refs) — only the verdict differs.
    blocked = _gate(
        _result(verdict="REJECTED", artifact_refs=(_ARTIFACT,)),
        is_review=True,
    )
    assert blocked is not None, "a REJECTED verdict on a review step must BLOCK the run"
    assert blocked.reason == "agent result missing APPROVED verdict"


def test_wave_c_review_step_missing_verdict_blocks_run() -> None:
    # The missing-verdict variant (A15): a review step with NO verdict field BLOCKs, even
    # with a schema-valid payload — the absence of an explicit APPROVED is not a pass.
    blocked = _gate(
        _result(verdict=None, artifact_refs=(_ARTIFACT,)),
        is_review=True,
    )
    assert blocked is not None, "a missing verdict on a review step must BLOCK the run"
    assert blocked.reason == "agent result missing APPROVED verdict"


def test_wave_c_review_step_approved_verdict_passes_contrast() -> None:
    # Positive contrast pinning the negative: the SAME schema-valid payload PASSES iff the
    # verdict is APPROVED — so the block above is attributable to the verdict, nothing else.
    blocked = _gate(
        _result(verdict="APPROVED", artifact_refs=(_ARTIFACT,)),
        is_review=True,
    )
    assert blocked is None, "an APPROVED verdict on a schema-valid review payload must PASS"
