"""Integration tests for GET /api/workflows and GET /api/workflows/<name>.

Coverage (merged per plan-integration.md, 14 -> 2 + 1 kept):
  1. list shape + source_hint + lean-item (no stages[]/diagram_svg)
  2. detail shape + stages + 404/400/traversal table
  3. cache-invalidation-on-mtime (kept: unique own tmp workspace)

Uses real workflow files from .dadaia/agentic/workflows/ — no mocks. Bearer
fns deleted (no-auth contract pinned in tests/unit/features/panel/test_no_auth_contract.py).
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api_workflows import (
    render_api_workflow_detail,
    render_api_workflows_list,
)
from dadaia_workspace.features.workflows.service import WorkflowsService
from dadaia_workspace.infrastructure.markdown_workflow_store import MarkdownWorkflowStore
from tests.integration.panel.conftest import BASE_STUB_VIEWS, get


class _StubRegistry:
    def list_entries(self, include_stale: bool = True) -> list:
        return []


class _StubSpecContextService:
    def list_all(self) -> list:
        return []


class _StubTelemetry:
    is_degraded: bool = False


@pytest.fixture(scope="module")
def workflows_server(panel_server_factory, staged_root: Path) -> str:
    workflows_service = WorkflowsService(staged_root, store_factory=MarkdownWorkflowStore)
    panel_service = PanelService(
        registry=_StubRegistry(),  # type: ignore[arg-type]
        spec_context=_StubSpecContextService(),  # type: ignore[arg-type]
        workspace_root=staged_root,
        telemetry=_StubTelemetry(),
        workflows_service=workflows_service,
    )
    return panel_server_factory(
        {
            "api_workflows": render_api_workflows_list(panel_service),
            "api_workflow_detail": render_api_workflow_detail(workflows_service),
        }
    )


class TestWorkflowsListShape:
    def test_top_level_keys_source_hint_and_lean_items(self, workflows_server: str) -> None:
        status, _, body = get(f"{workflows_server}/api/workflows")
        assert status == 200
        data = json.loads(body)
        for key in ("generated_at", "source_hint", "workflows"):
            assert key in data, f"missing key: {key}"
        assert data["source_hint"] == ".dadaia/agentic/workflows/"

        names = {w["name"] for w in data["workflows"]}
        assert "audit-fanout" in names

        item = next(w for w in data["workflows"] if w["name"] == "audit-fanout")
        for key in (
            "name",
            "display_name",
            "description",
            "version",
            "schema_version",
            "stage_count",
            "agent_ids",
            "has_parallel",
            "has_gates",
            "source_path",
        ):
            assert key in item, f"missing workflow item key: {key}"
        assert "stages" not in item
        assert "diagram_svg" not in item


class TestWorkflowDetailShapeAndErrors:
    def test_detail_shape_stages_and_error_table(self, workflows_server: str) -> None:
        status, _, body = get(f"{workflows_server}/api/workflows/audit-fanout")
        assert status == 200
        data = json.loads(body)
        for key in ("name", "stages", "diagram_svg", "inputs", "agent_ids"):
            assert key in data, f"missing detail key: {key}"
        for stage in data["stages"]:
            for key in ("id", "agent", "needs", "gate", "on_failure"):
                assert key in stage, f"stage missing key: {key}"

        status, _, _ = get(f"{workflows_server}/api/workflows/nonexistent-workflow")
        assert status == 404

        status, _, body = get(f"{workflows_server}/api/workflows/bad..name")
        assert status == 400
        data = json.loads(body)
        assert data.get("error") == "invalid_workflow_name"

        status, _, _ = get(f"{workflows_server}/api/workflows/..%2Fetc%2Fpasswd")
        assert status in (400, 404)


class TestWorkflowCacheInvalidation:
    """Verify that editing a workflow file and touching its mtime produces updated data.

    Own tmp workspace + own server (unique fixture) — kept per plan (not folded into
    the package factory, since it needs to mutate the underlying workflow file).
    """

    _WORKFLOW_TEMPLATE = """\
---
name: cache-test-workflow
description: {description}
version: 0.1.0
schema_version: "1"
stages:
  - id: step-one
    agent: software-engineer
    needs: []
    on_failure: stop
    expected_output:
      path: ".dadaia/reports/cache-test-workflow/step-one.html"
---
"""

    def _setup_temp_workspace(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="dw-integ-cache-"))
        wf_dir = tmp / ".dadaia" / "agentic" / "workflows"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "cache-test-workflow.workflow.md"
        wf_file.write_text(
            self._WORKFLOW_TEMPLATE.format(description="version-one"), encoding="utf-8"
        )
        return tmp

    def _build_server(self, token: str, workspace_root: Path) -> ThreadingHTTPServer:
        workflows_service = WorkflowsService(workspace_root, store_factory=MarkdownWorkflowStore)
        panel_service = PanelService(
            registry=_StubRegistry(),  # type: ignore[arg-type]
            spec_context=_StubSpecContextService(),  # type: ignore[arg-type]
            workspace_root=workspace_root,
            telemetry=_StubTelemetry(),
            workflows_service=workflows_service,
        )
        views: dict[str, Any] = {
            **BASE_STUB_VIEWS,
            "api_workflows": render_api_workflows_list(panel_service),
            "api_workflow_detail": render_api_workflow_detail(workflows_service),
        }
        handler_cls = make_handler_class(views, token=token, telemetry=_StubTelemetry())
        return ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)

    def test_cache_invalidated_on_mtime_change(self) -> None:
        tmp = self._setup_temp_workspace()
        try:
            server = self._build_server("cache-token", tmp)
            port = server.server_address[1]
            base = f"http://127.0.0.1:{port}"
            thread = threading.Thread(
                target=lambda: server.serve_forever(poll_interval=0.05), daemon=True
            )
            thread.start()

            try:
                status, _, body = get(f"{base}/api/workflows/cache-test-workflow")
                assert status == 200
                data = json.loads(body)
                assert "version-one" in data["description"]

                wf_file = (
                    tmp / ".dadaia" / "agentic" / "workflows" / "cache-test-workflow.workflow.md"
                )
                wf_file.write_text(
                    self._WORKFLOW_TEMPLATE.format(description="version-two"),
                    encoding="utf-8",
                )
                future_mtime = time.time() + 2
                os.utime(wf_file, (future_mtime, future_mtime))

                status2, _, body2 = get(f"{base}/api/workflows/cache-test-workflow")
                assert status2 == 200
                data2 = json.loads(body2)
                assert "version-two" in data2["description"], (
                    "Cache was NOT invalidated after mtime change — "
                    f"still got: {data2['description']!r}"
                )
            finally:
                server.shutdown()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
