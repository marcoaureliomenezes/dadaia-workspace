"""WS-1 — LifecyclePipeline threads one run through phases with per-step harness mixing.

CRITICAL: AC7.2 — review steps NEVER gain production write paths (kept with AC7.1 positive
contrast inside it); first-block stops the ladder. Prompt-substring greps on fragment
banners (implement/qa_review/security_review) and the fragment-bundle field-list assert are
owned by ``test_fragment_gate_goldens.py`` (the pipeline golden pins the full prompts incl.
banners) — not repeated here. The former-deferred-workflow e2e is owned by the shared
``test_fragment_workflow_bodies.py`` suite; the no-workflow-is-deferred-anymore assert is
dead post-v0.1.30 (``DEFERRED_WORKFLOWS`` has been permanently empty since the fix it guarded).
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
        artifact_refs=(".dadaia/tmp/lifecycle-worker/dadaia-workspace/x.step-output.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _approved_for(context: str) -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="ok",
        artifact_refs=(f".dadaia/tmp/lifecycle-worker/{context}/x.step-output.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _no_verdict() -> AgentRunResult:
    return AgentRunResult(status=AgentRunStatus.SUCCEEDED, summary="no verdict")


def _pipeline(store: _MemoryRunStore, factory: object) -> LifecyclePipeline:
    return LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.16",
        run_store=store,
        runtime_factory=factory,  # type: ignore[arg-type]
    )


# --- ① full-ladder-completes + per-step harness mixing ----------------------------------


def test_pipeline_completes_full_ladder_and_mixes_harness_per_step() -> None:
    store = _MemoryRunStore()
    pipe = _pipeline(store, lambda kind: _KindFake(kind, _approved()))

    result = pipe.run("run-1", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    assert result.final_phase is LifecyclePhase.CLOSURE
    assert [s.label for s in result.steps] == [
        "implement",
        "review_combined",
        "close",
    ]
    assert all(s.accepted for s in result.steps)
    # One persisted run advancing through phases (start + 3 steps).
    assert store.saved["run-1"].phase is LifecyclePhase.CLOSURE

    mix_store = _MemoryRunStore()
    mix_pipe = _pipeline(mix_store, lambda kind: _KindFake(kind, _approved()))
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
    mix_result = mix_pipe.run("run-mix", steps)
    assert mix_result.completed is True
    assert mix_result.steps[0].runtime_kind is AgentRuntimeKind.CLAUDE_SDK
    assert mix_result.steps[1].runtime_kind is AgentRuntimeKind.CODEX_EXEC


def _task_specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    release = specs / "releases" / "task-release"
    release.mkdir(parents=True)
    (release / "TASKS.md").write_text(
        "# TASKS\n\n"
        "- [ ] **T01 - First task.**\n"
        "  - Validation: focused test.\n"
        "- [ ] **T02 - Second task.**\n",
        encoding="utf-8",
    )
    return specs


def test_pipeline_python_owns_task_marker_completion(tmp_path: Path) -> None:
    specs = _task_specs(tmp_path)
    store = _MemoryRunStore()
    pipe = LifecyclePipeline(
        context="demo",
        release_id="task-release",
        run_store=store,
        runtime_factory=lambda kind: _KindFake(kind, _approved_for("demo")),
        specs_dir=specs,
    )

    result = pipe.run("task-markers-complete", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    tasks = (specs / "releases" / "task-release" / "TASKS.md").read_text(encoding="utf-8")
    assert tasks.count("- [x] **T") == 2
    assert "- [ ] **T" not in tasks
    assert "- [-] **T" not in tasks


@pytest.mark.parametrize(
    ("task_lines", "done_markers"),
    [
        ("### [ ] T1 - First task\n### [ ] T2 - Second task\n", "### [x] T"),
        ("### T-1 - First task `[ ]`\n### T-2 - Second task `[ ]`\n", "`[x]`"),
        (
            "[ ] T-1\n**T-1 - First task**\n[ ] T-2\n**T-2 - Second task**\n",
            "[x] T-",
        ),
    ],
)
def test_pipeline_transitions_every_supported_release_task_grammar(
    tmp_path: Path, task_lines: str, done_markers: str
) -> None:
    specs = tmp_path / "specs"
    release = specs / "releases" / "task-release"
    release.mkdir(parents=True)
    (release / "TASKS.md").write_text(f"# TASKS\n\n{task_lines}", encoding="utf-8")
    store = _MemoryRunStore()
    pipe = LifecyclePipeline(
        context="demo",
        release_id="task-release",
        run_store=store,
        runtime_factory=lambda kind: _KindFake(kind, _approved_for("demo")),
        specs_dir=specs,
    )

    result = pipe.run("task-marker-grammar", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    tasks = (release / "TASKS.md").read_text(encoding="utf-8")
    assert tasks.count(done_markers) == 2
    assert "[ ]" not in tasks
    assert "[-]" not in tasks


def test_pipeline_refuses_success_when_tasks_have_no_recognizable_markers(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    release = specs / "releases" / "task-release"
    release.mkdir(parents=True)
    (release / "TASKS.md").write_text("# TASKS\n\n### T1 - Missing marker\n", encoding="utf-8")
    pipe = LifecyclePipeline(
        context="demo",
        release_id="task-release",
        run_store=_MemoryRunStore(),
        runtime_factory=lambda kind: _KindFake(kind, _approved_for("demo")),
        specs_dir=specs,
    )

    with pytest.raises(RuntimeError, match="no recognizable task markers"):
        pipe.run("task-marker-missing", implementation_ladder(AgentRuntimeKind.FAKE))


def test_pipeline_keeps_tasks_reserved_when_review_blocks(tmp_path: Path) -> None:
    specs = _task_specs(tmp_path)
    store = _MemoryRunStore()
    calls = 0

    class _RejectReviewFake:
        def runtime_kind(self) -> AgentRuntimeKind:
            return AgentRuntimeKind.FAKE

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            nonlocal calls
            calls += 1
            if calls == 1:
                return _approved_for("demo")
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="review rejected",
                artifact_refs=(".dadaia/tmp/lifecycle-worker/demo/rejected.step-output.json",),
                structured_output={"verdict": "REJECTED", "verdict_reason": "missing case"},
            )

    fake = _RejectReviewFake()
    pipe = LifecyclePipeline(
        context="demo",
        release_id="task-release",
        run_store=store,
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        specs_dir=specs,
        max_review_retries=0,
    )

    result = pipe.run("task-markers-blocked", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is False
    tasks = (specs / "releases" / "task-release" / "TASKS.md").read_text(encoding="utf-8")
    assert tasks.count("- [-] **T") == 2
    assert "- [ ] **T" not in tasks
    assert "- [x] **T" not in tasks


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
        release_id="v0.1.16",
        run_store=store,
        runtime_factory=lambda kind: _RecordingFake(kind, captured),
        prefix=prefix,
    )

    result = pipe.run("run-pfx", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    assert len(captured) == 3
    # Every step's worker prompt leads with the SAME cached prefix bytes (WS-7).
    assert all(req.prompt.startswith(prefix.text) for req in captured)
    # No "sonnet"/"opus" tier literals remain (LAW 2): the step model defaults from the
    # discrete catalog, and model_profile records the chosen option's effort.
    assert all(req.model_profile not in ("sonnet", "opus") for req in captured)
    assert all(req.model_profile == "high" for req in captured)

    from dadaia_workspace.core.harness_models import CODEX_HARNESS, options_for

    default_steps = implementation_ladder(AgentRuntimeKind.FAKE)
    expected_effort = options_for(CODEX_HARNESS)[0].effort
    assert all(step.model_profile == expected_effort for step in default_steps)
    assert all(step.model_profile not in ("sonnet", "opus") for step in default_steps)


# ---------------------------------------------------------------------------
# T-28-A-07 — pipeline threads resolved policy + persists the snapshot before step 1
# ---------------------------------------------------------------------------


class _PolicyRecordingFake:
    def __init__(self, kind: AgentRuntimeKind) -> None:
        self.kind = kind
        self.requests: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.requests.append(request)
        return _approved()


def _snapshot_for_implementation() -> object:
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowExecutionPolicyResolver,
    )
    from tests.unit.features.lifecycle._workflow_catalog import library_workflow_catalog

    resolver = WorkflowExecutionPolicyResolver(catalog=library_workflow_catalog())
    return resolver.resolve("implementation_reviews", context="default")


def test_pipeline_threads_resolved_model_and_persists_snapshot() -> None:
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy

    store = _MemoryRunStore()
    recorder = _PolicyRecordingFake(AgentRuntimeKind.FAKE)
    snapshot = _snapshot_for_implementation()

    pipe = LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.28",
        run_store=store,
        runtime_factory=lambda kind: recorder,  # type: ignore[arg-type, return-value]
        policy_snapshot=snapshot,  # type: ignore[arg-type]
    )
    base = implementation_ladder(AgentRuntimeKind.FAKE)
    steps = apply_resolved_policy(base, snapshot)  # type: ignore[arg-type]
    result = pipe.run("run-policy", steps)

    assert result.completed is True
    # Each request carried the resolved concrete model from the snapshot.
    impl_req = recorder.requests[0]
    assert impl_req.resolved_model is not None
    assert impl_req.resolved_model.profile_id == "codex-implementation-standard"
    qa_req = recorder.requests[1]
    assert qa_req.resolved_model is not None
    assert qa_req.resolved_model.profile_id == "codex-review-deep"
    # The persisted run carries the resolved-policy snapshot (LAW 6).
    persisted = store.saved["run-policy"]
    assert persisted.workflow_policy is not None
    assert persisted.workflow_policy.workflow_id == "implementation_reviews"
    assert persisted.workflow_policy.step("implement") is not None


# ---------------------------------------------------------------------------
# ② apply_resolved_policy param: pi->PI_HEADLESS / codex->CODEX_EXEC /
#    FAKE-preserved-with-model-threaded (v0.1.29 / T-29-A-06)
# ---------------------------------------------------------------------------


def _resolve(default_harness: str | None = None):  # type: ignore[no-untyped-def]
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowExecutionPolicyResolver,
    )
    from tests.unit.features.lifecycle._workflow_catalog import library_workflow_catalog

    resolver = WorkflowExecutionPolicyResolver(catalog=library_workflow_catalog())
    return resolver.resolve(
        "implementation_reviews", context="default", default_harness=default_harness
    )


@pytest.mark.parametrize(
    "case_id,default_harness,base_kind,expect_kind_of_step,expect_fake_preserved",
    [
        (
            "pi-resolves-pi-headless",
            "pi",
            AgentRuntimeKind.CODEX_EXEC,
            AgentRuntimeKind.PI_HEADLESS,
            False,
        ),
        (
            "codex-resolves-codex-exec",
            None,
            AgentRuntimeKind.PI_HEADLESS,
            AgentRuntimeKind.CODEX_EXEC,
            False,
        ),
        ("fake-preserved-for-dry-run", "pi", AgentRuntimeKind.FAKE, AgentRuntimeKind.FAKE, True),
    ],
    ids=["pi-resolves-pi-headless", "codex-resolves-codex-exec", "fake-preserved-for-dry-run"],
)
def test_apply_resolved_policy_owns_runtime_kind_from_resolved_harness(
    case_id: str,
    default_harness: str | None,
    base_kind: AgentRuntimeKind,
    expect_kind_of_step: AgentRuntimeKind,
    expect_fake_preserved: bool,
) -> None:
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy

    snapshot = _resolve(default_harness=default_harness)
    base = implementation_ladder(base_kind)
    steps = apply_resolved_policy(base, snapshot)  # type: ignore[arg-type]
    for step in steps:
        assert step.runtime_kind is expect_kind_of_step
        if expect_fake_preserved:
            # ARCHITECT MEDIUM: fake is never a resolved harness — the governed model is
            # still threaded for auditability even though runtime_kind stays FAKE.
            assert step.resolved_model is not None
            assert step.resolved_model.harness == "pi"


# ---------------------------------------------------------------------------
# T-66-08 (FR7) — _scope unions extra_allowed_paths for non-review steps only
# (AC7.1 / AC7.2). Gated on step.is_review is False (ARCHITECT MEDIUM-2) — NOT
# a label == "implement" string match, so any create-kind (non-review) step
# gets the union, and every review step (is_review=True) stays handoff-only.
# ---------------------------------------------------------------------------


def _pipeline_for_scope() -> LifecyclePipeline:
    return LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.66",
        run_store=_MemoryRunStore(),
        runtime_factory=lambda kind: None,  # type: ignore[arg-type,return-value]
    )


def _step_with(
    label: str, *, is_review: bool, extra_allowed_paths: tuple[str, ...]
) -> PipelineStep:
    return PipelineStep(
        label=label,
        role="software-engineer",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        runtime_kind=AgentRuntimeKind.FAKE,
        is_review=is_review,
        extra_allowed_paths=extra_allowed_paths,
    )


def test_scope_extra_allowed_paths_union_for_create_steps_ignored_for_review_ac71_ac72() -> None:
    """AC7.1: extra_allowed_paths fed into _scope for a non-review (create) step yields
    allowed_paths containing both the handoff-dir glob AND the extra path — the positive
    contrast that attributes AC7.2's block to review-ness, nothing else.

    AC7.2 (CRITICAL): the SAME extra_allowed_paths value fed into a review step
    (is_review=True) is IGNORED — the union only applies to non-review (create) steps;
    review steps stay handoff-only. Regression guard proving review steps never gain
    production write rights.

    Additive-optional regression guard: a non-review step with the default empty
    extra_allowed_paths behaves exactly as before this FR.
    """
    create_step = _step_with("implement", is_review=False, extra_allowed_paths=("repos/x/src/**",))
    create_scope = _pipeline_for_scope()._scope(create_step, "run1")
    assert ".dadaia/tmp/lifecycle-worker/dadaia-workspace/**" in create_scope.allowed_paths
    assert "repos/x/src/**" in create_scope.allowed_paths

    review_step = _step_with("review_qa", is_review=True, extra_allowed_paths=("repos/x/src/**",))
    review_scope = _pipeline_for_scope()._scope(review_step, "run1")
    assert review_scope.allowed_paths == (".dadaia/tmp/lifecycle-worker/dadaia-workspace/**",)
    assert "repos/x/src/**" not in review_scope.allowed_paths

    no_extra_step = _step_with("implement", is_review=False, extra_allowed_paths=())
    no_extra_scope = _pipeline_for_scope()._scope(no_extra_step, "run1")
    assert no_extra_scope.allowed_paths == (".dadaia/tmp/lifecycle-worker/dadaia-workspace/**",)

    close_step = implementation_ladder(AgentRuntimeKind.FAKE)[-1]
    close_scope = _pipeline(_MemoryRunStore(), lambda kind: _KindFake(kind, _approved()))._scope(
        close_step, "close-scope"
    )
    assert "repos/dadaia-workspace/specs/releases/v0.1.16/**" in (close_scope.allowed_paths)
    assert all("{" not in path for path in close_scope.allowed_paths)


def test_close_requires_real_closure_deliverable(tmp_path: Path) -> None:
    handoff = (
        tmp_path
        / ".dadaia"
        / "tmp"
        / "lifecycle-worker"
        / "dadaia-workspace"
        / "x.step-output.json"
    )
    handoff.parent.mkdir(parents=True)
    handoff.write_text("{}", encoding="utf-8")
    store = _MemoryRunStore()
    pipe = LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.16",
        run_store=store,
        runtime_factory=lambda kind: _KindFake(kind, _approved()),
        artifact_root=tmp_path,
    )

    result = pipe.run("close-deliverable", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is False
    assert result.blocked is not None
    assert result.blocked.blocked_at_step == "close"
    assert "no deliverable" in result.blocked.reason
