"""T-28-B-02 — ``*.workflow.md`` is demoted to reference/doc-only.

Wave B makes the Python ``dadaia_catalog`` the single governed source of executable
workflow behavior. The legacy Markdown ``*.workflow.md`` read path
(:meth:`WorkflowsService.get_detail` / :meth:`WorkflowsService.list_summaries`) is kept
for the legacy reference view but is **no longer the authority** for executable workflow
behavior. Docstring-declares-demotion prose assertions are deleted (the demotion is
tested behaviorally: the governed catalog resolves with no Markdown store present).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog
from dadaia_workspace.features.workflows.service import WorkflowsService, _cache
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


def _make_workflows_dir(tmp_path: Path) -> Path:
    wf_dir = tmp_path / ".dadaia" / "agentic" / "workflows"
    wf_dir.mkdir(parents=True)
    return wf_dir


def test_reference_read_path_functions_independent_of_governed_catalog(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The legacy Markdown reference view still works, and the governed catalog (the
    executable authority) resolves with no Markdown store present at all — proving the
    two are decoupled, i.e. the demotion holds behaviorally, not just in prose."""
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path, store_factory=MarkdownWorkflowStore)
    summaries = svc.list_summaries()
    assert [s.name for s in summaries] == ["simple-wf"]
    detail = svc.get_detail("simple-wf")
    assert detail is not None
    assert detail.name == "simple-wf"

    # No workflows dir on this fresh instance — Markdown read path is empty ...
    _cache.clear()
    empty_root = tmp_path.parent / (tmp_path.name + "-empty")
    empty_svc = WorkflowsService(workspace_root=empty_root, store_factory=MarkdownWorkflowStore)
    assert empty_svc.list_summaries() == []
    assert empty_svc.get_detail("simple-wf") is None

    # ... yet the governed catalog is unaffected — it is the executable authority.
    governed = empty_svc.list_dadaia_workflows()
    assert {w.name for w in governed} >= {
        "release_definition",
        "implementation",
        "backlog_definition",
    }
    impl = empty_svc.get_dadaia_workflow("implementation")
    assert impl is not None
    assert impl.steps


def test_governed_catalog_is_the_resolver_source() -> None:
    """The resolver reads the governed catalog, not the Markdown reference store."""
    catalog = governed_workflow_catalog()
    assert catalog.workflow("implementation") is not None
