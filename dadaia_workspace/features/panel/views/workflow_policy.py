"""Panel workflow model-governance views — control-plane GET + mutation endpoints (Wave C).

These views are the panel half of the v0.1.28 control plane (the CLI half is the
``dadaia workflow policy`` verbs). They read through the same container-built seams the
CLI uses — the governed :class:`WorkflowCatalog`, the built-in :mod:`model_profiles`
registry, the :class:`JsonWorkflowModelPolicyStore`, and the persisted
:class:`LifecycleRun` snapshots — so the panel and CLI never disagree on which model a
step runs (LAW: one resolver, one catalog, one policy file).

Endpoints
---------
GET routes (T-28-C-01, read-only):
  - ``GET /api/workflow-catalog`` — every governed workflow + its steps + effective vs
    default profile (resolved through the shared resolver).
  - ``GET /api/workflow-catalog/<id>`` — one governed workflow's detail.
  - ``GET /api/workflow-model-profiles`` — the built-in profile registry.
  - ``GET /api/workflow-model-policy?context=<ctx>`` — the persisted overlay (or the
    empty default when no overlay file exists; missing != invalid).
  - ``GET /api/lifecycle-runs?workflow=<id>&context=<ctx>`` — run history, reading each
    run's persisted ``workflow_policy`` snapshot verbatim (AC-7: never re-resolves).

Mutation routes (T-28-C-02, guarded writes):
  - ``PUT /api/workflow-model-policy?context=<ctx>`` — persist an overlay (validate →
    atomic write → ``.last-good.json`` backup).
  - ``POST /api/workflow-model-policy/validate`` — dry-run validation, no write.

Security posture (AC-5): the existing panel posture — loopback bind + Host-header
allowlist enforced in the handler BEFORE any view runs, NO bearer auth. The mutation
views additionally reject non-JSON content types (415), oversized payloads (413), and
invalid policy shapes (400 with structured field-path errors) before any write. Error
messages never echo the request body or any secret (OWASP A06).
"""

from __future__ import annotations

import datetime
import json
import re
from collections.abc import Callable
from typing import Protocol

from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.fragments.loader import (
    Fragment,
    FragmentError,
    FragmentLoader,
    FragmentNotFoundError,
)
from dadaia_workspace.features.lifecycle.policy_resolver import (
    PolicyResolutionError,
    WorkflowCatalog,
    WorkflowExecutionPolicyResolver,
)
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    DEFAULT_CONTEXT,
    JsonWorkflowModelPolicyStore,
    WorkflowModelPolicyOverlay,
    WorkflowModelPolicyStoreError,
)


class ResolverFactory(Protocol):
    """Builds a :class:`WorkflowExecutionPolicyResolver` for a context.

    The on-disk overlay is used when ``overlay`` is ``None``; a candidate overlay is
    bound instead during validation (T-28-C-02) so the candidate is resolved without
    being persisted.
    """

    def __call__(
        self, context: str, *, overlay: WorkflowModelPolicyOverlay | None = None
    ) -> WorkflowExecutionPolicyResolver: ...


#: Max accepted policy mutation body, in bytes (A03/A06 — DoS + slop guard). A real
#: overlay is a few hundred bytes; 64 KiB is generous headroom and a hard ceiling.
_MAX_POLICY_BODY_BYTES = 64 * 1024

#: A governed workflow id is a conservative identifier — letters, digits, underscore.
_WORKFLOW_ID_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")

#: A fragment id is ``workflow.step`` — letters, digits, underscore, and a single dot
#: separator. The conservative pattern rejects path traversal (``..``, ``/``) and any
#: shell/path metacharacter before the loader ever touches disk (OWASP A03).
_FRAGMENT_ID_RE = re.compile(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$")

_JSON = "application/json; charset=utf-8"


def _json_response(status: int, payload: object) -> tuple[int, str, bytes]:
    return (status, _JSON, json.dumps(payload).encode("utf-8"))


# ---------------------------------------------------------------------------
# Effective-vs-default resolution helper
# ---------------------------------------------------------------------------


def _effective_steps(
    resolver: WorkflowExecutionPolicyResolver,
    workflow_id: str,
    context: str,
    *,
    catalog: WorkflowCatalog,
) -> list[dict[str, object]]:
    """Return per-step rows with both the *default* and the *effective* profile.

    The effective profile is what the shared resolver currently resolves for the
    (context, workflow) given the persisted overlay; the default is the library default
    on the catalog step. A row carries ``is_overridden`` so the panel can render the
    default-vs-effective diff without a second resolve in the browser.

    A resolver failure (e.g. an invalid persisted overlay) is surfaced to the caller —
    the GET catalog view turns it into a 200 with a per-workflow ``error`` field so a
    broken overlay does not blank the whole catalog.
    """
    workflow = catalog.workflow(workflow_id)
    if workflow is None:
        return []
    snapshot = resolver.resolve(workflow_id, context=context)
    rows: list[dict[str, object]] = []
    for cat_step in workflow.steps:
        entry = snapshot.step(cat_step.label)
        if entry is None:  # pragma: no cover - resolver returns an entry per step
            continue
        rows.append(
            {
                "step": cat_step.label,
                "role": cat_step.role,
                "harness": entry.harness,
                "default_profile": cat_step.default_profile,
                "effective_profile": entry.model_profile,
                "model": entry.model,
                "reasoning": entry.reasoning,
                "source": entry.source.value,
                "fragments": list(entry.fragments),
                "output_schema": entry.output_schema,
                "is_overridden": entry.model_profile != cat_step.default_profile,
            }
        )
    return rows


def _workflow_to_dict(
    resolver: WorkflowExecutionPolicyResolver,
    catalog: WorkflowCatalog,
    workflow_id: str,
    context: str,
) -> dict[str, object]:
    base: dict[str, object] = {"workflow_id": workflow_id}
    try:
        base["steps"] = _effective_steps(resolver, workflow_id, context, catalog=catalog)
    except PolicyResolutionError as exc:
        # A broken/stale overlay must not blank the catalog — surface a per-workflow
        # error and still list the default steps from the catalog (no resolve).
        workflow = catalog.workflow(workflow_id)
        base["error"] = str(exc)
        base["steps"] = [
            {
                "step": s.label,
                "role": s.role,
                "harness": s.default_harness,
                "default_profile": s.default_profile,
                "effective_profile": s.default_profile,
                "is_overridden": False,
            }
            for s in (workflow.steps if workflow else ())
        ]
    return base


# ---------------------------------------------------------------------------
# GET views (T-28-C-01)
# ---------------------------------------------------------------------------


def render_api_workflow_catalog(
    catalog: WorkflowCatalog,
    resolver_factory: ResolverFactory,
) -> Callable[..., tuple[int, str, bytes]]:
    """GET /api/workflow-catalog — every governed workflow with default+effective steps."""

    def _view(qs: dict[str, list[str]] | None = None, **_kwargs: object) -> tuple[int, str, bytes]:
        context = _context_from_qs(qs)
        resolver = resolver_factory(context)
        workflows = [
            _workflow_to_dict(resolver, catalog, wf.workflow_id, context)
            for wf in catalog.workflows
        ]
        return _json_response(
            200,
            {
                "generated_at": _now_iso(),
                "context": context,
                "workflows": workflows,
            },
        )

    return _view


def render_api_workflow_catalog_detail(
    catalog: WorkflowCatalog,
    resolver_factory: ResolverFactory,
) -> Callable[..., tuple[int, str, bytes]]:
    """GET /api/workflow-catalog/<id> — one governed workflow's detail."""

    def _view(
        workflow_id: str = "",
        qs: dict[str, list[str]] | None = None,
        **_kwargs: object,
    ) -> tuple[int, str, bytes]:
        if not workflow_id or not _WORKFLOW_ID_RE.match(workflow_id):
            return _json_response(
                400, {"error": "invalid_workflow_id", "message": "Invalid workflow id."}
            )
        if catalog.workflow(workflow_id) is None:
            return _json_response(
                404, {"error": "not_found", "message": f"Workflow {workflow_id!r} not found."}
            )
        context = _context_from_qs(qs)
        resolver = resolver_factory(context)
        payload = _workflow_to_dict(resolver, catalog, workflow_id, context)
        payload["context"] = context
        return _json_response(200, payload)

    return _view


def render_api_workflow_model_profiles() -> Callable[..., tuple[int, str, bytes]]:
    """GET /api/workflow-model-profiles — the built-in profile registry (no I/O)."""

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        profiles = [p.to_dict() for p in model_profiles.list_profiles()]
        return _json_response(200, {"generated_at": _now_iso(), "profiles": profiles})

    return _view


def _fragment_to_dict(fragment: Fragment) -> dict[str, object]:
    """Project a loaded fragment onto the read-only inspector payload.

    Carries the resolved body plus the inspector-relevant metadata: dynamic-context
    selectors (``dynamic_inputs``), static inputs, and the output schema id. The
    filesystem ``path`` is deliberately NOT exposed (no operator-local path leak, A06).
    """
    return {
        "id": fragment.id,
        "role": fragment.role,
        "workflow": fragment.workflow,
        "step": fragment.step,
        "static_inputs": list(fragment.static_inputs),
        "dynamic_inputs": list(fragment.dynamic_inputs),
        "output_schema": fragment.output_schema,
        "max_context_policy": fragment.max_context_policy,
        "body": fragment.body,
    }


def render_api_workflow_fragment(
    loader: FragmentLoader,
) -> Callable[..., tuple[int, str, bytes]]:
    """GET /api/workflow-fragments/<fragment_id> — one fragment, read-only (T-28-D-01).

    Resolves a governed step's fragment id to its resolved body + dynamic-context
    selectors + output schema via the shared :class:`FragmentLoader`. The endpoint is
    strictly read-only — the panel inspector renders fragment content but never edits it
    (editing fragments is source-controlled release work, SPEC §6).

    Guardrails: the id is validated against :data:`_FRAGMENT_ID_RE` before any disk read
    (A03 — no path traversal); an unknown id is a 404; a malformed/unreadable fragment
    surfaces a 422 with an actionable message; no error echoes a filesystem path (A06).
    """

    def _view(fragment_id: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        if not fragment_id or not _FRAGMENT_ID_RE.match(fragment_id):
            return _json_response(
                400,
                {
                    "error": "invalid_fragment_id",
                    "message": "Fragment id must be of the form '<workflow>.<step>'.",
                },
            )
        try:
            fragment = loader.load_fragment(fragment_id)
        except FragmentNotFoundError:
            return _json_response(
                404,
                {
                    "error": "not_found",
                    "message": f"No fragment with id {fragment_id!r}.",
                },
            )
        except FragmentError as exc:
            # A malformed fragment must not blank the inspector or leak a path: surface a
            # generic, actionable message (the precise loader message may carry the disk
            # path, so it is intentionally not forwarded to the client — A06).
            _ = exc
            return _json_response(
                422,
                {
                    "error": "invalid_fragment",
                    "message": f"Fragment {fragment_id!r} could not be loaded.",
                },
            )
        return _json_response(200, _fragment_to_dict(fragment))

    return _view


def render_api_workflow_model_policy(
    store: JsonWorkflowModelPolicyStore,
) -> Callable[..., tuple[int, str, bytes]]:
    """GET /api/workflow-model-policy?context=<ctx> — the persisted overlay.

    Missing file ⇒ the empty default overlay (200) — *missing != invalid* (LAW 4). A
    present-but-invalid file ⇒ 409 with an actionable message and the ``.last-good.json``
    untouched (the panel shows the operator the overlay is broken).
    """

    def _view(qs: dict[str, list[str]] | None = None, **_kwargs: object) -> tuple[int, str, bytes]:
        context = _context_from_qs(qs)
        try:
            overlay = store.load()
        except WorkflowModelPolicyStoreError as exc:
            return _json_response(
                409,
                {
                    "error": "invalid_policy",
                    "message": str(exc),
                    "context": context,
                },
            )
        if overlay is None:
            return _json_response(
                200,
                {
                    "context": context,
                    "exists": False,
                    "policy": _empty_overlay_dict(context),
                },
            )
        return _json_response(
            200,
            {"context": context, "exists": True, "policy": overlay.to_dict()},
        )

    return _view


def render_api_lifecycle_runs(
    run_store: object,
) -> Callable[..., tuple[int, str, bytes]]:
    """GET /api/lifecycle-runs?workflow=<id>&context=<ctx> — run history (AC-7).

    Reads each run's persisted ``workflow_policy`` snapshot **verbatim** — it never
    re-resolves the current policy, so a historical run always shows the model it
    actually ran on, even after the live overlay changes.
    """

    def _view(qs: dict[str, list[str]] | None = None, **_kwargs: object) -> tuple[int, str, bytes]:
        params = qs or {}
        workflow_filter = _first(params, "workflow")
        context_filter = _first(params, "context")
        runs = run_store.list_runs()  # type: ignore[attr-defined]
        items: list[dict[str, object]] = []
        for run in runs:
            snapshot = run.workflow_policy
            if context_filter is not None and run.context != context_filter:
                continue
            if workflow_filter is not None:
                snap_wf = snapshot.workflow_id if snapshot is not None else None
                if snap_wf != workflow_filter:
                    continue
            items.append(
                {
                    "run_id": run.run_id,
                    "context": run.context,
                    "release_id": run.release_id,
                    "command": run.command,
                    "phase": run.phase.value,
                    "status": run.status.value,
                    "workflow_policy": snapshot.to_dict() if snapshot is not None else None,
                }
            )
        return _json_response(
            200,
            {
                "generated_at": _now_iso(),
                "workflow": workflow_filter,
                "context": context_filter,
                "runs": items,
            },
        )

    return _view


# ---------------------------------------------------------------------------
# Mutation views (T-28-C-02)
# ---------------------------------------------------------------------------


def render_put_workflow_model_policy(
    store: JsonWorkflowModelPolicyStore,
    resolver_factory: ResolverFactory,
) -> Callable[..., tuple[int, str, bytes]]:
    """PUT /api/workflow-model-policy?context=<ctx> — validated, atomic overlay write.

    Pipeline: validate content-type (415) → size (413) → JSON parse (400) → overlay
    shape (400, field-path) → semantic resolve through the shared resolver (400) → atomic
    write with ``.last-good.json`` backup. Only the ``default`` context is honored (D-2);
    a non-default context is rejected 400.
    """

    def _view(
        body: bytes = b"",
        content_type: str = "",
        qs: dict[str, list[str]] | None = None,
        **_kwargs: object,
    ) -> tuple[int, str, bytes]:
        context = _context_from_qs(qs)
        validated = _validate_policy_request(store, resolver_factory, body, content_type, context)
        if isinstance(validated, tuple):
            return validated  # an error response
        overlay = validated
        try:
            store.save(overlay)
        except WorkflowModelPolicyStoreError as exc:
            return _json_response(500, {"error": "write_failed", "message": str(exc)})
        return _json_response(
            200,
            {"saved": True, "context": context, "policy": overlay.to_dict()},
        )

    return _view


def render_post_workflow_model_policy_validate(
    store: JsonWorkflowModelPolicyStore,
    resolver_factory: ResolverFactory,
) -> Callable[..., tuple[int, str, bytes]]:
    """POST /api/workflow-model-policy/validate — dry-run validation, no write."""

    def _view(
        body: bytes = b"",
        content_type: str = "",
        qs: dict[str, list[str]] | None = None,
        **_kwargs: object,
    ) -> tuple[int, str, bytes]:
        context = _context_from_qs(qs)
        validated = _validate_policy_request(store, resolver_factory, body, content_type, context)
        if isinstance(validated, tuple):
            return validated
        return _json_response(200, {"valid": True, "context": context})

    return _view


def _validate_policy_request(
    store: JsonWorkflowModelPolicyStore,
    resolver_factory: ResolverFactory,
    body: bytes,
    content_type: str,
    context: str,
) -> WorkflowModelPolicyOverlay | tuple[int, str, bytes]:
    """Validate a mutation request; return the parsed overlay or an error response.

    Shared by PUT and POST-validate so the two endpoints validate identically.
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
    # D-2: only the `default` context is honored.
    if context != DEFAULT_CONTEXT:
        return _json_response(
            400,
            {
                "error": "unsupported_context",
                "errors": [
                    {
                        "path": "context",
                        "message": f"Only the {DEFAULT_CONTEXT!r} context is honored.",
                    }
                ],
            },
        )
    # 400: overlay shape (typed parse with field-path errors).
    try:
        overlay = store.parse(raw)
    except WorkflowModelPolicyStoreError as exc:
        return _json_response(
            400,
            {"error": "invalid_policy", "errors": [{"path": "$", "message": str(exc)}]},
        )
    # 400: semantic validity — resolve every governed workflow through the shared
    # resolver against the candidate overlay. A stale step id, unknown profile,
    # harness/profile mismatch, or deprecated-without-replacement is rejected here,
    # so an invalid policy can never be persisted (and thus never blocks execution).
    semantic_error = _semantic_check(resolver_factory, overlay, context)
    if semantic_error is not None:
        return _json_response(400, semantic_error)
    return overlay


def _semantic_check(
    resolver_factory: ResolverFactory,
    overlay: WorkflowModelPolicyOverlay,
    context: str,
) -> dict[str, object] | None:
    """Resolve every workflow named in the overlay against a candidate resolver.

    Returns ``None`` when the candidate is valid, else a 400-shaped error dict with a
    structured field path identifying the offending workflow/step.
    """
    resolver = resolver_factory(context, overlay=overlay)
    workflows = overlay.contexts.get(context, {})
    for workflow_id in workflows:
        try:
            resolver.resolve(workflow_id, context=context)
        except PolicyResolutionError as exc:
            return {
                "error": "invalid_policy",
                "errors": [
                    {
                        "path": f"contexts.{context}.workflows.{workflow_id}",
                        "message": str(exc),
                    }
                ],
            }
    return None


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()


def _first(params: dict[str, list[str]], key: str) -> str | None:
    vals = params.get(key)
    return vals[0] if vals else None


def _context_from_qs(qs: dict[str, list[str]] | None) -> str:
    return _first(qs or {}, "context") or DEFAULT_CONTEXT


def _empty_overlay_dict(context: str) -> dict[str, object]:
    return {
        "schema_version": "workflow-model-policy-v1",
        "policy_id": DEFAULT_CONTEXT,
        "contexts": {context: {"workflows": {}}},
    }


__all__ = [
    "render_api_lifecycle_runs",
    "render_api_workflow_catalog",
    "render_api_workflow_catalog_detail",
    "render_api_workflow_fragment",
    "render_api_workflow_model_policy",
    "render_api_workflow_model_profiles",
    "render_post_workflow_model_policy_validate",
    "render_put_workflow_model_policy",
]
