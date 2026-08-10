"""Panel L1 agent-model-policy views (v0.1.65 FR8 / T-65-11).

Endpoint half of the Sub-agents tab:
same security posture (loopback bind + Host-guard in the handler BEFORE any view
runs, NO bearer), same mutation validation pipeline (415 content-type → 413 size →
400 JSON parse → 400 shape/semantic with field-path errors) BEFORE any write.

Endpoints
---------
- ``GET /api/agent-model-policy`` — ``{exists, policy, resolved}``; ``resolved`` is
  the full source-tagged roster (``override|template|default|pack``). An invalid
  persisted overlay is a 409 (missing != invalid).
- ``GET /api/agent-model-templates`` — the 3 built-in templates (full rosters) +
  selectable registry model ids + the effort vocabulary.
- ``POST /api/agent-model-policy/validate`` — dry-run, no write; surfaces the FR3/
  AC-4 store messages verbatim (incl. D-7 never-Fable-on-security).
- ``PUT /api/agent-model-policy`` — validate → atomic save (+ ``.last-good.json``)
  → **re-render BOTH L1 projections** (G-2 Apply); the response carries the
  re-render summary + per-harness pickup instructions for the post-apply pop-up.

Error messages never echo the request body or any secret (OWASP A06).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol

from dadaia_workspace.core.models.agent_model_policy import (
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
)


class AgentModelPolicyServicePort(Protocol):
    """The feature-service surface these views consume (structural typing).

    The concrete ``features/agents/model_policy.AgentModelPolicyService`` is
    container-wired; the ``features-no-cross-feature`` independence contract forbids
    a direct sibling import, so the views depend on this Protocol only.
    """

    def get_policy(self) -> dict[str, object]: ...

    def templates_payload(self) -> dict[str, object]: ...

    def validate(self, raw: object) -> AgentModelPolicyOverlay: ...

    def apply(self, raw: object) -> dict[str, object]: ...


#: Max accepted policy mutation body, in bytes — same envelope as the handler-level
#: mutation views (a real overlay is a few hundred bytes; 64 KiB is a hard ceiling).
_MAX_POLICY_BODY_BYTES = 64 * 1024

_JSON = "application/json; charset=utf-8"


def _json_response(status: int, payload: object) -> tuple[int, str, bytes]:
    return (status, _JSON, json.dumps(payload).encode("utf-8"))


# ---------------------------------------------------------------------------
# GET views
# ---------------------------------------------------------------------------


def render_api_agent_model_policy(
    service: AgentModelPolicyServicePort,
) -> Callable[..., tuple[int, str, bytes]]:
    """GET /api/agent-model-policy — ``{exists, policy, resolved}``.

    Missing overlay ⇒ 200 with the empty policy + the ``balanced``-resolved roster
    (*missing != invalid*). A present-but-invalid file ⇒ 409 with the actionable
    store message (the panel shows the operator the overlay is broken).
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        try:
            payload = service.get_policy()
        except AgentModelPolicyStoreError as exc:
            return _json_response(409, {"error": "invalid_policy", "message": str(exc)})
        return _json_response(200, payload)

    return _view


def render_api_agent_model_templates(
    service: AgentModelPolicyServicePort,
) -> Callable[..., tuple[int, str, bytes]]:
    """GET /api/agent-model-templates — built-ins + model choices + effort vocab."""

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        return _json_response(200, service.templates_payload())

    return _view


# ---------------------------------------------------------------------------
# Mutation views
# ---------------------------------------------------------------------------


def render_put_agent_model_policy(
    service: AgentModelPolicyServicePort,
) -> Callable[..., tuple[int, str, bytes]]:
    """PUT /api/agent-model-policy — validated, atomic overlay write + re-render (G-2).

    Pipeline: 415 content-type → 413 size → 400 JSON parse → 400 shape/semantic
    (store parse, field-path errors) → atomic save with ``.last-good.json`` backup →
    agents-only re-render of BOTH projections. The response carries what was
    re-rendered plus the per-harness pickup instructions payload.
    """

    def _view(
        body: bytes = b"",
        content_type: str = "",
        **_kwargs: object,
    ) -> tuple[int, str, bytes]:
        validated = _validate_policy_request(service, body, content_type)
        if isinstance(validated, tuple):
            return validated  # an error response
        try:
            result = service.apply(validated.to_dict())
        except AgentModelPolicyStoreError as exc:
            return _json_response(500, {"error": "write_failed", "message": str(exc)})
        return _json_response(200, {"saved": True, **result})

    return _view


def render_post_agent_model_policy_validate(
    service: AgentModelPolicyServicePort,
) -> Callable[..., tuple[int, str, bytes]]:
    """POST /api/agent-model-policy/validate — dry-run validation, no write."""

    def _view(
        body: bytes = b"",
        content_type: str = "",
        **_kwargs: object,
    ) -> tuple[int, str, bytes]:
        validated = _validate_policy_request(service, body, content_type)
        if isinstance(validated, tuple):
            return validated
        return _json_response(200, {"valid": True})

    return _view


def _validate_policy_request(
    service: AgentModelPolicyServicePort,
    body: bytes,
    content_type: str,
) -> AgentModelPolicyOverlay | tuple[int, str, bytes]:
    """Validate a mutation request; return the parsed overlay or an error response.

    Shared by PUT and POST-validate so the two endpoints validate identically —
    the canonical mutation-view pipeline order.
    """
    # 415: content-type must be JSON.
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type != "application/json":
        return _json_response(
            415,
            {
                "error": "unsupported_media_type",
                "message": "Content-Type must be application/json.",
            },
        )
    # 413: oversized payload.
    if len(body) > _MAX_POLICY_BODY_BYTES:
        return _json_response(
            413,
            {
                "error": "payload_too_large",
                "message": f"Policy payload exceeds {_MAX_POLICY_BODY_BYTES} bytes.",
            },
        )
    # 400: not valid JSON. Never echo the body (A06).
    try:
        raw = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json_response(
            400,
            {"error": "invalid_json", "message": "Request body is not valid JSON."},
        )
    if not isinstance(raw, dict):
        return _json_response(
            400,
            {
                "error": "invalid_policy",
                "errors": [{"path": "$", "message": "Policy root must be a JSON object."}],
            },
        )
    # 400: shape + semantic validity through the shared store parse (FR3/AC-4 —
    # unknown agent/model/effort/template and D-7 Fable-on-security surface their
    # distinct actionable messages verbatim).
    try:
        return service.validate(raw)
    except AgentModelPolicyStoreError as exc:
        return _json_response(
            400,
            {"error": "invalid_policy", "errors": [{"path": "$", "message": str(exc)}]},
        )


__all__ = [
    "render_api_agent_model_policy",
    "render_api_agent_model_templates",
    "render_post_agent_model_policy_validate",
    "render_put_agent_model_policy",
]
