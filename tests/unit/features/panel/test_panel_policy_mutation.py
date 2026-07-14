"""Unit tests for the Wave C panel policy mutation routes (T-28-C-02).

Two layers:

1. **View layer** — the PUT / validate view callables directly: content-type (415), size
   (413), JSON + overlay-shape + semantic validation (400 with structured field paths),
   atomic write + ``.last-good.json`` backup, the *default*-context-only rule (D-2), and
   the invalid-blocks-execution invariant (an invalid candidate is never persisted, so it
   can never block a future run).

2. **Handler layer** — the in-process request driver exercising ``do_PUT`` /
   ``do_POST`` body reading by Content-Length, the Host-guard-first invariant (no bearer),
   and the 413 envelope at the handler before the body is read.

Five survivors, one per real decision:
  1. PUT reject pipeline (415/413/invalid-json/unknown-workflow/harness-mismatch/
     non-default-ctx), each asserting the store stays untouched.
  2. PUT persists atomically + takes a .last-good backup.
  3. An invalid candidate never overwrites a prior good file.
  4. Kimi profile PUT -> GET -> resolver round-trip.
  5. Handler PUT/POST body-read + 413-before-read + Host-guard-first (no view reached).
"""

from __future__ import annotations

import io
import json
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import pytest

from dadaia_workspace.core.models.workflow_execution import WorkflowModelPolicyOverlay
from dadaia_workspace.features.lifecycle.policy_resolver import WorkflowExecutionPolicyResolver
from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.views.workflow_policy import (
    render_api_workflow_model_policy,
    render_post_workflow_model_policy_validate,
    render_put_workflow_model_policy,
)
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
)

pytestmark = pytest.mark.unit


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia").mkdir(parents=True)
    return tmp_path


def _store(tmp_path: Path) -> JsonWorkflowModelPolicyStore:
    return JsonWorkflowModelPolicyStore(_workspace(tmp_path))


def _factory(
    store: JsonWorkflowModelPolicyStore,
) -> Callable[..., WorkflowExecutionPolicyResolver]:
    catalog = governed_workflow_catalog()

    def _f(
        context: str, *, overlay: WorkflowModelPolicyOverlay | None = None
    ) -> WorkflowExecutionPolicyResolver:
        resolved = overlay if overlay is not None else store.load()
        return WorkflowExecutionPolicyResolver(catalog=catalog, overlay=resolved)

    return _f


def _decode(result: tuple[int, str, bytes]) -> tuple[int, dict]:  # type: ignore[type-arg]
    status, _ct, body = result
    return status, json.loads(body.decode("utf-8"))


def _valid_policy_body() -> bytes:
    return json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {
                        "implementation_reviews": {"steps": {"implement": "codex-review-deep"}}
                    }
                }
            },
        }
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# 1. PUT reject pipeline — every rejection leaves the store untouched
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "content_type", "qs", "expected_error"),
    [
        pytest.param(
            _valid_policy_body(),
            "text/plain",
            {},
            "unsupported_media_type",
            id="415-non-json-content-type",
        ),
        pytest.param(
            b'{"x":"' + b"a" * (65 * 1024) + b'"}',
            "application/json",
            {},
            "payload_too_large",
            id="413-oversized-payload",
        ),
        pytest.param(b"{not json", "application/json", {}, "invalid_json", id="400-invalid-json"),
        pytest.param(
            json.dumps(
                {
                    "schema_version": "workflow-model-policy-v1",
                    "policy_id": "default",
                    "contexts": {
                        "default": {
                            "workflows": {"nope": {"steps": {"implement": "codex-review-deep"}}}
                        }
                    },
                }
            ).encode("utf-8"),
            "application/json",
            {},
            "invalid_policy",
            id="400-unknown-workflow",
        ),
        pytest.param(
            json.dumps(
                {
                    "schema_version": "workflow-model-policy-v1",
                    "policy_id": "default",
                    "contexts": {
                        "default": {
                            "workflows": {
                                "implementation_reviews": {
                                    "steps": {"implement": "pi-reasoning-high"}
                                }
                            }
                        }
                    },
                }
            ).encode("utf-8"),
            "application/json",
            {},
            "invalid_policy",
            id="400-harness-mismatched-profile",
        ),
        pytest.param(
            _valid_policy_body(),
            "application/json",
            {"context": ["other"]},
            "unsupported_context",
            id="400-non-default-context",
        ),
    ],
)
def test_put_reject_pipeline_never_writes(
    tmp_path: Path,
    body: bytes,
    content_type: str,
    qs: dict[str, list[str]],
    expected_error: str,
) -> None:
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))

    status, payload = _decode(view(body=body, content_type=content_type, qs=qs))

    assert status in (400, 413, 415)
    assert payload["error"] == expected_error
    assert not store.path.exists()

    # POST validate mirrors the same reject path for a representative 400 case, also no write.
    if expected_error == "invalid_policy":
        validate_view = render_post_workflow_model_policy_validate(store, _factory(store))
        v_status, v_payload = _decode(validate_view(body=body, content_type=content_type, qs=qs))
        assert v_status == 400
        assert v_payload["error"] == "invalid_policy"
        assert not store.path.exists()


# ---------------------------------------------------------------------------
# 2. PUT persists atomically + .last-good backup
# ---------------------------------------------------------------------------


def test_put_persists_valid_policy_atomically_with_last_good_backup(tmp_path: Path) -> None:
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))
    # Seed a prior valid file so the next save backs it up to .last-good.json.
    store.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={
                "default": {
                    "implementation_reviews": {"implement": "codex-implementation-standard"}
                }
            },
        )
    )

    status, payload = _decode(
        view(body=_valid_policy_body(), content_type="application/json", qs={})
    )

    assert status == 200
    assert payload["saved"] is True
    overlay = store.load()
    assert overlay is not None
    assert (
        overlay.step_profile("default", "implementation_reviews", "implement")
        == "codex-review-deep"
    )
    assert store.last_good_path.exists()
    backup = json.loads(store.last_good_path.read_text(encoding="utf-8"))
    seeded = backup["contexts"]["default"]["workflows"]["implementation_reviews"]["steps"][
        "implement"
    ]
    assert seeded == "codex-implementation-standard"

    # Validate view accepts the same valid body without ever writing.
    validate_view = render_post_workflow_model_policy_validate(store, _factory(store))
    v_status, v_payload = _decode(
        validate_view(body=_valid_policy_body(), content_type="application/json", qs={})
    )
    assert v_status == 200
    assert v_payload["valid"] is True


# ---------------------------------------------------------------------------
# 3. Invalid candidate never overwrites a prior good file
# ---------------------------------------------------------------------------


def test_put_invalid_candidate_never_overwrites_a_good_file(tmp_path: Path) -> None:
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))
    store.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={"default": {"implementation_reviews": {"implement": "codex-review-deep"}}},
        )
    )
    before = store.path.read_text(encoding="utf-8")
    bad = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation_reviews": {"steps": {"implement": "ghost"}}}
                }
            },
        }
    ).encode("utf-8")

    status, _payload = _decode(view(body=bad, content_type="application/json", qs={}))

    assert status == 400
    assert store.path.read_text(encoding="utf-8") == before


# ---------------------------------------------------------------------------
# 4. Kimi profile PUT -> GET -> resolver round-trip
# ---------------------------------------------------------------------------


def test_kimi_profile_round_trips_through_put_get_and_resolver(tmp_path: Path) -> None:
    """v0.1.45 T-45-06: the governed OpenRouter kimi profile persists end-to-end.

    Selecting the kimi profile on a pi step, saving via PUT, reloading via GET, and
    resolving the persisted overlay all agree: the persisted value is the PROFILE ID
    ``pi-openrouter-kimi-high`` (not a raw ``moonshotai/kimi-k2.5:high`` — the resolver
    rejects raw ids), and the resolver resolves that profile to the discrete pi option
    ``moonshotai/kimi-k2.5:high``.
    """
    store = _store(tmp_path)
    factory = _factory(store)
    put = render_put_workflow_model_policy(store, factory)
    body = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {
                        "implementation_reviews": {
                            "default_harness": "pi",
                            "steps": {"implement": "pi-openrouter-kimi-high"},
                        }
                    }
                }
            },
        }
    ).encode("utf-8")

    status, payload = _decode(put(body=body, content_type="application/json", qs={}))
    assert status == 200
    assert payload["saved"] is True

    get = render_api_workflow_model_policy(store)
    status, got = _decode(get(qs={}))
    assert status == 200
    persisted = got["policy"]["contexts"]["default"]["workflows"]["implementation_reviews"]
    assert persisted["steps"]["implement"] == "pi-openrouter-kimi-high"

    resolver = factory("default")
    snapshot = resolver.resolve("implementation_reviews", context="default")
    entry = snapshot.step("implement")
    assert entry is not None
    assert entry.harness == "pi"
    assert entry.model_profile == "pi-openrouter-kimi-high"
    assert entry.model == "moonshotai/kimi-k2.5"
    assert entry.reasoning == "high"
    assert f"{entry.model}:{entry.reasoning}" == "moonshotai/kimi-k2.5:high"


# ---------------------------------------------------------------------------
# 5. Handler layer — PUT/POST body-read + 413-before-read + Host-guard-first
# ---------------------------------------------------------------------------


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


class _RecordingView:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(
        self, body: bytes = b"", content_type: str = "", qs: object = None
    ) -> tuple[int, str, bytes]:
        self.calls.append({"body": body, "content_type": content_type, "qs": qs})
        return (200, "application/json", b'{"saved": true}')


def _drive(handler_class: type[BaseHTTPRequestHandler], raw: bytes) -> tuple[int, bytes]:
    sock = _FakeSocket(raw)
    handler_class(sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = sock._wfile.getvalue()
    status = int(response.split(b"\r\n", 1)[0].split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status, body


def test_handler_put_post_body_read_and_host_guard_first() -> None:
    payload = _valid_policy_body()

    # (a) PUT reads the body by Content-Length and forwards qs to the view.
    put_view = _RecordingView()
    put_handler_class = make_handler_class({"api_workflow_model_policy_put": put_view})
    raw_put = (
        b"PUT /api/workflow-model-policy?context=default HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
    )
    status_put, _body_put = _drive(put_handler_class, raw_put)
    assert status_put == 200
    assert len(put_view.calls) == 1
    assert put_view.calls[0]["body"] == payload
    assert put_view.calls[0]["content_type"] == "application/json"
    assert put_view.calls[0]["qs"] == {"context": ["default"]}

    # (b) POST validate reads the body the same way.
    post_view = _RecordingView()
    post_handler_class = make_handler_class({"api_workflow_model_policy_validate": post_view})
    raw_post = (
        b"POST /api/workflow-model-policy/validate HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
    )
    status_post, _body_post = _drive(post_handler_class, raw_post)
    assert status_post == 200
    assert post_view.calls[0]["body"] == payload

    # (c) Host-guard runs FIRST: a foreign Host is rejected before the view ever runs.
    guard_view = _RecordingView()
    guard_handler_class = make_handler_class({"api_workflow_model_policy_put": guard_view})
    raw_guard = (
        b"PUT /api/workflow-model-policy HTTP/1.1\r\n"
        b"Host: evil.example.com\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
    )
    status_guard, _body_guard = _drive(guard_handler_class, raw_guard)
    assert status_guard == 403
    assert guard_view.calls == []

    # (d) 413 fires from the declared Content-Length BEFORE the body is read/view reached.
    oversize_view = _RecordingView()
    oversize_handler_class = make_handler_class({"api_workflow_model_policy_put": oversize_view})
    raw_oversize = (
        b"PUT /api/workflow-model-policy HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: 999999999\r\n\r\n"
    )
    status_oversize, _body_oversize = _drive(oversize_handler_class, raw_oversize)
    assert status_oversize == 413
    assert oversize_view.calls == []
