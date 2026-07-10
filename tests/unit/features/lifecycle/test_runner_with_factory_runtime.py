"""W5 — the factory emits the production FakeAgentRuntime, which satisfies the
LifecycleAgentRunner injection contract end-to-end (advances the phase on an
APPROVED worker result).

PI git seam = Ring-2 boundary wiring — kept.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.container import build_agent_runtime
from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.infrastructure.claude_sdk_runtime import ClaudeSdkAdapter
from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter


@pytest.mark.parametrize(
    ("kind", "expected_adapter"),
    [
        (AgentRuntimeKind.FAKE, FakeAgentRuntime),
        (AgentRuntimeKind.CODEX_EXEC, CodexExecAdapter),
        (AgentRuntimeKind.CLAUDE_SDK, ClaudeSdkAdapter),
        (AgentRuntimeKind.PI_HEADLESS, PiHeadlessAdapter),
    ],
)
def test_factory_total_over_kind_maps_to_adapter_and_echoes_kind(
    kind: AgentRuntimeKind, expected_adapter: type
) -> None:
    # The factory is total over the enum: each AgentRuntimeKind resolves to its
    # concrete adapter (FAKE is the same production FakeAgentRuntime the runner
    # injection contract exercises), and the adapter reports back the same kind.
    runtime = build_agent_runtime(kind)
    assert isinstance(runtime, expected_adapter)
    assert runtime.runtime_kind() is kind


def test_pi_adapter_carries_real_git_seam() -> None:
    # The Layer-2 PI wiring the operator reaches via `--harness pi` must construct a
    # PiHeadlessAdapter with a real git client — that git seam is what gives PI its
    # Ring-2 changed-paths write boundary (not a model self-report).
    runtime = build_agent_runtime(AgentRuntimeKind.PI_HEADLESS)
    assert isinstance(runtime, PiHeadlessAdapter)
    assert runtime._git is not None
    assert hasattr(runtime._git, "diff_name_only")
