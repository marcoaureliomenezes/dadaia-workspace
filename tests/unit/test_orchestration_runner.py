"""Unit tests for runner.py and resolver.py helper functions."""

import pytest

from dadaia_workspace.core.exceptions import WorkflowSchemaError
from dadaia_workspace.core.models.run_state import (
    RunManifest,
    RunStatus,
    StageState,
    StageStatus,
)
from dadaia_workspace.core.models.workflow import (
    StageExpectedOutput,
    StageInputBinding,
    WorkflowDefinition,
    WorkflowInput,
    WorkflowStage,
)
from dadaia_workspace.features.orchestration.resolver import (
    render_output_path,
    resolve_stage_inputs,
)
from dadaia_workspace.features.orchestration.runner import (
    group_ready,
    next_ready_stages,
    stage_by_id,
    topo_order,
    update_stage_state,
)

# ──────────────────────────── helpers ────────────────────────────


def _stage(
    id: str,
    needs: tuple[str, ...] = (),
    parallel_group: str | None = None,
    inputs: tuple[StageInputBinding, ...] = (),
) -> WorkflowStage:
    return WorkflowStage(
        id=id,
        agent="product-engineer",
        expected_output=StageExpectedOutput(path=f"out/{id}.md"),
        needs=needs,
        parallel_group=parallel_group,
        inputs=inputs,
    )


def _workflow(*stages: WorkflowStage, inputs: tuple[WorkflowInput, ...] = ()) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="test-wf",
        description="test",
        version="0.1",
        schema_version="1",
        inputs=inputs,
        stages=stages,
    )


def _manifest(
    *stages: StageState,
    inputs: dict[str, str] | None = None,
) -> RunManifest:
    return RunManifest(
        run_id="run-001",
        workflow_name="test-wf",
        workflow_version="0.1",
        context="myctx",
        runtime="claude",
        status=RunStatus.RUNNING,
        started_at="2026-01-01T00:00:00Z",
        finished_at=None,
        stages=stages,
        inputs=inputs or {},
    )


def _stage_state(id: str, status: StageStatus, output_path: str | None = None) -> StageState:
    return StageState(id=id, agent="product-engineer", status=status, output_path=output_path)


# ──────────────────────────── topo_order ────────────────────────────


def test_topo_order_linear_dependency() -> None:
    s1 = _stage("s1")
    s2 = _stage("s2", needs=("s1",))
    s3 = _stage("s3", needs=("s2",))
    wf = _workflow(s1, s2, s3)
    order = topo_order(wf)
    assert order == ("s1", "s2", "s3")


def test_topo_order_parallel_stages() -> None:
    s1 = _stage("s1")
    s2 = _stage("s2")
    s3 = _stage("s3", needs=("s1", "s2"))
    wf = _workflow(s1, s2, s3)
    order = topo_order(wf)
    assert "s1" in order
    assert "s2" in order
    # s3 must come after both s1 and s2
    assert order.index("s3") > order.index("s1")
    assert order.index("s3") > order.index("s2")


def test_topo_order_single_stage() -> None:
    s = _stage("only")
    assert topo_order(_workflow(s)) == ("only",)


# ──────────────────────────── stage_by_id ────────────────────────────


def test_stage_by_id_finds_existing() -> None:
    s1 = _stage("alpha")
    s2 = _stage("beta")
    wf = _workflow(s1, s2)
    assert stage_by_id(wf, "beta") is s2


def test_stage_by_id_raises_on_missing() -> None:
    wf = _workflow(_stage("only"))
    with pytest.raises(KeyError):
        stage_by_id(wf, "ghost")


# ──────────────────────────── next_ready_stages ────────────────────────────


def test_next_ready_stages_returns_stages_with_no_pending_deps() -> None:
    s1 = _stage("s1")
    s2 = _stage("s2", needs=("s1",))
    wf = _workflow(s1, s2)
    manifest = _manifest(
        _stage_state("s1", StageStatus.COMPLETED),
        _stage_state("s2", StageStatus.PENDING),
    )
    ready = next_ready_stages(wf, manifest)
    assert len(ready) == 1
    assert ready[0].id == "s2"


def test_next_ready_stages_excludes_blocked_stages() -> None:
    s1 = _stage("s1")
    s2 = _stage("s2", needs=("s1",))
    wf = _workflow(s1, s2)
    manifest = _manifest(
        _stage_state("s1", StageStatus.PENDING),
        _stage_state("s2", StageStatus.PENDING),
    )
    ready = next_ready_stages(wf, manifest)
    assert len(ready) == 1
    assert ready[0].id == "s1"


# ──────────────────────────── group_ready ────────────────────────────


def test_group_ready_groups_parallel_stages() -> None:
    s1 = _stage("s1", parallel_group="pg1")
    s2 = _stage("s2", parallel_group="pg1")
    s3 = _stage("s3")
    groups = group_ready((s1, s2, s3))
    assert len(groups) == 2
    singleton = next(g for g in groups if len(g) == 1)
    parallel = next(g for g in groups if len(g) == 2)
    assert singleton[0].id == "s3"
    assert {s.id for s in parallel} == {"s1", "s2"}


def test_group_ready_all_singletons() -> None:
    s1 = _stage("s1")
    s2 = _stage("s2")
    groups = group_ready((s1, s2))
    assert all(len(g) == 1 for g in groups)
    assert len(groups) == 2


# ──────────────────────────── update_stage_state ────────────────────────────


def test_update_stage_state_changes_status() -> None:
    manifest = _manifest(
        _stage_state("s1", StageStatus.PENDING),
        _stage_state("s2", StageStatus.PENDING),
    )
    updated = update_stage_state(manifest, "s1", status=StageStatus.RUNNING)
    s1 = next(s for s in updated.stages if s.id == "s1")
    s2 = next(s for s in updated.stages if s.id == "s2")
    assert s1.status == StageStatus.RUNNING
    assert s2.status == StageStatus.PENDING


# ──────────────────────────── resolver ────────────────────────────


def test_resolve_workflow_input_binding() -> None:
    stage = _stage(
        "s1",
        inputs=(
            StageInputBinding(kind="workflow_input", from_ref="$.inputs.context", as_name="ctx"),
        ),
    )
    wf = _workflow(stage, inputs=(WorkflowInput(name="context", type="string"),))
    manifest = _manifest(inputs={"context": "myproject"})
    result = resolve_stage_inputs(wf, manifest, stage)
    assert result["ctx"] == "myproject"


def test_resolve_workflow_input_with_default() -> None:
    stage = _stage(
        "s1",
        inputs=(
            StageInputBinding(kind="workflow_input", from_ref="$.inputs.mode", as_name="mode"),
        ),
    )
    wf = _workflow(stage, inputs=(WorkflowInput(name="mode", type="string", default="prod"),))
    manifest = _manifest(inputs={})  # mode not provided → use default
    result = resolve_stage_inputs(wf, manifest, stage)
    assert result["mode"] == "prod"


def test_resolve_stage_output_binding() -> None:
    stage = _stage(
        "s2",
        inputs=(
            StageInputBinding(kind="stage_output", from_ref="stages.s1.output", as_name="prev_out"),
        ),
    )
    wf = _workflow(_stage("s1"), stage)
    manifest = _manifest(
        _stage_state("s1", StageStatus.COMPLETED, output_path="out/s1.md"),
        _stage_state("s2", StageStatus.PENDING),
    )
    result = resolve_stage_inputs(wf, manifest, stage)
    assert result["prev_out"] == "out/s1.md"


def test_resolve_path_binding() -> None:
    stage = _stage(
        "s1", inputs=(StageInputBinding(kind="path", from_ref="/some/path.md", as_name="doc"),)
    )
    wf = _workflow(stage)
    manifest = _manifest()
    result = resolve_stage_inputs(wf, manifest, stage)
    assert result["doc"] == "/some/path.md"


def test_resolve_literal_binding() -> None:
    stage = _stage(
        "s1", inputs=(StageInputBinding(kind="literal", from_ref="hello world", as_name="msg"),)
    )
    wf = _workflow(stage)
    manifest = _manifest()
    result = resolve_stage_inputs(wf, manifest, stage)
    assert result["msg"] == "hello world"


def test_resolve_raises_on_missing_workflow_input() -> None:
    stage = _stage(
        "s1",
        inputs=(
            StageInputBinding(kind="workflow_input", from_ref="$.inputs.missing", as_name="x"),
        ),
    )
    wf = _workflow(stage)
    manifest = _manifest(inputs={})
    with pytest.raises(WorkflowSchemaError, match="missing"):
        resolve_stage_inputs(wf, manifest, stage)


def test_resolve_raises_on_missing_stage_output() -> None:
    stage = _stage(
        "s2",
        inputs=(
            StageInputBinding(kind="stage_output", from_ref="stages.s1.output", as_name="out"),
        ),
    )
    wf = _workflow(_stage("s1"), stage)
    manifest = _manifest(
        _stage_state("s1", StageStatus.PENDING, output_path=None),  # no output yet
        _stage_state("s2", StageStatus.PENDING),
    )
    with pytest.raises(WorkflowSchemaError, match="s1"):
        resolve_stage_inputs(wf, manifest, stage)


def test_resolve_raises_on_unknown_binding_kind() -> None:
    stage = _stage(
        "s1", inputs=(StageInputBinding(kind="unknown_kind", from_ref="x", as_name="y"),)
    )
    wf = _workflow(stage)
    manifest = _manifest()
    with pytest.raises(WorkflowSchemaError, match="unknown_kind"):
        resolve_stage_inputs(wf, manifest, stage)


def test_render_output_path_substitutes_variables() -> None:
    template = "out/{run_id}/{context}/{run_ts}/report.md"
    result = render_output_path(template, run_id="r1", context="myctx", run_ts="2026-01-01")
    assert result == "out/r1/myctx/2026-01-01/report.md"
