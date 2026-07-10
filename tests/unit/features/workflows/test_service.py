"""Unit tests for dadaia_workspace.features.workflows.service.

Coverage:
- Directory resolution precedence (env > .dadaia/agentic/workflows > .claude/workflows).
- Summary + detail DTO shape (SPEC §5.3/§5.4), stage/parallel/gate detection, agent
  dedup, inputs mapping.
- Per-process mtime cache: hit / invalidation on mtime change / eviction on delete.
- Error paths: unknown name / no dir -> None; malformed/empty YAML -> WorkflowSchemaError.
"""

import os
from pathlib import Path

import pytest

from dadaia_workspace.features.workflows.service import (
    StageDTO,
    WorkflowDetailDTO,
    WorkflowsService,
    WorkflowSummaryDTO,
    _cache,
)
from dadaia_workspace.infrastructure.markdown_workflow_store import MarkdownWorkflowStore

_SIMPLE_WF = """\
---
name: simple-wf
description: A simple workflow for testing.
version: 1.0.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
stages:
  - id: do_work
    agent: software-engineer
    expected_output:
      path: ".dadaia/reports/{context}/software-engineer/{run_ts}-done.html"
      must_include:
        - "Task done"
---

# simple-wf
"""

_PARALLEL_WF = """\
---
name: parallel-wf
description: A workflow with parallel stages.
version: 0.2.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
stages:
  - id: start
    agent: product-engineer
    expected_output:
      path: ".dadaia/reports/{context}/product-engineer/{run_ts}-start.html"

  - id: parallel_a
    agent: software-engineer
    needs: [start]
    parallel_group: impl
    expected_output:
      path: ".dadaia/reports/{context}/software-engineer/{run_ts}-impl-a.html"

  - id: parallel_b
    agent: frontend-engineer
    needs: [start]
    parallel_group: impl
    expected_output:
      path: ".dadaia/reports/{context}/frontend-engineer/{run_ts}-impl-b.html"

  - id: review
    agent: qa-engineer
    needs: [parallel_a, parallel_b]
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-review.html"
    gate:
      kind: operator-approval
      prompt: "Approve?"
---

# parallel-wf
"""

_TWO_STAGE_WF = """\
---
name: two-stage
description: Two stages same agent.
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
stages:
  - id: step_a
    agent: software-engineer
    expected_output:
      path: ".dadaia/reports/{context}/software-engineer/{run_ts}-a.html"
  - id: step_b
    agent: software-engineer
    needs: [step_a]
    expected_output:
      path: ".dadaia/reports/{context}/software-engineer/{run_ts}-b.html"
---
# two-stage
"""


def _make_workflows_dir(tmp_path: Path) -> Path:
    wf_dir = tmp_path / ".dadaia" / "agentic" / "workflows"
    wf_dir.mkdir(parents=True)
    return wf_dir


# ---------------------------------------------------------------------------
# Directory resolution precedence — 1 param
# ---------------------------------------------------------------------------


def _write_agentic_preferred_over_claude(tmp_path: Path) -> None:
    agentic_dir = _make_workflows_dir(tmp_path)
    (agentic_dir / "agentic-wf.workflow.md").write_text(
        _SIMPLE_WF.replace("simple-wf", "agentic-wf")
    )
    claude_dir = tmp_path / ".claude" / "workflows"
    claude_dir.mkdir(parents=True)
    (claude_dir / "claude-wf.workflow.md").write_text(_SIMPLE_WF.replace("simple-wf", "claude-wf"))


@pytest.mark.parametrize(
    ("case", "setup", "expect_present", "expect_absent"),
    [
        pytest.param(
            "env-var-overrides-default",
            lambda tp, mp: (
                mp.setenv("DADAIA_WORKFLOWS_DIR", str(_write_custom_env_dir(tp))),
            ),
            "simple-wf",
            None,
            id="env-var-overrides-default-dir",
        ),
        pytest.param(
            "claude-used-when-agentic-missing",
            lambda tp, mp: _write_claude_only(tp),
            "simple-wf",
            None,
            id="claude-used-when-agentic-missing",
        ),
        pytest.param(
            "claude-used-when-agentic-empty",
            lambda tp, mp: _write_claude_with_empty_agentic(tp),
            "simple-wf",
            None,
            id="claude-used-when-agentic-empty",
        ),
        pytest.param(
            "agentic-preferred-over-claude",
            lambda tp, mp: _write_agentic_preferred_over_claude(tp),
            "agentic-wf",
            "claude-wf",
            id="agentic-dir-preferred-over-claude",
        ),
    ],
)
def test_dir_resolution_precedence_matrix(  # type: ignore[no-untyped-def]
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    setup,
    expect_present: str,
    expect_absent: str | None,
) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    setup(tmp_path, monkeypatch)

    svc = WorkflowsService(workspace_root=tmp_path, store_factory=MarkdownWorkflowStore)
    summaries = svc.list_summaries()
    names = {s.name for s in summaries}
    assert expect_present in names
    if expect_absent is not None:
        assert expect_absent not in names


def _write_custom_env_dir(tmp_path: Path) -> Path:
    custom_dir = tmp_path / "custom_workflows"
    custom_dir.mkdir()
    (custom_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)
    return custom_dir


def _write_claude_only(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude" / "workflows"
    claude_dir.mkdir(parents=True)
    (claude_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)


def _write_claude_with_empty_agentic(tmp_path: Path) -> None:
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "workflows"
    agentic_dir.mkdir(parents=True)
    claude_dir = tmp_path / ".claude" / "workflows"
    claude_dir.mkdir(parents=True)
    (claude_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)


# ---------------------------------------------------------------------------
# Summary + detail DTO facets — 1 test
# ---------------------------------------------------------------------------


def test_summary_and_detail_dto_facets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)
    (wf_dir / "parallel-wf.workflow.md").write_text(_PARALLEL_WF)
    (wf_dir / "two-stage.workflow.md").write_text(_TWO_STAGE_WF)

    svc = WorkflowsService(workspace_root=tmp_path, store_factory=MarkdownWorkflowStore)
    summaries = svc.list_summaries()
    names = {s.name for s in summaries}
    assert names == {"simple-wf", "parallel-wf", "two-stage"}

    simple = next(s for s in summaries if s.name == "simple-wf")
    assert isinstance(simple, WorkflowSummaryDTO)
    assert simple.display_name == "simple-wf"
    assert simple.description == "A simple workflow for testing."
    assert simple.version == "1.0.0"
    assert simple.schema_version == "1"
    assert simple.stage_count == 1
    assert simple.agent_ids == ["software-engineer"]
    assert simple.has_parallel is False
    assert simple.has_gates is False
    assert simple.source_path.endswith("simple-wf.workflow.md")
    # SPEC §5.3: no stages[] and no diagram_svg on summary.
    assert not hasattr(simple, "stages")
    assert not hasattr(simple, "diagram_svg")

    parallel = next(s for s in summaries if s.name == "parallel-wf")
    assert parallel.has_parallel is True
    assert parallel.has_gates is True
    assert parallel.stage_count == 4

    two_stage = next(s for s in summaries if s.name == "two-stage")
    assert two_stage.agent_ids == ["software-engineer"]  # deduped

    # detail: unknown name -> None; no dir -> None.
    assert svc.get_detail("nonexistent-workflow") is None
    bare_svc = WorkflowsService(
        workspace_root=tmp_path.parent / (tmp_path.name + "-bare"), store_factory=MarkdownWorkflowStore
    )
    assert bare_svc.get_detail("simple-wf") is None

    detail = svc.get_detail("simple-wf")
    assert detail is not None
    assert isinstance(detail, WorkflowDetailDTO)
    assert detail.stage_count == 1
    assert isinstance(detail.inputs, list)
    assert isinstance(detail.stages, list)
    assert isinstance(detail.diagram_svg, str)

    # inputs mapping.
    assert len(detail.inputs) == 1
    inp = detail.inputs[0]
    assert inp["name"] == "context"
    assert inp["type"] == "string"
    assert inp["required"] is True

    # StageDTO field mapping.
    stage = detail.stages[0]
    assert isinstance(stage, StageDTO)
    assert stage.id == "do_work"
    assert stage.agent == "software-engineer"
    assert stage.needs == []
    assert stage.parallel_group is None
    assert stage.gate is False
    assert stage.expected_output_path is not None
    assert "software-engineer" in stage.expected_output_path
    assert stage.must_include == ["Task done"]
    assert stage.on_failure == "stop"

    # gate bool True + parallel fields on the parallel workflow's stages.
    parallel_detail = svc.get_detail("parallel-wf")
    assert parallel_detail is not None
    review_stage = next(s for s in parallel_detail.stages if s.id == "review")
    assert review_stage.gate is True
    assert review_stage.parallel_group is None
    assert review_stage.needs == ["parallel_a", "parallel_b"]
    pa = next(s for s in parallel_detail.stages if s.id == "parallel_a")
    assert pa.parallel_group == "impl"
    assert pa.needs == ["start"]
    assert pa.gate is False

    # get_detail works when the workflow comes from .claude/workflows/.
    claude_ws = tmp_path.parent / (tmp_path.name + "-claude-only")
    claude_dir = claude_ws / ".claude" / "workflows"
    claude_dir.mkdir(parents=True)
    (claude_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)
    claude_svc = WorkflowsService(workspace_root=claude_ws, store_factory=MarkdownWorkflowStore)
    claude_detail = claude_svc.get_detail("simple-wf")
    assert claude_detail is not None
    assert claude_detail.name == "simple-wf"


# ---------------------------------------------------------------------------
# Per-process mtime cache: hit / invalidation / eviction — 1 test
# ---------------------------------------------------------------------------


def test_cache_hit_invalidation_and_eviction(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    wf_file = wf_dir / "simple-wf.workflow.md"
    wf_file.write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path, store_factory=MarkdownWorkflowStore)
    detail_first = svc.get_detail("simple-wf")
    detail_second = svc.get_detail("simple-wf")
    assert detail_first is not None
    assert detail_second is detail_first  # cache hit — same object

    current_mtime = wf_file.stat().st_mtime
    os.utime(wf_file, (current_mtime + 10.0, current_mtime + 10.0))
    detail_third = svc.get_detail("simple-wf")
    assert detail_third is not None
    assert detail_third is not detail_first  # invalidated on mtime change

    wf_file.unlink()
    assert svc.get_detail("simple-wf") is None  # evicted on file deletion


# ---------------------------------------------------------------------------
# Error paths: malformed/empty YAML -> WorkflowSchemaError — 1 test
# ---------------------------------------------------------------------------


def test_malformed_and_empty_workflow_yaml_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The MarkdownWorkflowStore does not swallow parse errors — callers must handle
    them. A broken/empty workflow file is a configuration error that surfaces loudly
    rather than silently disappearing."""
    from dadaia_workspace.core.exceptions import WorkflowSchemaError

    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)

    malformed_dir = _make_workflows_dir(tmp_path)
    (malformed_dir / "bad.workflow.md").write_text("---\n: invalid: yaml: [\n---\n# Bad\n")
    svc_malformed = WorkflowsService(workspace_root=tmp_path, store_factory=MarkdownWorkflowStore)
    with pytest.raises(WorkflowSchemaError):
        svc_malformed.list_summaries()

    empty_root = tmp_path.parent / (tmp_path.name + "-empty")
    empty_dir = _make_workflows_dir(empty_root)
    (empty_dir / "empty.workflow.md").write_text("")
    svc_empty = WorkflowsService(workspace_root=empty_root, store_factory=MarkdownWorkflowStore)
    with pytest.raises(WorkflowSchemaError):
        svc_empty.list_summaries()
