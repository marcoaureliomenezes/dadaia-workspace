"""Unit tests for FakeAgentRuntime request recording (T-28-A-06).

The fake adapter records each request so tests can assert policy resolution threaded the
right ``resolved_model`` into each step's request — without a live provider. The optional
``on_run`` hook lets a test mutate external state between steps (AC-6 demo seam).
"""

from __future__ import annotations

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.models.workflow_execution import PolicySource, ResolvedModelConfig
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime


def _request(model: ResolvedModelConfig | None = None) -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="do work",
        runtime=AgentRuntimeKind.FAKE,
        context="dadaia-workspace",
        release_id="v0.1.28",
        resolved_model=model,
    )


def _resolved(model: str = "gpt-5.5", reasoning: str = "medium") -> ResolvedModelConfig:
    return ResolvedModelConfig(
        profile_id="codex-implementation-standard",
        harness="codex",
        model=model,
        reasoning=reasoning,
        source=PolicySource.LIBRARY_DEFAULT,
    )


def test_fake_runtime_records_resolves_and_injects() -> None:
    runtime = FakeAgentRuntime()
    a = _request(_resolved("gpt-5.5", "medium"))
    b = _request(_resolved("gpt-5.5", "high"))
    c = _request(None)
    runtime.run(a)
    runtime.run(b)
    runtime.run(c)

    assert runtime.received_requests == [a, b, c]
    assert runtime.received_models[0] is not None
    assert runtime.received_models[0].model == "gpt-5.5"
    assert runtime.received_models[0].reasoning == "medium"
    assert runtime.received_models[2] is None

    default_result = FakeAgentRuntime().run(_request())
    assert default_result.status is AgentRunStatus.SUCCEEDED

    canned = AgentRunResult(status=AgentRunStatus.SUCCEEDED, summary="canned")
    injected_runtime = FakeAgentRuntime(result=canned)
    assert injected_runtime.run(_request()) is canned

    seen: list[str | None] = []

    def hook(req: AgentRunRequest) -> None:
        seen.append(req.resolved_model.model if req.resolved_model else None)

    hooked_runtime = FakeAgentRuntime(on_run=hook)
    hooked_runtime.run(_request(_resolved("gpt-5.5", "medium")))
    hooked_runtime.run(_request(_resolved("gpt-5.3-codex", "medium")))
    assert seen == ["gpt-5.5", "gpt-5.3-codex"]
