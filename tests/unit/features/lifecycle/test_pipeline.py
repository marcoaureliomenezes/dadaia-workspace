"""WS-1 — LifecyclePipeline threads one run through phases with per-step harness mixing."""

from __future__ import annotations

from dataclasses import dataclass

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.lifecycle.pipeline import (
    LifecyclePipeline,
    PipelineStep,
    implementation_ladder,
)
from dadaia_workspace.features.lifecycle.prompt_builder import PromptPrefix


@dataclass(frozen=True)
class _KindFake:
    kind: AgentRuntimeKind
    result: AgentRunResult

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return self.result


class _MemoryRunStore:
    def __init__(self) -> None:
        self.saved: dict[str, LifecycleRun] = {}
        self.save_count = 0

    def save(self, run: LifecycleRun) -> None:
        self.saved[run.run_id] = run
        self.save_count += 1

    def load(self, run_id: str) -> LifecycleRun | None:
        return self.saved.get(run_id)

    def resume(self, run_id: str) -> LifecycleRun:
        run = self.saved.get(run_id)
        if run is None:
            raise LifecycleRunStoreError(message="missing", path=None)
        return run


def _approved() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="ok",
        artifact_refs=(".dadaia/handoff/dadaia-workspace/x.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _no_verdict() -> AgentRunResult:
    return AgentRunResult(status=AgentRunStatus.SUCCEEDED, summary="no verdict")


def _pipeline(store: _MemoryRunStore, factory: object) -> LifecyclePipeline:
    return LifecyclePipeline(
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
        run_store=store,
        runtime_factory=factory,  # type: ignore[arg-type]
    )


def test_pipeline_completes_full_ladder_when_every_step_approves() -> None:
    store = _MemoryRunStore()
    pipe = _pipeline(store, lambda kind: _KindFake(kind, _approved()))

    result = pipe.run("run-1", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    assert result.final_phase is LifecyclePhase.CLOSURE
    assert [s.label for s in result.steps] == [
        "implement",
        "review_qa",
        "review_security",
        "review_code",
    ]
    assert all(s.accepted for s in result.steps)
    # One persisted run advancing through phases (start + 4 steps).
    assert store.saved["run-1"].phase is LifecyclePhase.CLOSURE


def test_pipeline_mixes_harness_per_step() -> None:
    store = _MemoryRunStore()
    pipe = _pipeline(store, lambda kind: _KindFake(kind, _approved()))
    steps = (
        PipelineStep(
            "implement",
            "software-engineer",
            LifecyclePhase.IMPLEMENTATION,
            LifecyclePhase.QA_REVIEW,
            AgentRuntimeKind.CLAUDE_SDK,
        ),
        PipelineStep(
            "review_qa",
            "qa-engineer",
            LifecyclePhase.QA_REVIEW,
            LifecyclePhase.SECURITY_REVIEW,
            AgentRuntimeKind.CODEX_EXEC,
        ),
    )

    result = pipe.run("run-mix", steps)

    assert result.completed is True
    assert result.steps[0].runtime_kind is AgentRuntimeKind.CLAUDE_SDK
    assert result.steps[1].runtime_kind is AgentRuntimeKind.CODEX_EXEC


def test_pipeline_stops_at_first_blocked_step() -> None:
    store = _MemoryRunStore()

    def factory(kind: AgentRuntimeKind) -> _KindFake:
        # The security step's harness yields no verdict → its gate blocks.
        if kind is AgentRuntimeKind.CLAUDE_SDK:
            return _KindFake(kind, _no_verdict())
        return _KindFake(kind, _approved())

    pipe = _pipeline(store, factory)
    steps = (
        PipelineStep(
            "implement",
            "software-engineer",
            LifecyclePhase.IMPLEMENTATION,
            LifecyclePhase.QA_REVIEW,
            AgentRuntimeKind.FAKE,
        ),
        PipelineStep(
            "review_qa",
            "qa-engineer",
            LifecyclePhase.QA_REVIEW,
            LifecyclePhase.SECURITY_REVIEW,
            AgentRuntimeKind.FAKE,
        ),
        PipelineStep(
            "review_security",
            "security-reviewer",
            LifecyclePhase.SECURITY_REVIEW,
            LifecyclePhase.CODE_REVIEW,
            AgentRuntimeKind.CLAUDE_SDK,
        ),
        PipelineStep(
            "review_code",
            "code-reviewer",
            LifecyclePhase.CODE_REVIEW,
            LifecyclePhase.CLOSURE,
            AgentRuntimeKind.FAKE,
        ),
    )

    result = pipe.run("run-block", steps)

    assert result.completed is False
    assert result.blocked is not None
    assert [s.label for s in result.steps] == ["implement", "review_qa", "review_security"]
    assert result.steps[0].accepted and result.steps[1].accepted
    assert result.steps[2].accepted is False
    assert result.final_phase is LifecyclePhase.BLOCKED


class _RecordingFake:
    def __init__(self, kind: AgentRuntimeKind, captured: list[AgentRunRequest]) -> None:
        self._kind = kind
        self._captured = captured

    def runtime_kind(self) -> AgentRuntimeKind:
        return self._kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self._captured.append(request)
        return _approved()


def test_pipeline_reuses_cacheable_prefix_and_applies_step_tiers() -> None:
    captured: list[AgentRunRequest] = []
    store = _MemoryRunStore()
    prefix = PromptPrefix.from_sections({"constitution": "C", "memory": "M"})
    pipe = LifecyclePipeline(
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
        run_store=store,
        runtime_factory=lambda kind: _RecordingFake(kind, captured),
        prefix=prefix,
    )

    result = pipe.run("run-pfx", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    assert len(captured) == 4
    # Every step's worker prompt leads with the SAME cached prefix bytes (WS-7).
    assert all(req.prompt.startswith(prefix.text) for req in captured)
    # No "sonnet"/"opus" tier literals remain (LAW 2): the step model defaults from the
    # discrete catalog, and model_profile records the chosen option's effort.
    assert all(req.model_profile not in ("sonnet", "opus") for req in captured)
    assert all(req.model_profile == "high" for req in captured)


def test_implementation_ladder_default_model_comes_from_catalog() -> None:
    from dadaia_workspace.core.harness_models import CODEX_HARNESS, options_for
    from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder

    steps = implementation_ladder(AgentRuntimeKind.FAKE)
    expected_effort = options_for(CODEX_HARNESS)[0].effort
    assert all(step.model_profile == expected_effort for step in steps)
    assert all(step.model_profile not in ("sonnet", "opus") for step in steps)


def test_implementation_ladder_honors_explicit_discrete_model() -> None:
    from dadaia_workspace.core.harness_models import validate
    from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder

    chosen = validate("codex", "gpt-5.5:medium")
    steps = implementation_ladder(AgentRuntimeKind.FAKE, model=chosen)
    assert all(step.model_profile == "medium" for step in steps)
