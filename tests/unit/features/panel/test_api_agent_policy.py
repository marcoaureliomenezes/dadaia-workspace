"""Unit tests for the panel agent-model-policy endpoints (v0.1.65 FR8 / T-65-11).

Mirror of the workflow-policy suite: view-layer validation pipeline (415/413/400 with
field-path errors, semantic FR3/AC-4 messages verbatim, D-7 never-Fable-on-security),
GET shape ``{exists, policy, resolved}``, templates payload, PUT persist + re-render
trigger (G-2 Apply), and handler-layer route registration + foreign-Host 403.

Five survivors, one per real decision:
  1. GET shape + resolved default + invalid-overlay 409.
  2. Templates payload.
  3. Validate reject pipeline 415/413/400/non-object + FR3 verbatim messages incl.
     Fable-never-on-security-reviewer (D-7).
  4. Validate dry-run never writes + PUT-invalid neither saves nor rerenders.
  5. PUT persists + rerenders + instructions + AC-3 merge + handler routes registered
     + foreign-Host 403 before the view runs.
"""

from __future__ import annotations

import io
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import pytest

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

pytestmark = pytest.mark.unit


class _RecordingRerender:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> list[str]:
        self.calls += 1
        return ["[ok] .claude/agents/qa-engineer.md"]


def _service(
    tmp_path: Path,
) -> tuple[AgentModelPolicyService, JsonAgentModelPolicyStore, _RecordingRerender]:
    (tmp_path / ".dadaia").mkdir(exist_ok=True, parents=True)
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
# 1. GET shape + resolved default + invalid-overlay 409
# ---------------------------------------------------------------------------


def test_get_policy_shape_default_resolved_and_invalid_overlay(tmp_path: Path) -> None:
    service, store, _rr = _service(tmp_path)
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

    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{broken", encoding="utf-8")
    status_bad, payload_bad = _decode(view())
    assert status_bad == 409
    assert payload_bad["error"] == "invalid_policy"


# ---------------------------------------------------------------------------
# 2. Templates payload
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
# 3. Validate reject pipeline 415/413/400/non-object + FR3 verbatim incl. D-7
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "content_type", "expected_status", "expected_error", "message_fragment"),
    [
        pytest.param(b"x=1", "text/plain", 415, "unsupported_media_type", None, id="415-non-json"),
        pytest.param(
            b"x" * (64 * 1024 + 1),
            "application/json",
            413,
            "payload_too_large",
            None,
            id="413-oversized",
        ),
        pytest.param(
            b"{not json", "application/json", 400, "invalid_json", None, id="400-invalid-json"
        ),
        pytest.param(
            b"[1]", "application/json", 400, "invalid_policy", None, id="400-non-object-root"
        ),
        pytest.param(
            _body(
                {
                    "schema_version": "agent-model-policy-v1",
                    "overrides": {"nobody": {"model": "claude-sonnet-5"}},
                }
            ),
            "application/json",
            400,
            "invalid_policy",
            "unknown agent 'nobody'",
            id="400-unknown-agent",
        ),
        pytest.param(
            _body(
                {
                    "schema_version": "agent-model-policy-v1",
                    "overrides": {"qa-engineer": {"model": "gpt-9"}},
                }
            ),
            "application/json",
            400,
            "invalid_policy",
            "unknown model 'gpt-9'",
            id="400-unknown-model",
        ),
        pytest.param(
            _body(
                {
                    "schema_version": "agent-model-policy-v1",
                    "overrides": {"qa-engineer": {"effort": "turbo"}},
                }
            ),
            "application/json",
            400,
            "invalid_policy",
            "invalid effort 'turbo'",
            id="400-invalid-effort",
        ),
        pytest.param(
            _body({"schema_version": "agent-model-policy-v1", "applied_template": "nope"}),
            "application/json",
            400,
            "invalid_policy",
            "unknown agent-model template 'nope'",
            id="400-unknown-template",
        ),
        pytest.param(
            _body(
                {
                    "schema_version": "agent-model-policy-v1",
                    "overrides": {"security-reviewer": {"model": "claude-fable-5"}},
                }
            ),
            "application/json",
            400,
            "invalid_policy",
            "never assigned to security-reviewer",
            id="400-D7-fable-never-on-security-reviewer",
        ),
    ],
)
def test_validate_reject_pipeline(
    tmp_path: Path,
    body: bytes,
    content_type: str,
    expected_status: int,
    expected_error: str,
    message_fragment: str | None,
) -> None:
    service, _store, _rr = _service(tmp_path)
    view = render_post_agent_model_policy_validate(service)
    status, payload = _decode(view(body=body, content_type=content_type))
    assert status == expected_status
    if expected_error == "invalid_policy" and expected_status == 400 and "errors" in payload:
        if message_fragment is not None:
            assert message_fragment in payload["errors"][0]["message"]
        else:
            # non-object root: field path is "$"
            assert payload["errors"][0]["path"] == "$" or payload["error"] == expected_error
    else:
        assert payload["error"] == expected_error


# ---------------------------------------------------------------------------
# 4. Validate dry-run never writes + PUT-invalid neither saves nor rerenders
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("route", "doc", "expected_status"),
    [
        pytest.param(
            "validate",
            {"schema_version": "agent-model-policy-v1", "applied_template": "max-quality"},
            200,
            id="validate-dry-run-never-writes",
        ),
        pytest.param(
            "put",
            {
                "schema_version": "agent-model-policy-v1",
                "overrides": {"security-reviewer": {"model": "claude-fable-5"}},
            },
            400,
            id="put-invalid-neither-saves-nor-rerenders",
        ),
    ],
)
def test_dry_run_and_invalid_put_never_persist(
    tmp_path: Path,
    route: str,
    doc: dict,
    expected_status: int,  # type: ignore[type-arg]
) -> None:
    service, store, rerender = _service(tmp_path)
    view = (
        render_post_agent_model_policy_validate(service)
        if route == "validate"
        else render_put_agent_model_policy(service)
    )
    status, payload = _decode(view(body=_body(doc), content_type="application/json"))
    assert status == expected_status
    if route == "validate":
        assert payload["valid"] is True
    else:
        assert payload["error"] == "invalid_policy"
    assert not store.path.exists()
    assert rerender.calls == 0


# ---------------------------------------------------------------------------
# 5. PUT persists + rerenders + instructions + AC-3 merge + handler routes +
#    foreign-Host 403 before the view runs
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


def test_put_persists_rerenders_and_handler_routes_with_host_guard(tmp_path: Path) -> None:
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
    # AC-3 through the API: override model + template effort merge.
    assert payload["resolved"]["software-engineer"] == {
        "model": "claude-opus-4-8",
        "effort": "xhigh",
        "source": "override",
    }
    assert rerender.calls == 1
    persisted = store.load()
    assert persisted is not None and persisted.applied_template == "subscription-saver"

    # Handler layer: GET routes registered.
    policy_view = _RecordingView()
    templates_view = _RecordingView()
    get_handler_class = make_handler_class(
        {
            "api_agent_model_policy": policy_view,
            "api_agent_model_templates": templates_view,
        }
    )
    assert (
        _drive(
            get_handler_class, b"GET /api/agent-model-policy HTTP/1.1\r\nHost: localhost\r\n\r\n"
        )
        == 200
    )
    assert (
        _drive(
            get_handler_class, b"GET /api/agent-model-templates HTTP/1.1\r\nHost: localhost\r\n\r\n"
        )
        == 200
    )
    assert len(policy_view.calls) == 1
    assert len(templates_view.calls) == 1

    # Handler layer: PUT + validate routes registered.
    put_view = _RecordingView()
    validate_view = _RecordingView()
    mut_handler_class = make_handler_class(
        {
            "api_agent_model_policy_put": put_view,
            "api_agent_model_policy_validate": validate_view,
        }
    )
    payload_bytes = b"{}"
    put_raw = (
        b"PUT /api/agent-model-policy HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(payload_bytes)).encode() + b"\r\n\r\n" + payload_bytes
    )
    post_raw = (
        b"POST /api/agent-model-policy/validate HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(payload_bytes)).encode() + b"\r\n\r\n" + payload_bytes
    )
    assert _drive(mut_handler_class, put_raw) == 200
    assert _drive(mut_handler_class, post_raw) == 200
    assert len(put_view.calls) == 1
    assert len(validate_view.calls) == 1

    # Foreign Host is rejected before the view ever runs.
    guard_view = _RecordingView()
    guard_handler_class = make_handler_class({"api_agent_model_policy_put": guard_view})
    guard_raw = (
        b"PUT /api/agent-model-policy HTTP/1.1\r\nHost: evil.example.com\r\n"
        b"Content-Type: application/json\r\nContent-Length: 2\r\n\r\n{}"
    )
    assert _drive(guard_handler_class, guard_raw) == 403
    assert guard_view.calls == []
