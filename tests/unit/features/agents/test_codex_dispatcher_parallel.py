"""CodexAgentDispatcher reference-only parallel handoff behavior."""

from pathlib import Path

from dadaia_workspace.core.models.run_state import DispatcherMode, StageInvocation, StageStatus
from dadaia_workspace.infrastructure.codex_agent_dispatcher import CodexAgentDispatcher


def _make_invocation(
    tmp_path: Path, stage_id: str, *, parallel_group: str | None
) -> StageInvocation:
    return StageInvocation(
        run_id="run-parallel-99",
        stage_id=stage_id,
        workflow_name="fan-out-workflow",
        agent="software-engineer-python",
        inputs={"feature": "dispatcher"},
        expected_output_path=f"out/{stage_id}.md",
        must_include=(),
        parallel_group=parallel_group,
        invocation_path=str(tmp_path / f"{stage_id}.md"),
    )


def test_capabilities_supports_parallel_false() -> None:
    """CodexAgentDispatcher must not advertise unsupported parallel spawning."""
    cap = CodexAgentDispatcher().capabilities()
    assert cap.supports_parallel is False


def test_capabilities_mode_is_cli_only() -> None:
    """CodexAgentDispatcher reports CLI_ONLY because it writes manual handoffs."""
    cap = CodexAgentDispatcher().capabilities()
    assert cap.mode == DispatcherMode.CLI_ONLY


def test_capabilities_runtime_name_is_codex() -> None:
    """CodexAgentDispatcher.capabilities() must report runtime_name='codex'."""
    cap = CodexAgentDispatcher().capabilities()
    assert cap.runtime_name == "codex"


def test_parallel_dispatch_returns_result_for_each_invocation(tmp_path: Path) -> None:
    """dispatch_parallel() must return a tuple with len == len(invocations)."""
    invocations = tuple(
        _make_invocation(tmp_path, f"stage-{i}", parallel_group="specialists") for i in range(3)
    )
    results = CodexAgentDispatcher().dispatch_parallel(invocations)
    assert len(results) == 3


def test_parallel_dispatch_all_results_awaiting_gate(tmp_path: Path) -> None:
    """Every result from dispatch_parallel() must have status=AWAITING_GATE."""
    invocations = tuple(
        _make_invocation(tmp_path, f"p-stage-{i}", parallel_group="group-a") for i in range(2)
    )
    results = CodexAgentDispatcher().dispatch_parallel(invocations)
    assert all(r.status == StageStatus.AWAITING_GATE for r in results)


def test_parallel_dispatch_does_not_raise_for_parallel_group(tmp_path: Path) -> None:
    """dispatch_parallel() writes reference files but does not claim execution."""
    invocations = (
        _make_invocation(tmp_path, "alpha", parallel_group="group-x"),
        _make_invocation(tmp_path, "beta", parallel_group="group-x"),
    )
    results = CodexAgentDispatcher().dispatch_parallel(invocations)
    assert len(results) == 2


def test_parallel_dispatch_writes_all_invocation_files(tmp_path: Path) -> None:
    """dispatch_parallel() must write one file per invocation."""
    invocations = tuple(
        _make_invocation(tmp_path, f"item-{i}", parallel_group="batch") for i in range(3)
    )
    CodexAgentDispatcher().dispatch_parallel(invocations)
    for inv in invocations:
        assert Path(inv.invocation_path).exists(), f"Missing file for {inv.stage_id}"


def test_parallel_dispatch_writes_reference_only_note_for_each_parallel_stage(
    tmp_path: Path,
) -> None:
    """Each parallel_group handoff must state that Codex did not spawn agents."""
    invocations = (
        _make_invocation(tmp_path, "node-a", parallel_group="tier-1"),
        _make_invocation(tmp_path, "node-b", parallel_group="tier-1"),
    )
    CodexAgentDispatcher().dispatch_parallel(invocations)
    for inv in invocations:
        content = Path(inv.invocation_path).read_text()
        assert "reference-only" in content.lower()
        assert "does not spawn agents" in content.lower()


def test_parallel_dispatch_empty_tuple_returns_empty_tuple(tmp_path: Path) -> None:
    """dispatch_parallel() with zero invocations must return an empty tuple."""
    results = CodexAgentDispatcher().dispatch_parallel(())
    assert results == ()
