"""Unit tests for the Wave C panel workflow-governance GET views (T-28-C-01).

These exercise the real view callables against the real governed catalog + built-in
profile registry, a real :class:`JsonWorkflowModelPolicyStore` rooted in ``tmp_path``,
and a real run store. The resolver factory binds the real resolver — the panel reads the
SAME governed source the CLI reads (no second model table).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.models.workflow_execution import (
    PolicySource,
    WorkflowPolicySnapshot,
    WorkflowPolicyStepEntry,
)
from dadaia_workspace.features.lifecycle.policy_resolver import (
    WorkflowExecutionPolicyResolver,
)
from dadaia_workspace.features.panel.views.workflow_policy import (
    render_api_lifecycle_runs,
    render_api_workflow_catalog,
    render_api_workflow_catalog_detail,
    render_api_workflow_model_policy,
    render_api_workflow_model_profiles,
)
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
    WorkflowModelPolicyOverlay,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia").mkdir()
    return tmp_path


def _store(tmp_path: Path) -> JsonWorkflowModelPolicyStore:
    return JsonWorkflowModelPolicyStore(_workspace(tmp_path))


def _resolver_factory(
    store: JsonWorkflowModelPolicyStore,
) -> Callable[..., WorkflowExecutionPolicyResolver]:
    catalog = governed_workflow_catalog()

    def _factory(
        context: str, *, overlay: WorkflowModelPolicyOverlay | None = None
    ) -> WorkflowExecutionPolicyResolver:
        resolved = overlay if overlay is not None else store.load()
        return WorkflowExecutionPolicyResolver(catalog=catalog, overlay=resolved)

    return _factory


def _decode(result: tuple[int, str, bytes]) -> tuple[int, dict]:  # type: ignore[type-arg]
    status, ct, body = result
    assert "application/json" in ct
    return status, json.loads(body.decode("utf-8"))


# ---------------------------------------------------------------------------
# GET /api/workflow-catalog
# ---------------------------------------------------------------------------


def test_catalog_lists_governed_workflows_with_default_and_effective(tmp_path: Path) -> None:
    store = _store(tmp_path)
    catalog = governed_workflow_catalog()
    view = render_api_workflow_catalog(catalog, _resolver_factory(store))

    status, payload = _decode(view(qs={}))

    assert status == 200
    ids = {w["workflow_id"] for w in payload["workflows"]}
    assert "implementation" in ids
    impl = next(w for w in payload["workflows"] if w["workflow_id"] == "implementation")
    step = impl["steps"][0]
    # With no overlay, effective == default and nothing is overridden.
    assert step["default_profile"] == step["effective_profile"]
    assert step["is_overridden"] is False
    assert step["source"] == PolicySource.LIBRARY_DEFAULT.value


def test_catalog_reflects_overlay_override_as_effective(tmp_path: Path) -> None:
    store = _store(tmp_path)
    # Override implementation.implement to the codex deep profile.
    store.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={
                "default": {"implementation": {"implement": "codex-review-deep"}},
            },
        )
    )
    catalog = governed_workflow_catalog()
    view = render_api_workflow_catalog(catalog, _resolver_factory(store))

    _status, payload = _decode(view(qs={}))

    impl = next(w for w in payload["workflows"] if w["workflow_id"] == "implementation")
    implement = next(s for s in impl["steps"] if s["step"] == "implement")
    assert implement["effective_profile"] == "codex-review-deep"
    assert implement["is_overridden"] is True
    assert implement["source"] == PolicySource.DEFAULT_OVERLAY.value


# ---------------------------------------------------------------------------
# GET /api/workflow-catalog — harness dimension (T-29-C-01)
# ---------------------------------------------------------------------------


def test_catalog_row_carries_default_harness_and_unflagged_when_codex(tmp_path: Path) -> None:
    """With no overlay, every row carries the catalog default harness and no harness flag."""
    store = _store(tmp_path)
    catalog = governed_workflow_catalog()
    view = render_api_workflow_catalog(catalog, _resolver_factory(store))

    _status, payload = _decode(view(qs={}))

    impl = next(w for w in payload["workflows"] if w["workflow_id"] == "implementation")
    step = impl["steps"][0]
    assert step["default_harness"] == "codex"
    assert step["harness"] == "codex"
    assert step["harness_overridden"] is False
    # T-29-C-02: the per-harness default profiles are exposed for the panel auto-profile —
    # the same map the resolver uses, so a harness toggle picks the resolver's choice.
    assert step["default_profiles"]["codex"] == "codex-implementation-standard"
    assert step["default_profiles"]["pi"] == "pi-implementation-standard"


def test_catalog_row_flags_harness_override_from_overlay(tmp_path: Path) -> None:
    """An overlay step ``harness: pi`` makes the row resolve pi + sets the harness flag."""
    store = _store(tmp_path)
    store.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={"default": {"implementation": {}}},
            step_harness_overlay={"default": {"implementation": {"implement": "pi"}}},
        )
    )
    catalog = governed_workflow_catalog()
    view = render_api_workflow_catalog(catalog, _resolver_factory(store))

    _status, payload = _decode(view(qs={}))

    impl = next(w for w in payload["workflows"] if w["workflow_id"] == "implementation")
    implement = next(s for s in impl["steps"] if s["step"] == "implement")
    # The catalog default harness stays codex; the effective harness is pi + flagged.
    assert implement["default_harness"] == "codex"
    assert implement["harness"] == "pi"
    assert implement["harness_overridden"] is True
    # Auto-profile-on-harness-override: the PI default profile is selected, also flagged.
    assert implement["effective_profile"] == "pi-implementation-standard"
    assert implement["is_overridden"] is True


def test_catalog_error_fallback_row_carries_harness_fields(tmp_path: Path) -> None:
    """A broken overlay still surfaces default_harness + harness_overridden=False per row."""
    store = _store(tmp_path)
    # An overlay naming an unknown step makes resolve() raise → the per-workflow error path.
    store.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={"default": {"implementation": {"no_such_step": "codex-review-deep"}}},
        )
    )
    catalog = governed_workflow_catalog()
    view = render_api_workflow_catalog(catalog, _resolver_factory(store))

    _status, payload = _decode(view(qs={}))

    impl = next(w for w in payload["workflows"] if w["workflow_id"] == "implementation")
    assert "error" in impl
    step = impl["steps"][0]
    assert step["default_harness"] == "codex"
    assert step["harness"] == "codex"
    assert step["harness_overridden"] is False


# ---------------------------------------------------------------------------
# GET /api/workflow-catalog/<id>
# ---------------------------------------------------------------------------


def test_catalog_detail_returns_one_workflow(tmp_path: Path) -> None:
    store = _store(tmp_path)
    catalog = governed_workflow_catalog()
    view = render_api_workflow_catalog_detail(catalog, _resolver_factory(store))

    status, payload = _decode(view(workflow_id="implementation", qs={}))

    assert status == 200
    assert payload["workflow_id"] == "implementation"
    assert len(payload["steps"]) > 0


def test_catalog_detail_unknown_is_404(tmp_path: Path) -> None:
    store = _store(tmp_path)
    catalog = governed_workflow_catalog()
    view = render_api_workflow_catalog_detail(catalog, _resolver_factory(store))

    status, payload = _decode(view(workflow_id="nope", qs={}))

    assert status == 404
    assert payload["error"] == "not_found"


def test_catalog_detail_rejects_bad_id(tmp_path: Path) -> None:
    store = _store(tmp_path)
    catalog = governed_workflow_catalog()
    view = render_api_workflow_catalog_detail(catalog, _resolver_factory(store))

    status, payload = _decode(view(workflow_id="../etc", qs={}))

    assert status == 400
    assert payload["error"] == "invalid_workflow_id"


# ---------------------------------------------------------------------------
# GET /api/workflow-model-profiles
# ---------------------------------------------------------------------------


def test_profiles_lists_builtin_registry() -> None:
    view = render_api_workflow_model_profiles()

    status, payload = _decode(view())

    assert status == 200
    ids = {p["id"] for p in payload["profiles"]}
    assert "codex-implementation-standard" in ids
    assert "pi-reasoning-high" in ids


# ---------------------------------------------------------------------------
# GET /api/workflow-model-policy
# ---------------------------------------------------------------------------


def test_policy_get_missing_returns_empty_default_not_error(tmp_path: Path) -> None:
    # missing != invalid: a missing overlay file returns the empty default at 200.
    store = _store(tmp_path)
    view = render_api_workflow_model_policy(store)

    status, payload = _decode(view(qs={}))

    assert status == 200
    assert payload["exists"] is False
    assert payload["policy"]["contexts"]["default"]["workflows"] == {}


def test_policy_get_returns_persisted_overlay(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={"default": {"implementation": {"implement": "codex-review-deep"}}},
        )
    )
    view = render_api_workflow_model_policy(store)

    status, payload = _decode(view(qs={}))

    assert status == 200
    assert payload["exists"] is True
    steps = payload["policy"]["contexts"]["default"]["workflows"]["implementation"]["steps"]
    assert steps["implement"] == "codex-review-deep"


def test_policy_get_invalid_file_returns_409(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{not json", encoding="utf-8")
    view = render_api_workflow_model_policy(store)

    status, payload = _decode(view(qs={}))

    assert status == 409
    assert payload["error"] == "invalid_policy"


# ---------------------------------------------------------------------------
# GET /api/lifecycle-runs  (AC-7: reads the persisted snapshot, never re-resolves)
# ---------------------------------------------------------------------------


def _run_with_snapshot(
    run_id: str, *, profile: str, workflow_id: str = "implementation"
) -> LifecycleRun:
    snapshot = WorkflowPolicySnapshot(
        workflow_id=workflow_id,
        policy_id="default",
        resolved_at="2026-06-25T00:00:00Z",
        steps=(
            WorkflowPolicyStepEntry(
                step="implement",
                harness="codex",
                model_profile=profile,
                model="gpt-5.5",
                reasoning="medium",
                source=PolicySource.LIBRARY_DEFAULT,
            ),
        ),
    )
    return LifecycleRun(
        run_id=run_id,
        context="dadaia-workspace",
        release_id="v0.1.28",
        command="implement",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.COMPLETED,
        current_step="implement",
        workflow_policy=snapshot,
    )


def test_lifecycle_runs_reads_persisted_snapshot_verbatim(tmp_path: Path) -> None:
    run_store = JsonLifecycleRunStore(_workspace(tmp_path))
    run_store.save(_run_with_snapshot("run-1", profile="codex-implementation-standard"))
    view = render_api_lifecycle_runs(run_store)

    status, payload = _decode(view(qs={}))

    assert status == 200
    assert len(payload["runs"]) == 1
    snap = payload["runs"][0]["workflow_policy"]
    assert snap["steps"][0]["model_profile"] == "codex-implementation-standard"


def test_lifecycle_runs_filters_by_workflow_and_context(tmp_path: Path) -> None:
    run_store = JsonLifecycleRunStore(_workspace(tmp_path))
    run_store.save(_run_with_snapshot("run-a", profile="codex-review-deep"))
    run_store.save(
        _run_with_snapshot("run-b", profile="codex-review-deep", workflow_id="release_definition")
    )
    view = render_api_lifecycle_runs(run_store)

    status, payload = _decode(view(qs={"workflow": ["implementation"]}))

    assert status == 200
    assert [r["run_id"] for r in payload["runs"]] == ["run-a"]

    status2, payload2 = _decode(view(qs={"context": ["other-ctx"]}))
    assert status2 == 200
    assert payload2["runs"] == []
