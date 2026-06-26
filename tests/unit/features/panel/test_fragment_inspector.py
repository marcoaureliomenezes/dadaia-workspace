"""Unit tests for the Wave D read-only fragment inspector (T-28-D-01).

The inspector resolves each governed model step's fragment ids to their resolved body
(via :class:`FragmentLoader`), dynamic-context selectors, and output schema, served
read-only through ``GET /api/workflow-fragments/<fragment_id>``. The view never edits a
fragment (editing fragments is source-controlled release work, SPEC §6 UX principle).
"""

from __future__ import annotations

import json

from dadaia_workspace.features.lifecycle.fragments.loader import FragmentLoader
from dadaia_workspace.features.panel.views.workflow_policy import (
    render_api_workflow_fragment,
)
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog


def _loader() -> FragmentLoader:
    return FragmentLoader()


def test_fragment_view_resolves_real_fragment_body_and_metadata() -> None:
    view = render_api_workflow_fragment(_loader())
    status, content_type, body = view(fragment_id="implementation.implement_tdd")
    assert status == 200
    assert "application/json" in content_type
    payload = json.loads(body)
    assert payload["id"] == "implementation.implement_tdd"
    # Resolved body comes from the real fragment library (read-only).
    assert "Implement (TDD)" in payload["body"]
    # Dynamic-context selectors + output schema are surfaced for the inspector.
    assert "task_group" in payload["dynamic_inputs"]
    assert payload["output_schema"] == "implementation-result-v1"
    assert "static_inputs" in payload
    assert payload["role"]
    assert payload["workflow"]
    assert payload["step"]


def test_fragment_view_unknown_id_is_404_not_crash() -> None:
    view = render_api_workflow_fragment(_loader())
    status, _content_type, body = view(fragment_id="implementation.does_not_exist")
    assert status == 404
    payload = json.loads(body)
    assert payload["error"] == "not_found"
    # Never echoes a stack trace / internal path detail to the client (A06).
    assert "Traceback" not in payload["message"]


def test_fragment_view_rejects_malformed_id() -> None:
    view = render_api_workflow_fragment(_loader())
    # Path-traversal-ish / non-identifier ids are rejected before any disk read (A03).
    for bad in ("../secret", "a/b", "a b", "", "x" * 200):
        status, _content_type, body = view(fragment_id=bad)
        assert status == 400, bad
        payload = json.loads(body)
        assert payload["error"] == "invalid_fragment_id"


def test_every_governed_step_fragment_resolves_through_the_view() -> None:
    """Every fragment id the governed catalog references resolves via the inspector view.

    This is the read-only inspector's contract: each model step's fragment ids are
    resolvable to body + metadata. A step with no fragments (generic suffix step) is
    skipped — there is nothing to inspect.
    """
    view = render_api_workflow_fragment(_loader())
    catalog = governed_workflow_catalog()
    seen = 0
    for workflow in catalog.workflows:
        for step in workflow.steps:
            for fragment_id in step.fragments:
                status, _content_type, body = view(fragment_id=fragment_id)
                assert status == 200, f"{workflow.workflow_id}.{step.label}:{fragment_id}"
                payload = json.loads(body)
                assert payload["id"] == fragment_id
                seen += 1
    assert seen > 0
