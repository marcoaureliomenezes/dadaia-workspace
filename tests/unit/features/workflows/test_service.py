"""Unit tests for dadaia_workspace.features.workflows.service.

Coverage:
- list_summaries returns all workflows in dir
- summary DTO shape matches SPEC §5.3 (no stages[], no diagram_svg)
- detail DTO shape matches SPEC §5.4 (stages[], diagram_svg placeholder)
- get_detail returns None for unknown name
- per-process mtime cache: cache hit on second call
- cache invalidation on mtime change
- cache eviction on file deletion (None returned)
- StageDTO field mapping: needs, parallel_group, gate bool, expected_output_path,
  must_include, on_failure
"""

import os
import time
from pathlib import Path

import pytest

from dadaia_workspace.features.workflows.service import (
    StageDTO,
    WorkflowDetailDTO,
    WorkflowSummaryDTO,
    WorkflowsService,
    _cache,
)


# ---------------------------------------------------------------------------
# Fixtures — minimal .workflow.md files written to tmp_path
# ---------------------------------------------------------------------------

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


def _make_workflows_dir(tmp_path: Path) -> Path:
    wf_dir = tmp_path / ".dadaia" / "agentic" / "workflows"
    wf_dir.mkdir(parents=True)
    return wf_dir


# ---------------------------------------------------------------------------
# Tests: list_summaries
# ---------------------------------------------------------------------------


def test_list_returns_all_workflows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)
    (wf_dir / "parallel-wf.workflow.md").write_text(_PARALLEL_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    summaries = svc.list_summaries()

    names = {s.name for s in summaries}
    assert names == {"simple-wf", "parallel-wf"}


def test_list_returns_empty_when_no_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    # no workflows dir under tmp_path
    svc = WorkflowsService(workspace_root=tmp_path)
    assert svc.list_summaries() == []


def test_summary_shape_matches_spec(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    summaries = svc.list_summaries()
    assert len(summaries) == 1
    s = summaries[0]

    assert isinstance(s, WorkflowSummaryDTO)
    assert s.name == "simple-wf"
    assert s.display_name == "simple-wf"
    assert s.description == "A simple workflow for testing."
    assert s.version == "1.0.0"
    assert s.schema_version == "1"
    assert s.stage_count == 1
    assert s.agent_ids == ["software-engineer"]
    assert s.has_parallel is False
    assert s.has_gates is False
    assert s.source_path.endswith("simple-wf.workflow.md")

    # SPEC §5.3: no stages[] and no diagram_svg on summary
    assert not hasattr(s, "stages")
    assert not hasattr(s, "diagram_svg")


def test_summary_detects_parallel_and_gates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "parallel-wf.workflow.md").write_text(_PARALLEL_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    summaries = svc.list_summaries()
    p = summaries[0]

    assert p.has_parallel is True
    assert p.has_gates is True
    assert p.stage_count == 4


def test_summary_agent_ids_deduped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    # tdd-cycle has qa-engineer twice + implementer placeholder — use simple_wf
    two_stage = """\
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
    (wf_dir / "two-stage.workflow.md").write_text(two_stage)
    svc = WorkflowsService(workspace_root=tmp_path)
    s = svc.list_summaries()[0]
    assert s.agent_ids == ["software-engineer"]


# ---------------------------------------------------------------------------
# Tests: get_detail
# ---------------------------------------------------------------------------


def test_get_detail_returns_none_for_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    assert svc.get_detail("nonexistent-workflow") is None


def test_get_detail_returns_none_when_no_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    svc = WorkflowsService(workspace_root=tmp_path)
    assert svc.get_detail("simple-wf") is None


def test_detail_shape_matches_spec(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    detail = svc.get_detail("simple-wf")

    assert detail is not None
    assert isinstance(detail, WorkflowDetailDTO)
    assert detail.name == "simple-wf"
    assert detail.display_name == "simple-wf"
    assert detail.description == "A simple workflow for testing."
    assert detail.version == "1.0.0"
    assert detail.schema_version == "1"
    assert detail.stage_count == 1
    assert detail.agent_ids == ["software-engineer"]
    assert detail.has_parallel is False
    assert detail.has_gates is False
    assert detail.source_path.endswith("simple-wf.workflow.md")
    assert isinstance(detail.inputs, list)
    assert isinstance(detail.stages, list)
    assert isinstance(detail.diagram_svg, str)  # stub "" until PR3-13


def test_detail_stage_dto_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    detail = svc.get_detail("simple-wf")
    assert detail is not None
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


def test_detail_stage_gate_bool_true(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "parallel-wf.workflow.md").write_text(_PARALLEL_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    detail = svc.get_detail("parallel-wf")
    assert detail is not None

    review_stage = next(s for s in detail.stages if s.id == "review")
    assert review_stage.gate is True
    assert review_stage.parallel_group is None
    assert review_stage.needs == ["parallel_a", "parallel_b"]


def test_detail_parallel_stage_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "parallel-wf.workflow.md").write_text(_PARALLEL_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    detail = svc.get_detail("parallel-wf")
    assert detail is not None

    pa = next(s for s in detail.stages if s.id == "parallel_a")
    assert pa.parallel_group == "impl"
    assert pa.needs == ["start"]
    assert pa.gate is False


# ---------------------------------------------------------------------------
# Tests: DTO mapping — inputs list
# ---------------------------------------------------------------------------


def test_detail_inputs_mapped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    detail = svc.get_detail("simple-wf")
    assert detail is not None
    assert len(detail.inputs) == 1
    inp = detail.inputs[0]
    assert inp["name"] == "context"
    assert inp["type"] == "string"
    assert inp["required"] is True


# ---------------------------------------------------------------------------
# Tests: per-process in-memory cache
# ---------------------------------------------------------------------------


def test_cache_hit_on_second_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    wf_file = wf_dir / "simple-wf.workflow.md"
    wf_file.write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    detail_first = svc.get_detail("simple-wf")
    detail_second = svc.get_detail("simple-wf")

    assert detail_first is not None
    assert detail_second is detail_first  # same object from cache


def test_cache_invalidated_on_mtime_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    wf_file = wf_dir / "simple-wf.workflow.md"
    wf_file.write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    detail_first = svc.get_detail("simple-wf")
    assert detail_first is not None

    # Advance mtime by overwriting with a sleep or by explicitly setting mtime
    # Overwrite file content (same content) but bump mtime via os.utime
    current_mtime = wf_file.stat().st_mtime
    os.utime(wf_file, (current_mtime + 10.0, current_mtime + 10.0))

    detail_second = svc.get_detail("simple-wf")
    assert detail_second is not None
    # Different object — cache was invalidated and re-fetched
    assert detail_second is not detail_first


def test_cache_eviction_on_file_deletion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    wf_file = wf_dir / "simple-wf.workflow.md"
    wf_file.write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    assert svc.get_detail("simple-wf") is not None

    # Delete the file — subsequent lookup should return None
    wf_file.unlink()
    assert svc.get_detail("simple-wf") is None


def test_env_var_overrides_default_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _cache.clear()
    custom_dir = tmp_path / "custom_workflows"
    custom_dir.mkdir()
    (custom_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)
    monkeypatch.setenv("DADAIA_WORKFLOWS_DIR", str(custom_dir))

    svc = WorkflowsService(workspace_root=tmp_path)
    summaries = svc.list_summaries()
    assert any(s.name == "simple-wf" for s in summaries)


# ---------------------------------------------------------------------------
# Tests: .claude/workflows/ fallback branch (lines 43-46)
# ---------------------------------------------------------------------------


def test_claude_workflows_dir_used_when_agentic_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When .dadaia/agentic/workflows/ is absent, .claude/workflows/ is used."""
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    claude_dir = tmp_path / ".claude" / "workflows"
    claude_dir.mkdir(parents=True)
    (claude_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    summaries = svc.list_summaries()
    assert any(s.name == "simple-wf" for s in summaries)


def test_claude_workflows_dir_used_when_agentic_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When .dadaia/agentic/workflows/ exists but has no .workflow.md, fall through to .claude/."""
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    # Create empty agentic dir (no workflow files)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "workflows"
    agentic_dir.mkdir(parents=True)
    claude_dir = tmp_path / ".claude" / "workflows"
    claude_dir.mkdir(parents=True)
    (claude_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    summaries = svc.list_summaries()
    assert any(s.name == "simple-wf" for s in summaries)


def test_agentic_dir_preferred_over_claude(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When .dadaia/agentic/workflows/ has workflow files, .claude/ is NOT used."""
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    agentic_dir = _make_workflows_dir(tmp_path)
    (agentic_dir / "agentic-wf.workflow.md").write_text(
        _SIMPLE_WF.replace("simple-wf", "agentic-wf")
    )
    claude_dir = tmp_path / ".claude" / "workflows"
    claude_dir.mkdir(parents=True)
    (claude_dir / "claude-wf.workflow.md").write_text(_SIMPLE_WF.replace("simple-wf", "claude-wf"))

    svc = WorkflowsService(workspace_root=tmp_path)
    summaries = svc.list_summaries()
    names = {s.name for s in summaries}
    assert "agentic-wf" in names
    assert "claude-wf" not in names


# ---------------------------------------------------------------------------
# Tests: malformed workflow YAML raises WorkflowSchemaError (store contract)
# ---------------------------------------------------------------------------


def test_malformed_workflow_yaml_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A workflow file with malformed YAML frontmatter causes list_summaries to raise.

    The MarkdownWorkflowStore does not swallow parse errors — callers must handle them.
    This is intentional: a broken workflow file is a configuration error that should
    surface loudly rather than silently disappear.
    """
    from dadaia_workspace.core.exceptions import WorkflowSchemaError

    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "bad.workflow.md").write_text("---\n: invalid: yaml: [\n---\n# Bad\n")

    svc = WorkflowsService(workspace_root=tmp_path)
    with pytest.raises(WorkflowSchemaError):
        svc.list_summaries()


# ---------------------------------------------------------------------------
# Tests: empty workflow file raises WorkflowSchemaError
# ---------------------------------------------------------------------------


def test_empty_workflow_file_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An empty .workflow.md file (missing frontmatter) causes list_summaries to raise."""
    from dadaia_workspace.core.exceptions import WorkflowSchemaError

    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "empty.workflow.md").write_text("")

    svc = WorkflowsService(workspace_root=tmp_path)
    with pytest.raises(WorkflowSchemaError):
        svc.list_summaries()


# ---------------------------------------------------------------------------
# Tests: get_detail with .claude/workflows/ source
# ---------------------------------------------------------------------------


def test_get_detail_from_claude_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """get_detail works when the workflow comes from .claude/workflows/."""
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    claude_dir = tmp_path / ".claude" / "workflows"
    claude_dir.mkdir(parents=True)
    (claude_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    detail = svc.get_detail("simple-wf")
    assert detail is not None
    assert detail.name == "simple-wf"
