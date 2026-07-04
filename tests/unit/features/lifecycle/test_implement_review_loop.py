"""Implement/review attempt loop with bounded retry (v0.1.30 Item 5 / T-30-D-06).

Pins A24 + v0.1.56 FR3 (T-56-30):
- ``implement#2`` consumes the EXACT ``qa#1`` rejection by (run, producer step, attempt)
  — never ``qa#0`` / an unrelated run — AND the ``implement#N`` prompt carries the
  ``review#N-1`` rejection **digest** (the l.309 drop is replaced; AC-4(a)/(d)).
- every loop worker is gated through ``LifecycleAgentRunner.evaluate_gate_with_result``
  on EVIDENCE ONLY (``is_review=False``): a non-SUCCEEDED / evidence-less / out-of-scope
  worker BLOCKS the loop (structural block, AC-4(b)), while a well-formed REJECTED review
  is retried — its verdict is read from the result, never gated (AC-4(d)).
- the bounded retry count (default 2) BLOCKS for operator intervention when exceeded
  (retry EXHAUSTION, distinct from a structural evidence block).

Hermetic: real ``JsonLifecycleRunStore`` + real ``FilesystemRuntimeFileAdapter`` under
``tmp_path``, a fake runtime whose verdict is scripted per review attempt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
)
from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline, PipelineStep
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.30"


@dataclass
class _ScriptedReviewRuntime:
    """Implement always succeeds; review returns the scripted verdict per attempt.

    Records every request it receives (v0.1.56 / FR3) so a test can assert the digest that
    reached the ``implement#N`` prompt. Both the implement and the review worker return an
    in-scope ``.dadaia/handoff/<ctx>/**`` artifact_ref, so both pass the structural runner
    gate every round — the loop never blocks on a well-formed REJECTED review.
    """

    kind: AgentRuntimeKind
    review_verdicts: list[str]
    _review_calls: int = 0
    received_requests: list[AgentRunRequest] = field(default_factory=list)

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        role = request.role
        if "qa" in role or "review" in role:
            idx = min(self._review_calls, len(self.review_verdicts) - 1)
            verdict = self.review_verdicts[idx]
            self._review_calls += 1
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=f"review verdict {verdict}",
                artifact_refs=(f".dadaia/handoff/{_CONTEXT}/qa.handoff.json",),
                structured_output={"verdict": verdict},
            )
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="implementation done",
            artifact_refs=(f".dadaia/handoff/{_CONTEXT}/impl.handoff.json",),
            structured_output={"verdict": "APPROVED"},
        )


@dataclass
class _EvidencelessRuntime:
    """A worker that SUCCEEDS with an APPROVED verdict but produces NO artifact evidence.

    The structural runner gate (``is_review=False``) must BLOCK on the empty ``artifact_refs``
    BEFORE the verdict is ever read — the RED-first proof for AC-4(b). Pre-fix (the loop read
    ``verdict`` directly with no gate) an APPROVED verdict would COMPLETE the loop; post-fix it
    BLOCKS structurally.
    """

    kind: AgentRuntimeKind
    received_requests: list[AgentRunRequest] = field(default_factory=list)

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="no evidence produced",
            artifact_refs=(),
            structured_output={"verdict": "APPROVED"},
        )


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    return tmp_path


def _steps() -> tuple[PipelineStep, PipelineStep]:
    implement = PipelineStep(
        label="implement",
        role="software-engineer",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        runtime_kind=AgentRuntimeKind.FAKE,
    )
    review = PipelineStep(
        label="qa",
        role="qa-engineer",
        from_phase=LifecyclePhase.QA_REVIEW,
        target_phase=LifecyclePhase.IMPLEMENTATION,
        runtime_kind=AgentRuntimeKind.FAKE,
    )
    return implement, review


def _build(tmp_path: Path, runtime: object, *, max_retries: int = 2) -> LifecyclePipeline:
    """Wire a loop pipeline over *runtime* with a real handoff resolver + run store."""
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-06-27T12:00:00Z",
    )
    return LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: runtime,  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        max_review_retries=max_retries,
    )


def _pipeline(tmp_path: Path, verdicts: list[str], *, max_retries: int = 2) -> LifecyclePipeline:
    return _build(
        tmp_path, _ScriptedReviewRuntime(AgentRuntimeKind.FAKE, verdicts), max_retries=max_retries
    )


# --- A24 / AC-4(a)(d): implement#2 consumes the exact qa#1 rejection + carries its digest ---


def test_implement_attempt_2_consumes_exact_qa_attempt_1(tmp_path: Path) -> None:
    _workspace(tmp_path)
    # round 0 REJECTED, round 1 REJECTED, round 2 APPROVED → 3 attempts, success in bound.
    runtime = _ScriptedReviewRuntime(AgentRuntimeKind.FAKE, ["REJECTED", "REJECTED", "APPROVED"])
    pipeline = _build(tmp_path, runtime, max_retries=2)

    result = pipeline.run_implement_review_loop(
        "loop-1", implement_step=_steps()[0], review_step=_steps()[1]
    )

    assert result.completed is True
    assert result.attempts == 3
    # The well-formed REJECTED rounds NEVER blocked — the structural gate passed each round.
    assert result.blocked is None

    run = JsonLifecycleRunStore(tmp_path).load("loop-1")
    assert run is not None
    # implement#2 recorded a consumption of qa#1 — the EXACT prior-round rejection.
    qa1 = run.workflow_steps.find("qa", 1)
    assert qa1 is not None
    consumers = {(c.consumer_step, c.consumer_attempt) for c in qa1.consumptions}
    assert ("implement", 2) in consumers
    # And it did NOT consume qa#0 as the round-2 input (qa#0 was consumed by implement#1).
    qa0 = run.workflow_steps.find("qa", 0)
    assert qa0 is not None
    qa0_consumers = {(c.consumer_step, c.consumer_attempt) for c in qa0.consumptions}
    assert ("implement", 1) in qa0_consumers
    assert ("implement", 2) not in qa0_consumers

    # AC-4(a): the implement#2 prompt CONTAINS the review#1 (qa#1) rejection digest — the
    # digest that was DROPPED pre-fix (l.309 `_ = resolved`) now reaches the built request.
    impl2 = next(r for r in runtime.received_requests if r.task_id == "loop-1#a2:implement")
    assert "handoff qa#1" in impl2.prompt
    assert "verdict: REJECTED" in impl2.prompt


# --- A24: bounded retry exceeded → BLOCK (retry EXHAUSTION, not a structural block) ---------


def test_loop_blocks_after_bounded_retries_exceeded(tmp_path: Path) -> None:
    _workspace(tmp_path)
    # always REJECTED → never approves; with max_retries=2 there are 3 attempts then BLOCK.
    pipeline = _pipeline(tmp_path, ["REJECTED"], max_retries=2)

    result = pipeline.run_implement_review_loop(
        "loop-block", implement_step=_steps()[0], review_step=_steps()[1]
    )

    assert result.completed is False
    assert result.attempts == 3
    assert result.blocked is not None
    # The block is retry EXHAUSTION — the well-formed REJECTED workers passed the structural
    # gate every round; the loop exhausted its budget rather than blocking prematurely.
    assert "bounded retry" in result.blocked.reason
    assert "artifact evidence" not in result.blocked.reason

    run = JsonLifecycleRunStore(tmp_path).load("loop-block")
    assert run is not None
    assert run.phase is LifecyclePhase.BLOCKED


def test_loop_completes_on_first_approval(tmp_path: Path) -> None:
    _workspace(tmp_path)
    pipeline = _pipeline(tmp_path, ["APPROVED"], max_retries=2)

    result = pipeline.run_implement_review_loop(
        "loop-fast", implement_step=_steps()[0], review_step=_steps()[1]
    )

    assert result.completed is True
    assert result.attempts == 1
    run = JsonLifecycleRunStore(tmp_path).load("loop-fast")
    assert run is not None
    # Exactly one implement + one qa payload.
    assert run.workflow_steps.find("implement", 0) is not None
    assert run.workflow_steps.find("qa", 0) is not None
    assert run.workflow_steps.find("implement", 1) is None


def test_loop_requires_resolver(tmp_path: Path) -> None:
    _workspace(tmp_path)
    pipeline = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ScriptedReviewRuntime(kind, ["APPROVED"]),  # type: ignore[arg-type]
    )
    import pytest

    with pytest.raises(ValueError):
        pipeline.run_implement_review_loop(
            "loop-x", implement_step=_steps()[0], review_step=_steps()[1]
        )


# --- AC-4(a): the implement#N prompt carries the review#N-1 rejection digest -----------------


def test_implement_prompt_contains_prior_review_digest(tmp_path: Path) -> None:
    """RED-first (AC-4(a)): revert the digest-injection line ⇒ this assertion FAILS."""
    _workspace(tmp_path)
    # round 0 REJECTED → round 1 implement gets the review#0 digest → round 1 APPROVED.
    runtime = _ScriptedReviewRuntime(AgentRuntimeKind.FAKE, ["REJECTED", "APPROVED"])
    pipeline = _build(tmp_path, runtime, max_retries=2)

    result = pipeline.run_implement_review_loop(
        "digest-run", implement_step=_steps()[0], review_step=_steps()[1]
    )
    assert result.completed is True

    # The round-0 implement prompt carries NO digest (nothing preceded it).
    impl0 = next(r for r in runtime.received_requests if r.task_id == "digest-run#a0:implement")
    assert "handoff qa#" not in impl0.prompt

    # The round-1 implement prompt CONTAINS the review#0 (qa#0) REJECTED digest.
    impl1 = next(r for r in runtime.received_requests if r.task_id == "digest-run#a1:implement")
    assert "handoff qa#0" in impl1.prompt
    assert "verdict: REJECTED" in impl1.prompt


# --- AC-4(b): an evidence-less worker BLOCKS the loop via the STRUCTURAL gate ----------------


def test_loop_blocks_on_evidence_less_worker_via_structural_gate(tmp_path: Path) -> None:
    """RED-first (AC-4(b)): revert the structural-gate wiring ⇒ this assertion FAILS.

    The worker SUCCEEDS with an APPROVED verdict but produces NO ``artifact_refs``. The
    evidence-only runner gate blocks it structurally at ``implement#0`` — never reading the
    verdict. Pre-fix (verdict read directly, no gate) the APPROVED verdict would COMPLETE.
    """
    _workspace(tmp_path)
    runtime = _EvidencelessRuntime(AgentRuntimeKind.FAKE)
    pipeline = _build(tmp_path, runtime, max_retries=2)

    result = pipeline.run_implement_review_loop(
        "loop-noevidence", implement_step=_steps()[0], review_step=_steps()[1]
    )

    assert result.completed is False
    assert result.blocked is not None
    # STRUCTURAL block (missing artifact evidence) — NOT retry exhaustion.
    assert "artifact evidence" in result.blocked.reason
    assert "bounded retry" not in result.blocked.reason
    # Blocked during the very first attempt — no retry budget was consumed.
    assert result.attempts == 1

    run = JsonLifecycleRunStore(tmp_path).load("loop-noevidence")
    assert run is not None
    assert run.phase is LifecyclePhase.BLOCKED


# --- AC-4(d): a well-formed REJECTED round retries (never blocks) then COMPLETES -------------


def test_well_formed_rejected_round_retries_then_completes(tmp_path: Path) -> None:
    _workspace(tmp_path)
    runtime = _ScriptedReviewRuntime(AgentRuntimeKind.FAKE, ["REJECTED", "APPROVED"])
    pipeline = _build(tmp_path, runtime, max_retries=2)

    result = pipeline.run_implement_review_loop(
        "loop-rejretry", implement_step=_steps()[0], review_step=_steps()[1]
    )

    # Round 0 REJECTED did NOT block (well-formed evidence); round 1 APPROVED COMPLETED it.
    assert result.completed is True
    assert result.blocked is None
    assert result.attempts == 2
    assert [r.review_verdict for r in result.rounds] == ["REJECTED", "APPROVED"]

    # The round-1 implement received the review#0 digest (the retry consumed the rejection).
    impl1 = next(r for r in runtime.received_requests if r.task_id == "loop-rejretry#a1:implement")
    assert "handoff qa#0" in impl1.prompt
