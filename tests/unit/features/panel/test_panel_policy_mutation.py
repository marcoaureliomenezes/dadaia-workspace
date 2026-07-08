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
    render_api_workflow_model_policy,
    render_post_workflow_model_policy_validate,
    render_put_workflow_model_policy,
)
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia").mkdir()
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
                    "workflows": {"implementation": {"steps": {"implement": "codex-review-deep"}}}
                }
            },
        }
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# PUT view — validation pipeline
# ---------------------------------------------------------------------------


def test_put_rejects_non_json_content_type_415(tmp_path: Path) -> None:
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))

    status, payload = _decode(view(body=_valid_policy_body(), content_type="text/plain", qs={}))

    assert status == 415
    assert payload["error"] == "unsupported_media_type"
    # Nothing was written.
    assert not store.path.exists()


def test_put_rejects_oversized_payload_413(tmp_path: Path) -> None:
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))
    huge = b'{"x":"' + b"a" * (65 * 1024) + b'"}'

    status, payload = _decode(view(body=huge, content_type="application/json", qs={}))

    assert status == 413
    assert payload["error"] == "payload_too_large"
    assert not store.path.exists()


def test_put_rejects_invalid_json_400(tmp_path: Path) -> None:
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))

    status, payload = _decode(view(body=b"{not json", content_type="application/json", qs={}))

    assert status == 400
    assert payload["error"] == "invalid_json"
    assert not store.path.exists()


def test_put_rejects_unknown_workflow_with_field_path_400(tmp_path: Path) -> None:
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))
    body = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {"workflows": {"nope": {"steps": {"implement": "codex-review-deep"}}}}
            },
        }
    ).encode("utf-8")

    status, payload = _decode(view(body=body, content_type="application/json", qs={}))

    assert status == 400
    assert payload["error"] == "invalid_policy"
    paths = [e["path"] for e in payload["errors"]]
    assert any("workflows.nope" in p for p in paths)
    assert not store.path.exists()


def test_put_rejects_harness_mismatched_profile_400(tmp_path: Path) -> None:
    # implement runs on codex; a pi profile is a harness mismatch → rejected, not written.
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))
    body = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {"implement": "pi-reasoning-high"}}}
                }
            },
        }
    ).encode("utf-8")

    status, payload = _decode(view(body=body, content_type="application/json", qs={}))

    assert status == 400
    assert payload["error"] == "invalid_policy"
    assert not store.path.exists()


def test_put_rejects_non_default_context_400(tmp_path: Path) -> None:
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))

    status, payload = _decode(
        view(body=_valid_policy_body(), content_type="application/json", qs={"context": ["other"]})
    )

    assert status == 400
    assert payload["error"] == "unsupported_context"
    assert not store.path.exists()


def test_put_persists_valid_policy_atomically_with_last_good_backup(tmp_path: Path) -> None:
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))
    # Seed a prior valid file so the next save backs it up to .last-good.json.
    store.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={
                "default": {"implementation": {"implement": "codex-implementation-standard"}}
            },
        )
    )

    status, payload = _decode(
        view(body=_valid_policy_body(), content_type="application/json", qs={})
    )

    assert status == 200
    assert payload["saved"] is True
    # The new overlay is persisted and loads back.
    overlay = store.load()
    assert overlay is not None
    assert overlay.step_profile("default", "implementation", "implement") == "codex-review-deep"
    # The prior file was backed up to .last-good.json (the seeded value).
    assert store.last_good_path.exists()
    backup = json.loads(store.last_good_path.read_text(encoding="utf-8"))
    seeded = backup["contexts"]["default"]["workflows"]["implementation"]["steps"]["implement"]
    assert seeded == "codex-implementation-standard"


def test_put_invalid_candidate_never_overwrites_a_good_file(tmp_path: Path) -> None:
    # invalid-blocks-execution: an invalid candidate must not be persisted, so a prior
    # good overlay (which a run resolves against) is left intact.
    store = _store(tmp_path)
    view = render_put_workflow_model_policy(store, _factory(store))
    store.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={"default": {"implementation": {"implement": "codex-review-deep"}}},
        )
    )
    before = store.path.read_text(encoding="utf-8")
    bad = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {"workflows": {"implementation": {"steps": {"implement": "ghost"}}}}
            },
        }
    ).encode("utf-8")

    status, _payload = _decode(view(body=bad, content_type="application/json", qs={}))

    assert status == 400
    # The good file is byte-identical — the invalid candidate never touched it.
    assert store.path.read_text(encoding="utf-8") == before


def test_kimi_profile_round_trips_through_put_get_and_resolver(tmp_path: Path) -> None:
    """v0.1.45 T-45-06: the governed OpenRouter kimi profile persists end-to-end.

    Selecting the kimi profile on a pi step, saving via PUT, reloading via GET, and
    resolving the persisted overlay all agree: the persisted value is the PROFILE ID
    ``pi-openrouter-kimi-high`` (not a raw ``moonshotai/kimi-k2.5:high`` — the resolver
    rejects raw ids), and the resolver resolves that profile to the discrete pi option
    ``moonshotai/kimi-k2.5:high`` (model ``moonshotai/kimi-k2.5`` at effort ``high``;
    v0.1.66 FR3 corrected the id from the invalid ``kimi-2.7``). No changes to the
    overlay store or resolver — only a new built-in profile makes kimi reachable.
    """
    store = _store(tmp_path)
    factory = _factory(store)
    put = render_put_workflow_model_policy(store, factory)
    # The step runs on codex by default; move it to pi (harness) AND select the kimi
    # pi-profile so the profile's harness matches the step's effective harness.
    body = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {
                        "implementation": {
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

    # GET returns the persisted PROFILE ID verbatim (round-trips).
    get = render_api_workflow_model_policy(store)
    status, got = _decode(get(qs={}))
    assert status == 200
    persisted = got["policy"]["contexts"]["default"]["workflows"]["implementation"]
    assert persisted["steps"]["implement"] == "pi-openrouter-kimi-high"

    # The resolver resolves the persisted profile to the pi moonshotai/kimi-k2.5:high
    # option.
    resolver = factory("default")
    snapshot = resolver.resolve("implementation", context="default")
    entry = snapshot.step("implement")
    assert entry is not None
    assert entry.harness == "pi"
    assert entry.model_profile == "pi-openrouter-kimi-high"
    assert entry.model == "moonshotai/kimi-k2.5"
    assert entry.reasoning == "high"
    assert f"{entry.model}:{entry.reasoning}" == "moonshotai/kimi-k2.5:high"


# ---------------------------------------------------------------------------
# POST validate view — no write
# ---------------------------------------------------------------------------


def test_validate_accepts_valid_policy_without_writing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    view = render_post_workflow_model_policy_validate(store, _factory(store))

    status, payload = _decode(
        view(body=_valid_policy_body(), content_type="application/json", qs={})
    )

    assert status == 200
    assert payload["valid"] is True
    assert not store.path.exists()  # validate never writes


def test_validate_rejects_invalid_policy_with_field_path(tmp_path: Path) -> None:
    store = _store(tmp_path)
    view = render_post_workflow_model_policy_validate(store, _factory(store))
    bad = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {"workflows": {"implementation": {"steps": {"implement": "ghost"}}}}
            },
        }
    ).encode("utf-8")

    status, payload = _decode(view(body=bad, content_type="application/json", qs={}))

    assert status == 400
    assert payload["error"] == "invalid_policy"
    assert not store.path.exists()


# ---------------------------------------------------------------------------
# Handler layer — do_PUT / do_POST body reading + Host guard
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


def test_handler_put_reads_body_and_calls_view() -> None:
    view = _RecordingView()
    handler_class = make_handler_class({"api_workflow_model_policy_put": view})
    payload = _valid_policy_body()
    raw = (
        b"PUT /api/workflow-model-policy?context=default HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
    )

    status, _body = _drive(handler_class, raw)

    assert status == 200
    assert len(view.calls) == 1
    assert view.calls[0]["body"] == payload
    assert view.calls[0]["content_type"] == "application/json"
    assert view.calls[0]["qs"] == {"context": ["default"]}


def test_handler_post_validate_reads_body_and_calls_view() -> None:
    view = _RecordingView()
    handler_class = make_handler_class({"api_workflow_model_policy_validate": view})
    payload = _valid_policy_body()
    raw = (
        b"POST /api/workflow-model-policy/validate HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
    )

    status, _body = _drive(handler_class, raw)

    assert status == 200
    assert view.calls[0]["body"] == payload


def test_handler_put_host_guard_runs_first_no_bearer() -> None:
    view = _RecordingView()
    handler_class = make_handler_class({"api_workflow_model_policy_put": view})
    payload = _valid_policy_body()
    raw = (
        b"PUT /api/workflow-model-policy HTTP/1.1\r\n"
        b"Host: evil.example.com\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
    )

    status, _body = _drive(handler_class, raw)

    assert status == 403  # foreign Host rejected before the view runs
    assert view.calls == []  # the view was never reached


def test_handler_put_oversized_content_length_413_before_read() -> None:
    view = _RecordingView()
    handler_class = make_handler_class({"api_workflow_model_policy_put": view})
    # Declare a Content-Length far over the envelope; the handler must 413 without
    # reaching the view (no need to send the actual bytes).
    raw = (
        b"PUT /api/workflow-model-policy HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: 999999999\r\n\r\n"
    )

    status, _body = _drive(handler_class, raw)

    assert status == 413
    assert view.calls == []
