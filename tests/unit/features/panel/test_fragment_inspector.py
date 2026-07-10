"""Unit tests for the Wave D read-only fragment inspector (T-28-D-01).

The inspector resolves each governed model step's fragment ids to their resolved body
(via :class:`FragmentLoader`), dynamic-context selectors, and output schema, served
read-only through ``GET /api/workflow-fragments/<fragment_id>``. The view never edits a
fragment (editing fragments is source-controlled release work, SPEC §6 UX principle).

Two survivors:
  1. Real fragment resolves body+metadata AND every governed step fragment
     resolves through the view.
  2. 404 unknown (no traceback) + 400 malformed-id param (A03).
"""

from __future__ import annotations

import json

import pytest

from dadaia_workspace.features.lifecycle.fragments.loader import FragmentLoader
from dadaia_workspace.features.panel.views.workflow_policy import render_api_workflow_fragment
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog

pytestmark = pytest.mark.unit


def _loader() -> FragmentLoader:
    return FragmentLoader()


# ---------------------------------------------------------------------------
# 1. Real fragment resolves body+metadata + every governed step fragment resolves
# ---------------------------------------------------------------------------


def test_fragment_resolves_body_metadata_and_every_governed_step_fragment() -> None:
    view = render_api_workflow_fragment(_loader())

    status, content_type, body = view(fragment_id="implementation.implement_tdd")
    assert status == 200
    assert "application/json" in content_type
    payload = json.loads(body)
    assert payload["id"] == "implementation.implement_tdd"
    assert "Implement (TDD)" in payload["body"]
    assert "task_group" in payload["dynamic_inputs"]
    assert payload["output_schema"] == "implementation-result-v1"
    assert "static_inputs" in payload
    assert payload["role"]
    assert payload["workflow"]
    assert payload["step"]

    # Every fragment id the governed catalog references resolves via the
    # inspector view (each model step's fragment ids are resolvable to body +
    # metadata). A step with no fragments is skipped — nothing to inspect.
    catalog = governed_workflow_catalog()
    seen = 0
    for workflow in catalog.workflows:
        for step in workflow.steps:
            for fragment_id in step.fragments:
                fstatus, _fct, fbody = view(fragment_id=fragment_id)
                assert fstatus == 200, f"{workflow.workflow_id}.{step.label}:{fragment_id}"
                fpayload = json.loads(fbody)
                assert fpayload["id"] == fragment_id
                seen += 1
    assert seen > 0


# ---------------------------------------------------------------------------
# 2. 404 unknown (no traceback) + 400 malformed-id param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fragment_id", "expected_status", "expected_error"),
    [
        pytest.param("implementation.does_not_exist", 404, "not_found", id="unknown-id-404"),
        pytest.param("../secret", 400, "invalid_fragment_id", id="traversal-attempt"),
        pytest.param("a/b", 400, "invalid_fragment_id", id="slash-not-allowed"),
        pytest.param("a b", 400, "invalid_fragment_id", id="space-not-allowed"),
        pytest.param("", 400, "invalid_fragment_id", id="empty-id"),
        pytest.param("x" * 200, 400, "invalid_fragment_id", id="oversized-id"),
    ],
)
def test_unknown_and_malformed_ids(
    fragment_id: str, expected_status: int, expected_error: str
) -> None:
    view = render_api_workflow_fragment(_loader())
    status, _content_type, body = view(fragment_id=fragment_id)
    assert status == expected_status
    payload = json.loads(body)
    assert payload["error"] == expected_error
    if expected_status == 404:
        # Never echoes a stack trace / internal path detail to the client (A06).
        assert "Traceback" not in payload["message"]
