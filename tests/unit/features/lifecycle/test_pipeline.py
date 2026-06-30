"""WS-1 — LifecyclePipeline threads one run through phases with per-step harness mixing."""

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


# --- WS-6: fragment-sourced prompts for the implementation + QA-review steps ---------


def _capture_pipeline(captured: list[AgentRunRequest]) -> LifecyclePipeline:
    store = _MemoryRunStore()
    return LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.24",
        run_store=store,
        runtime_factory=lambda kind: _RecordingFake(kind, captured),
    )


def test_implementation_ladder_attaches_fragment_bundles_to_two_steps() -> None:
    from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder

    steps = implementation_ladder(AgentRuntimeKind.FAKE)
    by_label = {step.label: step for step in steps}

    # The implementation step runs on the TDD implement fragment, citing the shared
    # write-scope / anti-slop / output-handoff disciplines + the self-verify fragment.
    assert by_label["implement"].fragment_id == "implementation.implement_tdd"
    assert by_label["implement"].shared_fragment_ids == (
        "shared.write_scope",
        "shared.anti_slop",
        "shared.output_handoff",
        "implementation.self_verify",
    )
    # The QA review step runs on the qa-review fragment.
    assert by_label["review_qa"].fragment_id == "implementation.qa_review"
    # v0.1.43: the security + code review steps now run on their own gate fragments,
    # each citing the shared anti-slop + output-handoff disciplines.
    assert by_label["review_security"].fragment_id == "implementation.security_review"
    assert by_label["review_security"].shared_fragment_ids == (
        "shared.anti_slop",
        "shared.output_handoff",
    )
    assert by_label["review_code"].fragment_id == "implementation.code_review"
    assert by_label["review_code"].shared_fragment_ids == (
        "shared.anti_slop",
        "shared.output_handoff",
    )


def test_implementation_and_qa_steps_emit_fragment_sourced_prompts() -> None:
    from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder

    captured: list[AgentRunRequest] = []
    pipe = _capture_pipeline(captured)

    result = pipe.run("run-frag", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    by_label = {req.task_id.rsplit(":", 1)[1]: req for req in captured}

    implement_prompt = by_label["implement"].prompt
    # Fragment-sourced: carries the fragment id banners (own + cited shared), NOT the
    # generic "Run the ... step" suffix.
    assert "fragment:implementation.implement_tdd" in implement_prompt
    assert "fragment:shared.write_scope" in implement_prompt
    assert "fragment:implementation.self_verify" in implement_prompt
    assert "Run the implement step" not in implement_prompt
    # The output schema the fragment declares reaches the prompt.
    assert "implementation-result-v1" in implement_prompt

    qa_prompt = by_label["review_qa"].prompt
    assert "fragment:implementation.qa_review" in qa_prompt
    assert "Run the review_qa step" not in qa_prompt
    assert "qa-review-verdict-v1" in qa_prompt

    # v0.1.43: the security review step is now fragment-sourced, not generic.
    security_prompt = by_label["review_security"].prompt
    assert "fragment:implementation.security_review" in security_prompt
    assert "Run the review_security step" not in security_prompt


# ---------------------------------------------------------------------------
# T-30-E-04 — audit / research / bug_report are no longer deferred fail-loud stubs.
# Each ships a real fragment+gate workflow body; DEFERRED_WORKFLOWS is now empty, and the
# bodies advance/block via their Python gate rather than raising NotImplementedError (A28).
# ---------------------------------------------------------------------------


def test_no_workflow_is_deferred_anymore() -> None:
    from dadaia_workspace.features.lifecycle import workflows

    # The fail-loud stub callables are gone — no NotImplementedError entry point remains.
    assert workflows.DEFERRED_WORKFLOWS == ()
    assert not hasattr(workflows, "audit") or not callable(
        getattr(workflows.audit, "_deferred", None)
    )


@pytest.mark.parametrize(
    ("workflow_cls_name", "labels"),
    [
        ("AuditWorkflow", ["audit_scope", "drift_scan", "triage", "audit_disposition_gate"]),
        (
            "ResearchWorkflow",
            ["research_scope", "investigate", "synthesis", "research_synthesis_gate"],
        ),
        ("BugReportWorkflow", ["bug_intake", "dedupe", "bug_write", "bug_record_gate"]),
    ],
)
def test_former_deferred_workflows_run_via_python_gate(
    tmp_path: Path, workflow_cls_name: str, labels: list[str]
) -> None:
    """A28: each former-deferred body runs end-to-end on the FAKE runtime via its gate.

    Proves the body no longer raises ``NotImplementedError`` — it advances through every
    model step and the terminal Python gate completes the run.
    """
    from dadaia_workspace.features.lifecycle import workflows
    from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
    from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore

    # AgentRunRequest/Result/Status/Kind, dataclass, LifecyclePhase are module-level imports.

    context = "dadaia-workspace"
    release = "v0.1.30"
    specs = tmp_path / "repos" / context / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "bugs").mkdir(parents=True)
    (specs / "releases" / release).mkdir(parents=True)
    (specs / "memory" / "architecture.md").write_text("# a\n", encoding="utf-8")
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")

    @dataclass(frozen=True)
    class _Fake:
        kind: AgentRuntimeKind

        def runtime_kind(self) -> AgentRuntimeKind:
            return self.kind

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            ref = (
                f"repos/{context}/specs/bugs/x.md"
                if request.task_id.endswith(":bug_write")
                else f".dadaia/handoff/{context}/s.handoff.json"
            )
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="ok",
                artifact_refs=(ref,),
                structured_output={"verdict": "APPROVED"},
            )

    selector = ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=release, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )
    cls = getattr(workflows, workflow_cls_name)
    wf = cls(
        context=context,
        release_id=release,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _Fake(kind),
        context_selector=selector,
    )
    result = wf.run("run-1")  # must not raise NotImplementedError

    assert result.completed is True
    assert [s.label for s in result.steps] == labels
    assert result.steps[-1].is_gate is True


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
        library_workflow_catalog,
    )

    resolver = WorkflowExecutionPolicyResolver(catalog=library_workflow_catalog())
    return resolver.resolve("implementation", context="default")


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
    assert persisted.workflow_policy.workflow_id == "implementation"
    assert persisted.workflow_policy.step("implement") is not None


# ---------------------------------------------------------------------------
# v0.1.29 / T-29-A-06 — apply_resolved_policy owns runtime_kind from resolved harness
# ---------------------------------------------------------------------------


def _resolve(default_harness: str | None = None):  # type: ignore[no-untyped-def]
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowExecutionPolicyResolver,
        library_workflow_catalog,
    )

    resolver = WorkflowExecutionPolicyResolver(catalog=library_workflow_catalog())
    return resolver.resolve("implementation", context="default", default_harness=default_harness)


def test_apply_resolved_policy_sets_runtime_kind_from_resolved_harness() -> None:
    # AC-3: a pi-resolved snapshot drives PI_HEADLESS on every step when the base
    # ladder is built on a real (non-fake) harness.
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy

    snapshot = _resolve(default_harness="pi")
    base = implementation_ladder(AgentRuntimeKind.CODEX_EXEC)
    steps = apply_resolved_policy(base, snapshot)  # type: ignore[arg-type]
    for step in steps:
        assert step.runtime_kind is AgentRuntimeKind.PI_HEADLESS


def test_apply_resolved_policy_codex_resolves_codex_exec() -> None:
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy

    snapshot = _resolve()  # default codex
    base = implementation_ladder(AgentRuntimeKind.PI_HEADLESS)
    steps = apply_resolved_policy(base, snapshot)  # type: ignore[arg-type]
    for step in steps:
        assert step.runtime_kind is AgentRuntimeKind.CODEX_EXEC


def test_apply_resolved_policy_preserves_fake_for_dry_run() -> None:
    # ARCHITECT MEDIUM: a base ladder built on FAKE (dry-run / test) keeps FAKE even
    # though the snapshot resolves a governed harness — fake is never a resolved harness.
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy

    snapshot = _resolve(default_harness="pi")
    base = implementation_ladder(AgentRuntimeKind.FAKE)
    steps = apply_resolved_policy(base, snapshot)  # type: ignore[arg-type]
    for step in steps:
        assert step.runtime_kind is AgentRuntimeKind.FAKE
        # The governed model is still threaded for auditability.
        assert step.resolved_model is not None
        assert step.resolved_model.harness == "pi"
