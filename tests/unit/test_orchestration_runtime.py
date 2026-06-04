"""Parametric runtime behavior across all 4 dispatcher modes."""

from pathlib import Path

import pytest

from dadaia_workspace.core.models.run_state import (
    DispatcherCapabilities,
    DispatcherMode,
    StageInvocation,
    StageStatus,
)
from dadaia_workspace.infrastructure.claude_agent_dispatcher import ClaudeAgentDispatcher
from dadaia_workspace.infrastructure.cli_agent_dispatcher import (
    CliAgentDispatcher,
    OpenCodeAgentDispatcher,
)
from dadaia_workspace.infrastructure.codex_agent_dispatcher import CodexAgentDispatcher


def _make_invocation(tmp_path: Path, *, parallel_group: str | None = None) -> StageInvocation:
    return StageInvocation(
        run_id="r1",
        stage_id="discover",
        workflow_name="demo",
        agent="product-engineer",
        inputs={"context": "ws"},
        expected_output_path="out/discover.md",
        must_include=("Findings",),
        parallel_group=parallel_group,
        invocation_path=str(tmp_path / "inv.md"),
    )


@pytest.mark.parametrize(
    ("factory", "expected_runtime", "expected_mode", "expected_parallel"),
    [
        (ClaudeAgentDispatcher, "claude", DispatcherMode.NATIVE, True),
        (CliAgentDispatcher, "cli", DispatcherMode.CLI_ONLY, False),
        (OpenCodeAgentDispatcher, "opencode", DispatcherMode.BEST_EFFORT_SEQUENTIAL, False),
        (CodexAgentDispatcher, "codex", DispatcherMode.CLI_ONLY, False),
    ],
)
def test_capabilities_match_runtime(
    factory: type, expected_runtime: str, expected_mode: DispatcherMode, expected_parallel: bool
) -> None:
    cap: DispatcherCapabilities = factory().capabilities()
    assert cap.runtime_name == expected_runtime
    assert cap.mode == expected_mode
    assert cap.supports_parallel is expected_parallel


def test_claude_dispatch_writes_invocation_with_parallel_header(tmp_path: Path) -> None:
    inv = _make_invocation(tmp_path, parallel_group="specialists")
    result = ClaudeAgentDispatcher().dispatch(inv)
    assert result.status == StageStatus.AWAITING_GATE
    content = Path(inv.invocation_path).read_text()
    assert "parallel_group: `specialists`" in content
    assert "dispatch all members in a single host-agent message" in content


def test_cli_dispatch_omits_parallel_note_when_no_group(tmp_path: Path) -> None:
    inv = _make_invocation(tmp_path)
    CliAgentDispatcher().dispatch(inv)
    content = Path(inv.invocation_path).read_text()
    assert "cli-only" in content.lower()
    assert "parallel_group" not in content


def test_opencode_marks_parallel_group_as_best_effort(tmp_path: Path) -> None:
    inv = _make_invocation(tmp_path, parallel_group="specialists")
    OpenCodeAgentDispatcher().dispatch(inv)
    content = Path(inv.invocation_path).read_text()
    assert "OpenCode does not support true parallel agent dispatch" in content


def test_codex_parallel_group_dispatch_writes_reference_handoff(tmp_path: Path) -> None:
    """Codex writes a manual handoff for parallel_group without claiming execution."""
    inv = _make_invocation(tmp_path, parallel_group="specialists")
    results = CodexAgentDispatcher().dispatch_parallel((inv,))
    assert len(results) == 1
    assert results[0].status == StageStatus.AWAITING_GATE
    content = Path(inv.invocation_path).read_text()
    assert "reference-only" in content.lower()
    assert "no codex agent process was spawned" in content.lower()


def test_codex_accepts_sequential_dispatch(tmp_path: Path) -> None:
    inv = _make_invocation(tmp_path)
    results = CodexAgentDispatcher().dispatch_parallel((inv,))
    assert len(results) == 1
    assert results[0].status == StageStatus.AWAITING_GATE
