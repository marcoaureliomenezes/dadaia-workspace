"""Integration: workflow-governance routes through the real PanelHandler (T-28-C-04).

Drives full HTTP requests through ``make_handler_class`` with the real control-plane
views wired to a real policy store + governed catalog + run store rooted in ``tmp_path``.
This exercises the actual route table, qs-aware GET dispatch, and body-reading
do_PUT/do_POST — the seam the Playwright editor depends on — without a live socket.

The Playwright editor flow (dropdown filtering, reset, validate banner, save-persists,
default-vs-effective diff) lives in ``tests/e2e/panel/workflow-policy-editor.spec.ts``;
this asserts the server contract those JS-driven assertions rely on.
"""

from __future__ import annotations

import io
import json
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from dadaia_workspace.core.models.workflow_execution import (
    WorkflowModelPolicyOverlay,
)
from dadaia_workspace.features.lifecycle.policy_resolver import (
    WorkflowExecutionPolicyResolver,
)
from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.views.workflow_policy import (
    render_api_lifecycle_runs,
    render_api_workflow_catalog,
    render_api_workflow_catalog_detail,
    render_api_workflow_model_policy,
    render_api_workflow_model_profiles,
    render_post_workflow_model_policy_validate,
    render_put_workflow_model_policy,
)
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
)


class _FakeSocket:
    def __init__(self, request_bytes: bytes) -> None:
        self._rfile = io.BytesIO(request_bytes)
        self._wfile = io.BytesIO()

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        return self._rfile if "r" in mode else self._wfile

    def getsockname(self) -> tuple[str, int]:
        return ("127.0.0.1", 4999)

    def getpeername(self) -> tuple[str, int]:
        return ("127.0.0.1", 12345)

    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)


def _drive(handler_class: type[BaseHTTPRequestHandler], raw: bytes) -> tuple[int, dict]:  # type: ignore[type-arg]
    sock = _FakeSocket(raw)
    handler_class(sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = sock._wfile.getvalue()
    status = int(response.split(b"\r\n", 1)[0].split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    parsed = json.loads(body.decode("utf-8")) if body else {}
    return status, parsed


def _views(tmp_path: Path) -> dict[str, Callable[..., tuple[int, str, bytes]]]:
    (tmp_path / ".dadaia").mkdir(exist_ok=True)
    catalog = governed_workflow_catalog()
    store = JsonWorkflowModelPolicyStore(tmp_path)
    run_store = JsonLifecycleRunStore(tmp_path)

    def factory(
        context: str, *, overlay: WorkflowModelPolicyOverlay | None = None
    ) -> WorkflowExecutionPolicyResolver:
        resolved = overlay if overlay is not None else store.load()
        return WorkflowExecutionPolicyResolver(catalog=catalog, overlay=resolved)

    return {
        "api_workflow_catalog": render_api_workflow_catalog(catalog, factory),
        "api_workflow_catalog_detail": render_api_workflow_catalog_detail(catalog, factory),
        "api_workflow_model_profiles": render_api_workflow_model_profiles(),
        "api_workflow_model_policy": render_api_workflow_model_policy(store),
        "api_workflow_model_policy_validate": render_post_workflow_model_policy_validate(
            store, factory
        ),
        "api_workflow_model_policy_put": render_put_workflow_model_policy(store, factory),
        "api_lifecycle_runs": render_api_lifecycle_runs(run_store),
    }


def _get(handler_class: type[BaseHTTPRequestHandler], path: str) -> tuple[int, dict]:  # type: ignore[type-arg]
    raw = (f"GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n").encode()
    return _drive(handler_class, raw)


def _put(handler_class: type[BaseHTTPRequestHandler], path: str, body: bytes) -> tuple[int, dict]:  # type: ignore[type-arg]
    raw = (
        f"PUT {path} HTTP/1.1\r\nHost: localhost\r\n"
        f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n"
    ).encode() + body
    return _drive(handler_class, raw)


def _post(handler_class: type[BaseHTTPRequestHandler], path: str, body: bytes) -> tuple[int, dict]:  # type: ignore[type-arg]
    raw = (
        f"POST {path} HTTP/1.1\r\nHost: localhost\r\n"
        f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n"
    ).encode() + body
    return _drive(handler_class, raw)


def test_get_routes_reachable(tmp_path: Path) -> None:
    """Catalog, catalog-detail, model-profiles, and lifecycle-runs are all reachable."""
    handler = make_handler_class(_views(tmp_path))
    status, body = _get(handler, "/api/workflow-catalog?context=default")
    assert status == 200
    assert any(w["workflow_id"] == "implementation" for w in body["workflows"])

    s1, b1 = _get(handler, "/api/workflow-catalog/implementation")
    assert s1 == 200 and b1["workflow_id"] == "implementation"
    s2, b2 = _get(handler, "/api/workflow-model-profiles")
    assert s2 == 200 and any(p["id"] == "codex-review-deep" for p in b2["profiles"])
    s3, b3 = _get(handler, "/api/lifecycle-runs?workflow=implementation&context=default")
    assert s3 == 200 and b3["runs"] == []


def test_put_round_trip_harness_only_validate_and_415(tmp_path: Path) -> None:
    """PUT round-trip (profile + harness-only + catalog diff) + validate-rejects + 415."""
    handler = make_handler_class(_views(tmp_path))
    payload = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {"implement": "codex-review-deep"}}}
                }
            },
        }
    ).encode("utf-8")

    put_status, put_body = _put(handler, "/api/workflow-model-policy?context=default", payload)
    assert put_status == 200 and put_body["saved"] is True

    get_status, get_body = _get(handler, "/api/workflow-model-policy?context=default")
    assert get_status == 200 and get_body["exists"] is True
    steps = get_body["policy"]["contexts"]["default"]["workflows"]["implementation"]["steps"]
    assert steps["implement"] == "codex-review-deep"

    # The catalog now reports the override as the effective profile (default-vs-effective).
    _cs, cat = _get(handler, "/api/workflow-catalog?context=default")
    impl = next(w for w in cat["workflows"] if w["workflow_id"] == "implementation")
    implement = next(s for s in impl["steps"] if s["step"] == "implement")
    assert implement["effective_profile"] == "codex-review-deep"
    assert implement["is_overridden"] is True

    # A harness-only PUT (no profile) returns 200, persists harness, and flags the diff (AC-6).
    harness_payload = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {}, "harnesses": {"implement": "pi"}}}
                }
            },
        }
    ).encode("utf-8")

    put_status, put_body = _put(
        handler, "/api/workflow-model-policy?context=default", harness_payload
    )
    assert put_status == 200 and put_body["saved"] is True

    get_status, get_body = _get(handler, "/api/workflow-model-policy?context=default")
    assert get_status == 200 and get_body["exists"] is True
    wf = get_body["policy"]["contexts"]["default"]["workflows"]["implementation"]
    assert wf["harnesses"]["implement"] == "pi"

    _cs, cat = _get(handler, "/api/workflow-catalog?context=default")
    impl = next(w for w in cat["workflows"] if w["workflow_id"] == "implementation")
    implement = next(s for s in impl["steps"] if s["step"] == "implement")
    assert implement["harness"] == "pi"
    assert implement["default_harness"] == "codex"
    assert implement["harness_overridden"] is True
    assert implement["effective_profile"] == "pi-implementation-standard"

    # validate rejects an invalid policy without writing.
    bad = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {"workflows": {"implementation": {"steps": {"implement": "ghost"}}}}
            },
        }
    ).encode("utf-8")
    status, body = _post(handler, "/api/workflow-model-policy/validate?context=default", bad)
    assert status == 400
    assert body["error"] == "invalid_policy"

    # non-JSON content-type on PUT -> 415.
    raw = (
        b"PUT /api/workflow-model-policy HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: text/plain\r\nContent-Length: 2\r\n\r\n{}"
    )
    status, body = _drive(handler, raw)
    assert status == 415
    assert body["error"] == "unsupported_media_type"
