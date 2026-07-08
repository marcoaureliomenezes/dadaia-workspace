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
    WorkflowModelPolicyOverlay,
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
    render_api_workflow_step_ledger,
)
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
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


def test_profiles_surface_full_pi_model_choices_incl_openrouter_kimi() -> None:
    """T-45-06: the profiles endpoint carries the full per-harness allowed model set.

    The pi harness surfaces the complete ``known_layer2_model_ids()`` catalog including the
    curated OpenRouter id — value ``moonshotai/kimi-k2.5:high`` (effort suffix NOT
    stripped; v0.1.66 FR3 corrected the id from the invalid ``kimi-2.7``), labelled
    "OpenRouter — moonshotai/kimi-k2.5 (high)".
    """
    view = render_api_workflow_model_profiles()
    status, payload = _decode(view())
    assert status == 200

    choices = payload["model_choices"]
    assert "pi" in choices and "codex" in choices

    pi_values = [c["value"] for c in choices["pi"]]
    # The exact effort-suffixed value is present and un-stripped.
    assert "moonshotai/kimi-k2.5:high" in pi_values
    # The full model_choices('pi') set is surfaced (no narrowing).
    assert set(pi_values) == {
        "gpt-5.5:high",
        "gpt-5.5:low",
        "gpt-5.3-codex:medium",
        "moonshotai/kimi-k2.5:high",
    }

    kimi = next(c for c in choices["pi"] if c["value"] == "moonshotai/kimi-k2.5:high")
    assert kimi["label"] == "OpenRouter — moonshotai/kimi-k2.5 (high)"

    # A registry (non-OpenRouter) id is labelled without the OpenRouter prefix.
    gpt = next(c for c in choices["pi"] if c["value"] == "gpt-5.5:high")
    assert gpt["label"] == "gpt-5.5 (high)"
    # codex does not carry the OpenRouter kimi option.
    assert "moonshotai/kimi-k2.5:high" not in [c["value"] for c in choices["codex"]]


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


# --- workflow-step ledger API (T-30-D-08 / minimal run-ledger exposure) ------------


def _run_with_ledger(run_id: str = "led-1") -> LifecycleRun:
    from dadaia_workspace.core.models.workflow_handoff import (
        WorkflowStepLedger,
        WorkflowStepRecord,
    )

    record = WorkflowStepRecord(
        run_id=run_id,
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload_ref=f".dadaia/runs/lifecycle/{run_id}/steps/release_scope-attempt-0.step-payload.json",
        content_hash="a" * 64,
        produced_at="2026-06-27T12:00:00Z",
        declared_consumers=("spec_create",),
    )
    return LifecycleRun(
        run_id=run_id,
        context="dadaia-workspace",
        release_id="v0.1.30",
        command="release_definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.RUNNING,
        current_step="release_scope",
        workflow_steps=WorkflowStepLedger(records=(record,)),
    )


def test_workflow_step_ledger_returns_metadata_only(tmp_path: Path) -> None:
    run_store = JsonLifecycleRunStore(_workspace(tmp_path))
    run_store.save(_run_with_ledger("led-1"))
    view = render_api_workflow_step_ledger(run_store)

    status, payload = _decode(view(qs={}))

    assert status == 200
    assert len(payload["runs"]) == 1
    steps = payload["runs"][0]["workflow_steps"]
    assert len(steps) == 1
    record = steps[0]
    # Metadata only: addressable key, ref, hash, declared consumers — NO payload body.
    assert record["producer_step"] == "release_scope"
    assert record["payload_ref"].endswith(".step-payload.json")
    assert record["content_hash"] == "a" * 64
    assert "payload" not in record
    # The serialised JSON carries no payload-body key anywhere.
    assert '"payload"' not in json.dumps(payload)


def test_workflow_step_ledger_filters_by_run_and_context(tmp_path: Path) -> None:
    run_store = JsonLifecycleRunStore(_workspace(tmp_path))
    run_store.save(_run_with_ledger("led-a"))
    run_store.save(_run_with_ledger("led-b"))
    view = render_api_workflow_step_ledger(run_store)

    status, payload = _decode(view(qs={"run": ["led-a"]}))
    assert status == 200
    assert [r["run_id"] for r in payload["runs"]] == ["led-a"]

    status2, payload2 = _decode(view(qs={"context": ["other-ctx"]}))
    assert status2 == 200
    assert payload2["runs"] == []
