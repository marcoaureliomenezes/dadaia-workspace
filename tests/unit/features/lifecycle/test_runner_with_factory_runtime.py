"""W5 — the factory emits the production FakeAgentRuntime, which satisfies the
LifecycleAgentRunner injection contract end-to-end (advances the phase on an
APPROVED worker result)."""

from __future__ import annotations

import pytest

from dadaia_workspace.container import build_agent_runtime
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
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)
from dadaia_workspace.infrastructure.claude_sdk_runtime import ClaudeSdkAdapter
from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter


def _run() -> LifecycleRun:
    return LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
        command="implement",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="implementation",
        idempotency_key="resume-1",
    )


def test_factory_fake_is_the_production_fake_runtime() -> None:
    assert isinstance(build_agent_runtime(AgentRuntimeKind.FAKE), FakeAgentRuntime)


@pytest.mark.parametrize(
    ("kind", "expected_adapter"),
    [
        (AgentRuntimeKind.FAKE, FakeAgentRuntime),
        (AgentRuntimeKind.CODEX_EXEC, CodexExecAdapter),
        (AgentRuntimeKind.CLAUDE_SDK, ClaudeSdkAdapter),
        (AgentRuntimeKind.PI_HEADLESS, PiHeadlessAdapter),
    ],
)
def test_factory_maps_every_kind_to_its_adapter(
    kind: AgentRuntimeKind, expected_adapter: type
) -> None:
    # The factory is total over the enum: each AgentRuntimeKind resolves to its
    # concrete adapter, and the adapter reports back the same kind. This closes the
    # previously-untested "kind -> adapter" wiring branch for ALL harnesses.
    runtime = build_agent_runtime(kind)
    assert isinstance(runtime, expected_adapter)
    assert runtime.runtime_kind() is kind


def test_factory_pi_headless_carries_real_git_seam() -> None:
    # The Layer-2 PI wiring the operator reaches via `--harness pi` must construct a
    # PiHeadlessAdapter with a real git client — that git seam is what gives PI its
    # Ring-2 changed-paths write boundary (not a model self-report).
    runtime = build_agent_runtime(AgentRuntimeKind.PI_HEADLESS)
    assert isinstance(runtime, PiHeadlessAdapter)
    assert runtime._git is not None
    assert hasattr(runtime._git, "diff_name_only")


def test_factory_fake_runtime_satisfies_runner_injection_contract() -> None:
    # The exact type the factory emits, given an APPROVED worker result, drives the
    # runner to an accepted transition — proving factory output ⊨ the runner contract.
    approved = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="qa approved",
        artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        structured_output={"verdict": "APPROVED", "task_group": "T-016-05"},
    )
    runtime: AgentRuntimePort = FakeAgentRuntime(result=approved)
    request = AgentRunRequest(
        role="qa-engineer",
        prompt="review task group",
        runtime=AgentRuntimeKind.FAKE,
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )

    decision = LifecycleAgentRunner(runtime=runtime).run(
        _run(),
        AgentRunnerInput(
            request=request,
            target_phase=LifecyclePhase.QA_REVIEW,
            requirements=(),
            current_step="qa-review",
        ),
    )

    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.QA_REVIEW
    assert decision.run.blocked is None
