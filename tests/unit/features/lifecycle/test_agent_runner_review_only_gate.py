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

import json
from dataclasses import replace
from pathlib import Path

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
from dadaia_workspace.features.lifecycle.prompt_builder import canonical_worker_output_ref
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime

_ARTIFACT = ".dadaia/tmp/lifecycle-worker/dadaia-workspace/step.step-output.json"
_VERDICT_REASON = "agent result missing APPROVED verdict"
_REJECTED_REASON = "review verdict REJECTED"
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
        allowed_paths=(".dadaia/tmp/lifecycle-worker/dadaia-workspace/**",),
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
    ("review-rejected-blocks", "REJECTED", (_ARTIFACT,), True, True, _REJECTED_REASON),
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


# -- ①b explicit-rejection diagnostics (bug: blocked-reason-misreports-rejected-verdict) --


def test_rejected_verdict_block_carries_verdict_and_reason_detail() -> None:
    result = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="step output",
        artifact_refs=(_ARTIFACT,),
        structured_output={"verdict": "REJECTED", "verdict_reason": "spec not measurable"},
    )
    blocked = _gate(result, is_review=True)
    assert blocked is not None
    assert blocked.reason == "review verdict REJECTED: spec not measurable"
    assert blocked.detail["verdict"] == "REJECTED"
    assert blocked.detail["verdict_reason"] == "spec not measurable"


def test_rejected_verdict_without_reason_still_names_the_verdict() -> None:
    blocked = _gate(_result(verdict="REJECTED", artifact_refs=(_ARTIFACT,)), is_review=True)
    assert blocked is not None
    assert blocked.reason == "review verdict REJECTED"
    assert blocked.detail["verdict"] == "REJECTED"
    assert "verdict_reason" not in blocked.detail


def test_missing_verdict_keeps_missing_wording() -> None:
    blocked = _gate(_result(verdict=None, artifact_refs=(_ARTIFACT,)), is_review=True)
    assert blocked is not None
    assert blocked.reason == _VERDICT_REASON
    assert "verdict" not in blocked.detail


class _SequenceRuntime:
    def __init__(self, results: list[AgentRunResult]) -> None:
        self.results = results
        self.requests: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.requests.append(request)
        return self.results.pop(0)


def test_missing_evidence_gets_one_bounded_structural_correction_attempt() -> None:
    runtime = _SequenceRuntime(
        [
            _result(verdict=None, artifact_refs=()),
            _result(verdict=None, artifact_refs=(_ARTIFACT,)),
        ]
    )
    blocked = LifecycleAgentRunner(runtime=runtime).evaluate_gate(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.RELEASE_DEFINITION,
            current_step="step",
            is_review=False,
        ),
    )

    assert blocked is None
    assert len(runtime.requests) == 2
    assert "Automatic structural correction attempt (2 of 2)" in runtime.requests[1].prompt
    assert _ARTIFACT_REASON in runtime.requests[1].prompt


def test_explicit_rejected_review_is_never_structurally_retried() -> None:
    runtime = _SequenceRuntime([_result(verdict="REJECTED", artifact_refs=(_ARTIFACT,))])
    blocked = LifecycleAgentRunner(runtime=runtime).evaluate_gate(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.RELEASE_DEFINITION,
            current_step="step",
            is_review=True,
        ),
    )

    assert blocked is not None
    assert blocked.reason == _REJECTED_REASON
    assert len(runtime.requests) == 1


@pytest.mark.parametrize("is_review", [False, True], ids=["create", "review"])
def test_exact_python_assigned_handoff_recovers_empty_last_message(
    tmp_path: Path, is_review: bool
) -> None:
    request = replace(_request(), task_id="run-1:step")
    ref = canonical_worker_output_ref(request.context, request.task_id or "")
    handoff = tmp_path / ref
    handoff.parent.mkdir(parents=True, exist_ok=True)
    document: dict[str, object] = {
        "summary": "materialized exact handoff",
        "handoff": {"summary": "substantive domain handoff", "picked": ["item-a"]},
    }
    if is_review:
        document.update({"verdict": "APPROVED", "verdict_reason": "evidence passes"})
    handoff.write_text(json.dumps(document), encoding="utf-8")
    runtime = _SequenceRuntime([_result(verdict=None, artifact_refs=())])

    result, blocked = LifecycleAgentRunner(
        runtime=runtime, artifact_root=tmp_path
    ).evaluate_gate_with_result(
        _run(),
        AgentRunnerInput(
            request=request,
            target_phase=LifecyclePhase.RELEASE_DEFINITION,
            current_step="step",
            is_review=is_review,
        ),
    )

    assert blocked is None
    assert result.artifact_refs == (ref,)
    assert result.summary == "materialized exact handoff"
    assert result.domain_payload == document
    if is_review:
        assert result.structured_output["verdict"] == "APPROVED"
    assert len(runtime.requests) == 1


def test_handoff_without_declared_deliverable_gets_one_correction_attempt(
    tmp_path: Path,
) -> None:
    request = replace(
        _request(),
        task_id="run-1:spec_create",
        allowed_paths=(
            ".dadaia/tmp/lifecycle-worker/dadaia-workspace/**",
            "specs/releases/v1/**",
        ),
    )
    handoff_ref = canonical_worker_output_ref(request.context, request.task_id or "")
    handoff = tmp_path / handoff_ref
    handoff.parent.mkdir(parents=True, exist_ok=True)
    handoff.write_text(json.dumps({"summary": "handoff only"}), encoding="utf-8")
    spec_ref = "specs/releases/v1/SPEC.md"
    spec = tmp_path / spec_ref
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("# SPEC\n", encoding="utf-8")
    runtime = _SequenceRuntime(
        [
            _result(verdict=None, artifact_refs=()),
            _result(verdict=None, artifact_refs=(spec_ref,)),
        ]
    )

    _result_value, blocked = LifecycleAgentRunner(
        runtime=runtime, artifact_root=tmp_path
    ).evaluate_gate_with_result(
        _run(),
        AgentRunnerInput(
            request=request,
            target_phase=LifecyclePhase.RELEASE_DEFINITION,
            current_step="spec_create",
            is_review=False,
            deliverable_globs=("specs/releases/v1/**",),
        ),
    )

    assert blocked is None
    assert len(runtime.requests) == 2
    assert "carries no deliverable" in runtime.requests[1].prompt


def test_unique_existing_context_relative_spec_ref_is_normalized(tmp_path: Path) -> None:
    workspace_ref = "repos/demo/specs/releases/v1/SPEC.md"
    artifact = tmp_path / workspace_ref
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("# SPEC\n", encoding="utf-8")
    request = replace(
        _request(),
        task_id="run-1:spec_create",
        allowed_paths=(
            ".dadaia/handoff/dadaia-workspace/**",
            "repos/demo/specs/releases/v1/**",
        ),
    )
    runtime = _SequenceRuntime(
        [_result(verdict=None, artifact_refs=("specs/releases/v1/SPEC.md",))]
    )

    result, blocked = LifecycleAgentRunner(
        runtime=runtime, artifact_root=tmp_path
    ).evaluate_gate_with_result(
        _run(),
        AgentRunnerInput(
            request=request,
            target_phase=LifecyclePhase.RELEASE_DEFINITION,
            current_step="spec_create",
            is_review=False,
            deliverable_globs=("repos/demo/specs/releases/v1/**",),
        ),
    )

    assert blocked is None
    assert result.artifact_refs == (workspace_ref,)
    assert len(runtime.requests) == 1


# -- ①c review citations are not writes (bug review-step-out-of-scope-...-artifact) ------


def _result_with_changed(
    *, verdict: str, artifact_refs: tuple[str, ...], changed_paths: tuple[str, ...]
) -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="step output",
        artifact_refs=artifact_refs,
        structured_output={"verdict": verdict, "changed_paths": ",".join(changed_paths)},
    )


def test_approving_review_citing_reviewed_artifact_outside_allowlist_passes() -> None:
    """The reviewed artifact citation (artifact.path) is evidence, not a write."""
    blocked = _gate(
        _result(verdict="APPROVED", artifact_refs=("specs/releases/r1/TASKS.md",)),
        is_review=True,
    )
    assert blocked is None


def test_review_with_out_of_scope_changed_paths_still_blocks() -> None:
    """A reviewer that actually WRITES outside its allowlist stays blocked."""
    blocked = _gate(
        _result_with_changed(
            verdict="APPROVED",
            artifact_refs=(_ARTIFACT,),
            changed_paths=("specs/releases/r1/TASKS.md",),
        ),
        is_review=True,
    )
    assert blocked is not None
    assert blocked.reason == "agent result contains out-of-scope paths"


def test_create_step_out_of_scope_artifact_refs_still_block() -> None:
    """Create-step deliverables (artifact_refs) remain fully scope-checked."""
    blocked = _gate(
        _result(verdict="APPROVED", artifact_refs=("specs/releases/r1/TASKS.md",)),
        is_review=False,
    )
    assert blocked is not None
    assert blocked.reason == "agent result contains out-of-scope paths"


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
        expected = _VERDICT_REASON if verdict is None else _REJECTED_REASON
        assert blocked.reason == expected
