"""T-10 — CodexAgentDispatcher sequential dispatch (AC4)."""

from pathlib import Path

from dadaia_workspace.core.models.run_state import StageInvocation, StageStatus
from dadaia_workspace.infrastructure.codex_agent_dispatcher import CodexAgentDispatcher


def _make_invocation(
    tmp_path: Path,
    *,
    parallel_group: str | None = None,
    stage_id: str = "analyse",
) -> StageInvocation:
    return StageInvocation(
        run_id="run-abc123",
        stage_id=stage_id,
        workflow_name="my-workflow",
        agent="product-engineer",
        inputs={"context": "dadaia-workspace"},
        expected_output_path="out/analyse.md",
        must_include=("Summary",),
        parallel_group=parallel_group,
        invocation_path=str(tmp_path / f"{stage_id}.md"),
    )


def test_sequential_dispatch_writes_invocation_file(tmp_path: Path) -> None:
    """dispatch() must write the invocation file to disk."""
    inv = _make_invocation(tmp_path)
    result = CodexAgentDispatcher().dispatch(inv)

    invocation_file = Path(inv.invocation_path)
    assert invocation_file.exists(), "Invocation file must be written to disk"
    assert result.status == StageStatus.AWAITING_GATE


def test_sequential_dispatch_result_contains_run_and_stage_ids(tmp_path: Path) -> None:
    """dispatch() result must reference run_id and stage_id."""
    inv = _make_invocation(tmp_path)
    result = CodexAgentDispatcher().dispatch(inv)

    assert result.run_id == "run-abc123"
    assert result.stage_id == "analyse"


def test_sequential_dispatch_file_contains_required_identifiers(tmp_path: Path) -> None:
    """Invocation file must contain stage_id, agent, and run_id."""
    inv = _make_invocation(tmp_path)
    CodexAgentDispatcher().dispatch(inv)

    content = Path(inv.invocation_path).read_text()
    assert "run-abc123" in content
    assert "product-engineer" in content
    assert "analyse" in content


def test_sequential_dispatch_result_carries_output_path(tmp_path: Path) -> None:
    """dispatch() must set output_path in the returned StageResult."""
    inv = _make_invocation(tmp_path)
    result = CodexAgentDispatcher().dispatch(inv)

    assert result.output_path is not None
    assert "analyse" in result.output_path


def test_sequential_dispatch_no_parallel_note_when_no_group(tmp_path: Path) -> None:
    """dispatch() without parallel_group must NOT mention parallel in the file."""
    inv = _make_invocation(tmp_path)
    CodexAgentDispatcher().dispatch(inv)

    content = Path(inv.invocation_path).read_text()
    assert "parallel" not in content.lower()


def test_sequential_dispatch_creates_parent_dirs(tmp_path: Path) -> None:
    """dispatch() must create missing parent directories."""
    inv = StageInvocation(
        run_id="r1",
        stage_id="s1",
        workflow_name="wf",
        agent="qa-engineer",
        inputs={},
        expected_output_path="out/s1.md",
        must_include=(),
        parallel_group=None,
        invocation_path=str(tmp_path / "deep" / "nested" / "inv.md"),
    )
    CodexAgentDispatcher().dispatch(inv)
    assert Path(inv.invocation_path).exists()
