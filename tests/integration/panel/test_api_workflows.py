"""Integration tests for GET /api/workflows and GET /api/workflows/<name>.

Coverage areas (PR3-20 spec):
  - Bearer token enforcement (auth)
  - Cache invalidation when underlying file mtime changes
  - Response shape against SPEC §5.3 / §5.4
  - Path traversal / invalid workflow name rejection

Uses real workflow files from .dadaia/agentic/workflows/ — no mocks.
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
from dadaia_workspace.features.panel.views.api import (
    render_api_workflow_detail,
    render_api_workflows_list,
)

import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Workspace root
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubRegistry:
    def list_entries(self, include_stale: bool = True) -> list:
        return []


class _StubSpecContextService:
    def list_all(self) -> list:
        return []


class _StubTelemetry:
    is_degraded: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(url: str, token: str | None = None) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, headers, resp.read()
    except urllib.error.HTTPError as exc:
        headers = {k.lower(): v for k, v in exc.headers.items()}
        return exc.code, headers, exc.read()


def _build_server(
    token: str,
    workspace_root: Path,
) -> ThreadingHTTPServer:
    panel_service = PanelService(
        registry=_StubRegistry(),  # type: ignore[arg-type]
        spec_context=_StubSpecContextService(),  # type: ignore[arg-type]
        workspace_root=workspace_root,
        telemetry=_StubTelemetry(),
    )

    def _stub_html(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "text/html; charset=utf-8", b"<html>ok</html>")

    def _stub_json(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "application/json; charset=utf-8", b"{}")

    views: dict[str, Any] = {
        "index": _stub_html,
        "api_servers": _stub_json,
        "api_contexts": _stub_json,
        "api_agents": _stub_json,
        "api_agent_prompt": _stub_json,
        "api_workflows": render_api_workflows_list(panel_service),
        "api_workflow_detail": render_api_workflow_detail(panel_service._workflows_service),
        "memory": _stub_html,
        "memory_view": _stub_html,
        "static": lambda **kw: (200, "text/plain; charset=utf-8", b"ok"),
    }
    HandlerClass = make_handler_class(views, token=token, telemetry=_StubTelemetry())
    return ThreadingHTTPServer(("127.0.0.1", 0), HandlerClass)


_TOKEN = "workflows-integ-token-pr3-20"


@pytest.fixture(scope="module")
def workflows_server():
    """Server backed by real workflow files; yields (base_url, token)."""
    server = _build_server(_TOKEN, _WORKSPACE_ROOT)
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield base_url, _TOKEN
    server.shutdown()


# ---------------------------------------------------------------------------
# Tests: Bearer enforcement on /api/workflows
# ---------------------------------------------------------------------------


class TestWorkflowsBearerEnforcement:
    def test_workflows_list_401_without_token(self, workflows_server: Any) -> None:
        """GET /api/workflows without Authorization → 401."""
        base, token = workflows_server
        status, _, _ = _get(f"{base}/api/workflows")
        assert status == 401

    def test_workflows_list_200_with_token(self, workflows_server: Any) -> None:
        """GET /api/workflows with Bearer → 200."""
        base, token = workflows_server
        status, _, _ = _get(f"{base}/api/workflows", token=token)
        assert status == 200

    def test_workflow_detail_401_without_token(self, workflows_server: Any) -> None:
        """GET /api/workflows/<name> without Authorization → 401."""
        base, token = workflows_server
        status, _, _ = _get(f"{base}/api/workflows/hotfix-release")
        assert status == 401

    def test_workflow_detail_200_with_token(self, workflows_server: Any) -> None:
        """GET /api/workflows/hotfix-release with Bearer → 200."""
        base, token = workflows_server
        status, _, _ = _get(f"{base}/api/workflows/hotfix-release", token=token)
        assert status == 200


# ---------------------------------------------------------------------------
# Tests: Workflow list response shape (SPEC §5.3)
# ---------------------------------------------------------------------------


class TestWorkflowsListShape:
    def test_top_level_keys_present(self, workflows_server: Any) -> None:
        """Response has generated_at, source_hint, workflows keys."""
        base, token = workflows_server
        _, _, body = _get(f"{base}/api/workflows", token=token)
        data = json.loads(body)
        for key in ("generated_at", "source_hint", "workflows"):
            assert key in data, f"missing key: {key}"

    def test_source_hint_value(self, workflows_server: Any) -> None:
        """source_hint is the canonical path '.dadaia/agentic/workflows/'."""
        base, token = workflows_server
        _, _, body = _get(f"{base}/api/workflows", token=token)
        data = json.loads(body)
        assert data["source_hint"] == ".dadaia/agentic/workflows/"

    def test_workflows_list_contains_real_workflow(self, workflows_server: Any) -> None:
        """Response lists at least the 'hotfix-release' workflow from disk."""
        base, token = workflows_server
        _, _, body = _get(f"{base}/api/workflows", token=token)
        data = json.loads(body)
        names = {w["name"] for w in data["workflows"]}
        assert "hotfix-release" in names

    def test_workflow_item_shape(self, workflows_server: Any) -> None:
        """Each workflow item has required SPEC §5.3 fields; no stages[] or diagram_svg."""
        base, token = workflows_server
        _, _, body = _get(f"{base}/api/workflows", token=token)
        data = json.loads(body)
        item = next(w for w in data["workflows"] if w["name"] == "hotfix-release")
        for key in ("name", "display_name", "description", "version", "schema_version",
                    "stage_count", "agent_ids", "has_parallel", "has_gates", "source_path"):
            assert key in item, f"missing workflow item key: {key}"
        # LIST is lean (D1 synthesis decision) — no stages[] or diagram_svg
        assert "stages" not in item
        assert "diagram_svg" not in item


# ---------------------------------------------------------------------------
# Tests: Workflow detail response shape (SPEC §5.4)
# ---------------------------------------------------------------------------


class TestWorkflowDetailShape:
    def test_detail_top_level_keys(self, workflows_server: Any) -> None:
        """GET /api/workflows/hotfix-release → has name, stages, diagram_svg."""
        base, token = workflows_server
        _, _, body = _get(f"{base}/api/workflows/hotfix-release", token=token)
        data = json.loads(body)
        for key in ("name", "stages", "diagram_svg", "inputs", "agent_ids"):
            assert key in data, f"missing detail key: {key}"

    def test_detail_stages_shape(self, workflows_server: Any) -> None:
        """Each stage item has id, agent, needs, gate, on_failure keys."""
        base, token = workflows_server
        _, _, body = _get(f"{base}/api/workflows/hotfix-release", token=token)
        data = json.loads(body)
        for stage in data["stages"]:
            for key in ("id", "agent", "needs", "gate", "on_failure"):
                assert key in stage, f"stage missing key: {key}"

    def test_detail_not_found_returns_404(self, workflows_server: Any) -> None:
        """GET /api/workflows/nonexistent-workflow → 404."""
        base, token = workflows_server
        status, _, _ = _get(f"{base}/api/workflows/nonexistent-workflow", token=token)
        assert status == 404

    def test_detail_invalid_name_returns_400(self, workflows_server: Any) -> None:
        """GET /api/workflows/bad..name → 400 (dots violate regex)."""
        base, token = workflows_server
        status, _, body = _get(f"{base}/api/workflows/bad..name", token=token)
        assert status == 400
        data = json.loads(body)
        assert data.get("error") == "invalid_workflow_name"

    def test_detail_traversal_path_rejected(self, workflows_server: Any) -> None:
        """GET /api/workflows/../etc/passwd → 400 or 404 (regex blocks dots/slashes)."""
        base, token = workflows_server
        # The route pattern ^/api/workflows/(?P<workflow_name>[^/]+)$ prevents slashes.
        # A name with dots is caught by _WORKFLOW_NAME_RE before any I/O.
        status, _, _ = _get(f"{base}/api/workflows/..%2Fetc%2Fpasswd", token=token)
        assert status in (400, 404)


# ---------------------------------------------------------------------------
# Tests: Cache invalidation when file mtime changes
# ---------------------------------------------------------------------------


class TestWorkflowCacheInvalidation:
    """Verify that editing a workflow file and touching its mtime produces updated data.

    Strategy:
      1. Create a temp workspace with one minimal workflow file.
      2. Spin up a fresh server pointing at the temp workspace.
      3. Fetch the workflow detail — check initial description.
      4. Overwrite the file with a new description, update mtime.
      5. Fetch again — the new description must appear (cache invalidated).
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
        wf_file.write_text(self._WORKFLOW_TEMPLATE.format(description="version-one"), encoding="utf-8")
        return tmp

    def test_cache_invalidated_on_mtime_change(self) -> None:
        """After overwriting workflow file, new description is returned (cache busted)."""
        tmp = self._setup_temp_workspace()
        try:
            server = _build_server("cache-token", tmp)
            port = server.server_address[1]
            base = f"http://127.0.0.1:{port}"
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            try:
                # First fetch — must see "version-one"
                status, _, body = _get(f"{base}/api/workflows/cache-test-workflow", token="cache-token")
                assert status == 200
                data = json.loads(body)
                assert "version-one" in data["description"]

                # Overwrite with new description and advance mtime
                wf_file = tmp / ".dadaia" / "agentic" / "workflows" / "cache-test-workflow.workflow.md"
                wf_file.write_text(
                    self._WORKFLOW_TEMPLATE.format(description="version-two"),
                    encoding="utf-8",
                )
                # Advance mtime by ≥1 second to guarantee cache key differs
                future_mtime = time.time() + 2
                os.utime(wf_file, (future_mtime, future_mtime))

                # Second fetch — must see "version-two" (cache busted by mtime change)
                status2, _, body2 = _get(
                    f"{base}/api/workflows/cache-test-workflow", token="cache-token"
                )
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
