"""Unit tests for the panel agent-model-policy endpoints (v0.1.65 FR8 / T-65-11).

Mirror of the workflow-policy suite: view-layer validation pipeline (415/413/400 with
field-path errors, semantic FR3/AC-4 messages verbatim, D-7 never-Fable-on-security),
GET shape ``{exists, policy, resolved}``, templates payload, PUT persist + re-render
trigger (G-2 Apply), and handler-layer route registration + foreign-Host 403.
"""

from __future__ import annotations

import io
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from dadaia_workspace.features.agents.model_policy import AgentModelPolicyService
from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.views.agent_policy import (
    render_api_agent_model_policy,
    render_api_agent_model_templates,
    render_post_agent_model_policy_validate,
    render_put_agent_model_policy,
)
from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
    JsonAgentModelPolicyStore,
)


class _RecordingRerender:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> list[str]:
        self.calls += 1
        return ["[ok] .claude/agents/qa-engineer.md"]


def _service(
    tmp_path: Path,
) -> tuple[AgentModelPolicyService, JsonAgentModelPolicyStore, _RecordingRerender]:
    (tmp_path / ".dadaia").mkdir(exist_ok=True)
    store = JsonAgentModelPolicyStore(tmp_path)
    rerender = _RecordingRerender()
    service = AgentModelPolicyService(store=store, rerender=rerender)
    return service, store, rerender


def _decode(result: tuple[int, str, bytes]) -> tuple[int, dict]:  # type: ignore[type-arg]
    status, ct, body = result
    assert "application/json" in ct
    return status, json.loads(body.decode("utf-8"))


def _body(doc: dict) -> bytes:  # type: ignore[type-arg]
    return json.dumps(doc).encode("utf-8")


# ---------------------------------------------------------------------------
# GET /api/agent-model-policy
# ---------------------------------------------------------------------------


def test_get_policy_missing_overlay_shape(tmp_path: Path) -> None:
    service, _store, _rr = _service(tmp_path)
    view = render_api_agent_model_policy(service)
    status, payload = _decode(view())
    assert status == 200
    assert payload["exists"] is False
    assert payload["policy"]["schema_version"] == "agent-model-policy-v1"
    assert payload["resolved"]["software-engineer"] == {
        "model": "claude-sonnet-5",
        "effort": "xhigh",
        "source": "default",
    }


def test_get_policy_invalid_overlay_409(tmp_path: Path) -> None:
    service, store, _rr = _service(tmp_path)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{broken", encoding="utf-8")
    view = render_api_agent_model_policy(service)
    status, payload = _decode(view())
    assert status == 409
    assert payload["error"] == "invalid_policy"


# ---------------------------------------------------------------------------
# GET /api/agent-model-templates
# ---------------------------------------------------------------------------


def test_get_templates_payload(tmp_path: Path) -> None:
    service, _store, _rr = _service(tmp_path)
    view = render_api_agent_model_templates(service)
    status, payload = _decode(view())
    assert status == 200
    assert [t["id"] for t in payload["templates"]] == [
        "balanced",
        "subscription-saver",
        "max-quality",
    ]
    assert payload["templates"][0]["default"] is True
    assert len(payload["templates"][0]["assignments"]) == 9
    assert "claude-fable-5" in payload["models"]
    assert payload["efforts"] == ["low", "medium", "high", "xhigh", "max"]


# ---------------------------------------------------------------------------
# POST /api/agent-model-policy/validate — pipeline + AC-4 messages
# ---------------------------------------------------------------------------


def test_validate_rejects_non_json_content_type_415(tmp_path: Path) -> None:
    service, _store, _rr = _service(tmp_path)
    view = render_post_agent_model_policy_validate(service)
    status, payload = _decode(view(body=b"x=1", content_type="text/plain"))
    assert status == 415
    assert payload["error"] == "unsupported_media_type"


def test_validate_rejects_oversized_payload_413(tmp_path: Path) -> None:
    service, _store, _rr = _service(tmp_path)
    view = render_post_agent_model_policy_validate(service)
    status, payload = _decode(view(body=b"x" * (64 * 1024 + 1), content_type="application/json"))
    assert status == 413
    assert payload["error"] == "payload_too_large"


def test_validate_rejects_invalid_json_400(tmp_path: Path) -> None:
    service, _store, _rr = _service(tmp_path)
    view = render_post_agent_model_policy_validate(service)
    status, payload = _decode(view(body=b"{not json", content_type="application/json"))
    assert status == 400
    assert payload["error"] == "invalid_json"


def test_validate_rejects_non_object_root_400(tmp_path: Path) -> None:
    service, _store, _rr = _service(tmp_path)
    view = render_post_agent_model_policy_validate(service)
    status, payload = _decode(view(body=b"[1]", content_type="application/json"))
    assert status == 400
    assert payload["errors"][0]["path"] == "$"


def test_validate_surfaces_each_fr3_rejection_verbatim(tmp_path: Path) -> None:
    """AC-4: unknown agent/model/effort/template + Fable-on-security, distinct messages."""
    service, _store, _rr = _service(tmp_path)
    view = render_post_agent_model_policy_validate(service)
    cases = [
        (
            {
                "schema_version": "agent-model-policy-v1",
                "overrides": {"nobody": {"model": "claude-sonnet-5"}},
            },
            "unknown agent 'nobody'",
        ),
        (
            {
                "schema_version": "agent-model-policy-v1",
                "overrides": {"qa-engineer": {"model": "gpt-9"}},
            },
            "unknown model 'gpt-9'",
        ),
        (
            {
                "schema_version": "agent-model-policy-v1",
                "overrides": {"qa-engineer": {"effort": "turbo"}},
            },
            "invalid effort 'turbo'",
        ),
        (
            {"schema_version": "agent-model-policy-v1", "applied_template": "nope"},
            "unknown agent-model template 'nope'",
        ),
        (
            {
                "schema_version": "agent-model-policy-v1",
                "overrides": {"security-reviewer": {"model": "claude-fable-5"}},
            },
            "never assigned to security-reviewer",
        ),
    ]
    for doc, fragment in cases:
        status, payload = _decode(view(body=_body(doc), content_type="application/json"))
        assert status == 400, doc
        assert payload["error"] == "invalid_policy"
        assert fragment in payload["errors"][0]["message"], (fragment, payload)


def test_validate_dry_run_never_writes(tmp_path: Path) -> None:
    service, store, rerender = _service(tmp_path)
    view = render_post_agent_model_policy_validate(service)
    doc = {"schema_version": "agent-model-policy-v1", "applied_template": "max-quality"}
    status, payload = _decode(view(body=_body(doc), content_type="application/json"))
    assert status == 200 and payload["valid"] is True
    assert not store.path.exists()
    assert rerender.calls == 0


# ---------------------------------------------------------------------------
# PUT /api/agent-model-policy — persist + re-render (G-2 Apply)
# ---------------------------------------------------------------------------


def test_put_persists_rerenders_and_carries_instructions(tmp_path: Path) -> None:
    service, store, rerender = _service(tmp_path)
    view = render_put_agent_model_policy(service)
    doc = {
        "schema_version": "agent-model-policy-v1",
        "applied_template": "subscription-saver",
        "overrides": {"software-engineer": {"model": "claude-opus-4-8"}},
    }
    status, payload = _decode(view(body=_body(doc), content_type="application/json"))
    assert status == 200
    assert payload["saved"] is True
    assert payload["rerendered"] == ["[ok] .claude/agents/qa-engineer.md"]
    assert "claude" in payload["instructions"] and "codex" in payload["instructions"]
    # AC-3 through the API: override model + template effort.
    assert payload["resolved"]["software-engineer"] == {
        "model": "claude-opus-4-8",
        "effort": "xhigh",
        "source": "override",
    }
    assert rerender.calls == 1
    persisted = store.load()
    assert persisted is not None and persisted.applied_template == "subscription-saver"


def test_put_invalid_neither_saves_nor_rerenders(tmp_path: Path) -> None:
    service, store, rerender = _service(tmp_path)
    view = render_put_agent_model_policy(service)
    doc = {
        "schema_version": "agent-model-policy-v1",
        "overrides": {"security-reviewer": {"model": "claude-fable-5"}},
    }
    status, payload = _decode(view(body=_body(doc), content_type="application/json"))
    assert status == 400
    assert payload["error"] == "invalid_policy"
    assert not store.path.exists()
    assert rerender.calls == 0


# ---------------------------------------------------------------------------
# Handler layer — routes registered + foreign Host 403
# ---------------------------------------------------------------------------


class _FakeSocket:
    def __init__(self, request_bytes: bytes) -> None:
        self._rfile = io.BytesIO(request_bytes)
        self._wfile = io.BytesIO()

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        return self._rfile if "r" in mode else self._wfile

    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)


class _RecordingView:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> tuple[int, str, bytes]:
        self.calls.append(kwargs)
        return (200, "application/json", b"{}")


def _drive(handler_class: type[BaseHTTPRequestHandler], raw: bytes) -> int:
    sock = _FakeSocket(raw)
    handler_class(sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = sock._wfile.getvalue()
    return int(response.split(b"\r\n", 1)[0].split(b" ")[1])


def test_handler_get_routes_registered() -> None:
    policy_view = _RecordingView()
    templates_view = _RecordingView()
    handler_class = make_handler_class(
        {
            "api_agent_model_policy": policy_view,
            "api_agent_model_templates": templates_view,
        }
    )
    assert (
        _drive(handler_class, b"GET /api/agent-model-policy HTTP/1.1\r\nHost: localhost\r\n\r\n")
        == 200
    )
    assert (
        _drive(handler_class, b"GET /api/agent-model-templates HTTP/1.1\r\nHost: localhost\r\n\r\n")
        == 200
    )
    assert len(policy_view.calls) == 1
    assert len(templates_view.calls) == 1


def test_handler_put_and_validate_routes_registered() -> None:
    put_view = _RecordingView()
    validate_view = _RecordingView()
    handler_class = make_handler_class(
        {
            "api_agent_model_policy_put": put_view,
            "api_agent_model_policy_validate": validate_view,
        }
    )
    payload = b"{}"
    put_raw = (
        b"PUT /api/agent-model-policy HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
    )
    post_raw = (
        b"POST /api/agent-model-policy/validate HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
    )
    assert _drive(handler_class, put_raw) == 200
    assert _drive(handler_class, post_raw) == 200
    assert len(put_view.calls) == 1
    assert len(validate_view.calls) == 1


def test_handler_foreign_host_403_before_view() -> None:
    put_view = _RecordingView()
    handler_class = make_handler_class({"api_agent_model_policy_put": put_view})
    raw = (
        b"PUT /api/agent-model-policy HTTP/1.1\r\nHost: evil.example.com\r\n"
        b"Content-Type: application/json\r\nContent-Length: 2\r\n\r\n{}"
    )
    assert _drive(handler_class, raw) == 403
    assert put_view.calls == []
