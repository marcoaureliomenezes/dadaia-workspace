"""Panel API views — workflow endpoints.

Two families:
- Legacy declarative-DAG endpoints (GET /api/workflows, GET /api/workflows/<name>) serving the
  ``*.workflow.md`` definitions.
- dadaia-workflow catalog endpoints (GET /api/dadaia-workflows, GET /api/dadaia-workflows/<name>)
  describing the real Python-owned lifecycle workflows with per-step harness/model options and a
  server-rendered SVG fluxogram.

Security (OWASP A03, A06): workflow-name path params are validated against
``_WORKFLOW_NAME_RE`` before any lookup; error messages are generic; json.dumps escapes output.
"""

from __future__ import annotations

import datetime
import json
import logging
import re
from collections.abc import Callable

from dadaia_workspace.core.harness_registry import is_l1
from dadaia_workspace.features.panel.service import PanelService

logger = logging.getLogger(__name__)


def render_api_workflows_list(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/workflows.

    Response shape (SPEC §5.3 — normative):
        {
            "generated_at": "ISO-8601",
            "source_hint": ".dadaia/agentic/workflows/",
            "workflows": [
                {
                    "name": str,
                    "display_name": str,
                    "description": str,
                    "version": str,
                    "schema_version": str,
                    "stage_count": int,        # integer — NOT stages[]
                    "agent_ids": list[str],
                    "has_parallel": bool,
                    "has_gates": bool,
                    "lifecycle_phase": str,    # canonical dev-lifecycle group
                    "source_path": str
                }
            ]
        }

    No "diagram_svg", no "stages[]" in the items — LIST is lean (D1 synthesis decision).
    Bearer required (SPEC §5.5, G9). Auth is enforced by the handler; this view
    only produces the payload.

    Security (OWASP A03, A06):
        - No user-controlled input is consumed in this view (no path params).
        - json.dumps() handles JSON-string escaping.
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        # Parse runtime filter from query-string (NFR5: default to "claude").
        # Canonical workflow definitions carry no per-provider discriminator;
        # all workflows are returned regardless of runtime.  The param is parsed
        # here so that ?runtime=codex requests are accepted without error.
        qs: dict[str, list[str]] = _kwargs.get("qs", {})  # type: ignore[assignment]
        _runtime_vals = qs.get("runtime")
        _runtime = (_runtime_vals[0].strip().lower() if _runtime_vals else "").strip()
        if not is_l1(_runtime):
            _runtime = "claude"

        summaries = service.list_workflow_summaries()
        generated_at = datetime.datetime.now(tz=datetime.UTC).isoformat()
        # Use a stable source_hint; the actual directory is opaque to the client.
        source_hint = ".dadaia/agentic/workflows/"
        workflow_items = [
            {
                "name": s.name,
                "display_name": s.display_name,
                "description": s.description,
                "version": s.version,
                "schema_version": s.schema_version,
                "stage_count": s.stage_count,
                "agent_ids": list(s.agent_ids),
                "has_parallel": s.has_parallel,
                "has_gates": s.has_gates,
                "lifecycle_phase": s.lifecycle_phase,
                "source_path": s.source_path,
            }
            for s in summaries
        ]
        payload = {
            "generated_at": generated_at,
            "source_hint": source_hint,
            "workflows": workflow_items,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


# ---------------------------------------------------------------------------
# Workflow name validation regex (SPEC §5.4, §6 path traversal guard)
# Allows: A-Z a-z 0-9 _ -  (no dots, no slashes, no spaces, no special chars)
# ---------------------------------------------------------------------------
_WORKFLOW_NAME_RE: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_-]+$")


def render_api_workflow_detail(
    workflows_service: object,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/workflows/<name>.

    Response shape (SPEC §5.4 — normative):
        {
            "name": str,
            "display_name": str,
            "description": str,
            "version": str,
            "schema_version": str,
            "inputs": [...],
            "stages": [{
                "id": str, "agent": str, "needs": [...],
                "parallel_group": str | null, "gate": bool,
                "expected_output_path": str | null,
                "must_include": [...] | null,
                "on_failure": str
            }],
            "diagram_svg": "<svg ... role='img' ...>...</svg>",
            "source_path": str
        }

    Status codes:
        200  — workflow found, detail returned.
        400  — name fails the regex ^[A-Za-z0-9_-]+$ OR path traversal attempt.
        404  — name valid but no matching workflow file exists.

    Security (OWASP A03, A06):
        - name validated against _WORKFLOW_NAME_RE before any service call.
        - Generic error messages to clients; detail logged at WARNING level.
        - json.dumps() handles JSON-string escaping.
    """

    def _view(workflow_name: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        # --- Validate workflow name against the regex ---
        if not workflow_name or not _WORKFLOW_NAME_RE.match(workflow_name):
            logger.warning(
                "render_api_workflow_detail: invalid workflow_name=%r (regex failed)",
                workflow_name,
            )
            error_body = json.dumps(
                {
                    "error": "invalid_workflow_name",
                    "message": "Invalid workflow name format or path traversal attempt.",
                }
            ).encode("utf-8")
            return (400, "application/json; charset=utf-8", error_body)

        # --- Call the service ---
        detail = workflows_service.get_detail(workflow_name)  # type: ignore[attr-defined]
        if detail is None:
            logger.debug("render_api_workflow_detail: workflow not found name=%r", workflow_name)
            error_body = json.dumps(
                {
                    "error": "not_found",
                    "message": f"Workflow {workflow_name!r} not found.",
                }
            ).encode("utf-8")
            return (404, "application/json; charset=utf-8", error_body)

        # --- Serialise stages --- (StageDTO dataclass → dict)
        stages_list = [
            {
                "id": s.id,
                "agent": s.agent,
                "needs": list(s.needs),
                "parallel_group": s.parallel_group,
                "gate": s.gate,
                "expected_output_path": s.expected_output_path,
                "must_include": list(s.must_include) if s.must_include is not None else None,
                "on_failure": s.on_failure,
            }
            for s in detail.stages
        ]

        payload = {
            "name": detail.name,
            "display_name": detail.display_name,
            "description": detail.description,
            "version": detail.version,
            "schema_version": detail.schema_version,
            "stage_count": detail.stage_count,
            "agent_ids": list(detail.agent_ids),
            "has_parallel": detail.has_parallel,
            "has_gates": detail.has_gates,
            "lifecycle_phase": detail.lifecycle_phase,
            "inputs": detail.inputs,
            "stages": stages_list,
            "diagram_svg": detail.diagram_svg,
            "source_path": detail.source_path,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


# ---------------------------------------------------------------------------
# dadaia-workflow catalog endpoints (WS-8 / ADR-E)
#
# These describe the *real* Python-owned dadaia-workflows (release_definition,
# implementation, deferred) with purpose, per-step harness/model options,
# availability, and a server-rendered SVG + Mermaid diagram. They are wholly
# additive to the legacy ``/api/workflows`` endpoints above (which serve the
# declarative ``*.workflow.md`` DAGs unchanged).
# ---------------------------------------------------------------------------


def _dadaia_workflow_to_dict(wf: object, *, include_steps: bool) -> dict[str, object]:
    """Serialise a DadaiaWorkflowDTO to a JSON-ready dict.

    The list form omits the heavy step bodies + diagram (lean cards); the detail
    form includes the full step sequence and the server-rendered SVG fluxogram.
    """
    base: dict[str, object] = {
        "name": getattr(wf, "name"),  # noqa: B009
        "display_name": getattr(wf, "display_name"),  # noqa: B009
        "purpose": getattr(wf, "purpose"),  # noqa: B009
        "availability": getattr(wf, "availability"),  # noqa: B009
        "step_count": getattr(wf, "step_count"),  # noqa: B009
    }
    if not include_steps:
        return base
    steps = [
        {
            "order": s.order,
            "label": s.label,
            "role": s.role,
            "purpose": s.purpose,
            "is_gate": s.is_gate,
            "harness_options": list(s.harness_options),
            "model_options": {k: list(v) for k, v in s.model_options.items()},
            "runtime_kind": s.runtime_kind,
            "fragment_id": s.fragment_id,
        }
        for s in getattr(wf, "steps")  # noqa: B009
    ]
    base["steps"] = steps
    base["diagram_svg"] = getattr(wf, "diagram_svg")  # noqa: B009
    return base


def render_api_dadaia_workflows_list(
    workflows_service: object,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/dadaia-workflows.

    Lists every dadaia-workflow with its purpose, availability, and step count
    (lean cards — no per-step bodies or diagrams). A deferred workflow is listed
    with ``availability == "deferred"`` so the panel can mark it unavailable.

    Security (OWASP A03, A06): no user input consumed; json.dumps escapes output.
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        workflows = workflows_service.list_dadaia_workflows()  # type: ignore[attr-defined]
        items = [_dadaia_workflow_to_dict(wf, include_steps=False) for wf in workflows]
        generated_at = datetime.datetime.now(tz=datetime.UTC).isoformat()
        payload = {
            "generated_at": generated_at,
            "source_hint": "dadaia-workflows (Python-owned lifecycle workflows)",
            "workflows": items,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def render_api_dadaia_workflow_detail(
    workflows_service: object,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/dadaia-workflows/<name>.

    Returns the full self-description: purpose, the ordered step sequence with
    per-step role/harness_options/model_options/availability flags, and the
    server-rendered SVG DAG fluxogram (``diagram_svg``) of the step sequence.

    Status codes: 200 found; 400 invalid name (regex / traversal); 404 unknown.

    Security (OWASP A03, A06): name validated against _WORKFLOW_NAME_RE before
    any lookup; generic error messages; json.dumps escapes output.
    """

    def _view(workflow_name: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        if not workflow_name or not _WORKFLOW_NAME_RE.match(workflow_name):
            logger.warning(
                "render_api_dadaia_workflow_detail: invalid name=%r (regex failed)",
                workflow_name,
            )
            error_body = json.dumps(
                {
                    "error": "invalid_workflow_name",
                    "message": "Invalid workflow name format or path traversal attempt.",
                }
            ).encode("utf-8")
            return (400, "application/json; charset=utf-8", error_body)

        detail = workflows_service.get_dadaia_workflow(workflow_name)  # type: ignore[attr-defined]
        if detail is None:
            logger.debug("render_api_dadaia_workflow_detail: not found name=%r", workflow_name)
            error_body = json.dumps(
                {
                    "error": "not_found",
                    "message": f"Workflow {workflow_name!r} not found.",
                }
            ).encode("utf-8")
            return (404, "application/json; charset=utf-8", error_body)

        payload = _dadaia_workflow_to_dict(detail, include_steps=True)
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view
