"""T-28-B-02 — ``*.workflow.md`` is demoted to reference/doc-only.

Wave B makes the Python ``dadaia_catalog`` the single governed source of executable
workflow behavior. The legacy Markdown ``*.workflow.md`` read path
(:meth:`WorkflowsService.get_detail` / :meth:`WorkflowsService.list_summaries`) is kept
for the legacy reference view but is **no longer the authority** for executable workflow
behavior. These tests pin that contract:

1. The reference-only methods still function (legacy view keeps working).
2. The methods' docstrings declare the reference-only / non-authoritative status, so the
   demotion is documented at the API surface (AC-15).
3. The governed catalog accessors (``list_dadaia_workflows`` / ``get_dadaia_workflow``)
   are the authoritative source and are independent of the Markdown store.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from dadaia_workspace.features.workflows.service import WorkflowsService, _cache

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


# ---------------------------------------------------------------------------
# 1. The legacy reference read path still functions.
# ---------------------------------------------------------------------------


def test_reference_read_path_still_functions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    wf_dir = _make_workflows_dir(tmp_path)
    (wf_dir / "simple-wf.workflow.md").write_text(_SIMPLE_WF)

    svc = WorkflowsService(workspace_root=tmp_path)
    summaries = svc.list_summaries()
    assert [s.name for s in summaries] == ["simple-wf"]
    detail = svc.get_detail("simple-wf")
    assert detail is not None
    assert detail.name == "simple-wf"


# ---------------------------------------------------------------------------
# 2. The demotion is documented at the API surface (AC-15).
# ---------------------------------------------------------------------------


def _doc(method: object) -> str:
    return (inspect.getdoc(method) or "").lower()


def test_get_detail_docstring_declares_reference_only() -> None:
    doc = _doc(WorkflowsService.get_detail)
    assert "reference" in doc
    assert "authority" in doc or "authoritative" in doc


def test_list_summaries_docstring_declares_reference_only() -> None:
    doc = _doc(WorkflowsService.list_summaries)
    assert "reference" in doc
    assert "authority" in doc or "authoritative" in doc


def test_service_class_docstring_documents_demotion() -> None:
    doc = _doc(WorkflowsService)
    assert "reference" in doc
    assert ".workflow.md" in doc


# ---------------------------------------------------------------------------
# 3. The governed catalog is the executable authority, independent of Markdown.
# ---------------------------------------------------------------------------


def test_governed_catalog_authority_needs_no_markdown_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The Python catalog resolves with no ``*.workflow.md`` files present at all."""
    _cache.clear()
    monkeypatch.delenv("DADAIA_WORKFLOWS_DIR", raising=False)
    # No workflows dir created — the Markdown read path returns empty.
    svc = WorkflowsService(workspace_root=tmp_path)
    assert svc.list_summaries() == []
    assert svc.get_detail("simple-wf") is None

    # The governed catalog is unaffected — it is the executable authority.
    governed = svc.list_dadaia_workflows()
    assert {w.name for w in governed} >= {
        "release_definition",
        "implementation",
        "backlog_definition",
    }
    impl = svc.get_dadaia_workflow("implementation")
    assert impl is not None
    assert impl.steps


def test_governed_catalog_is_the_resolver_source() -> None:
    """The resolver reads the governed catalog, not the Markdown reference store."""
    from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog

    catalog = governed_workflow_catalog()
    assert catalog.workflow("implementation") is not None
