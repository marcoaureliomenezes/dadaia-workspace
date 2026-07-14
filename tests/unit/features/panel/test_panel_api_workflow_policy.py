"""Unit tests for the Wave C panel workflow-governance GET views (T-28-C-01).

These exercise the real view callables against the real governed catalog + built-in
profile registry, a real :class:`JsonWorkflowModelPolicyStore` rooted in ``tmp_path``,
and a real run store. The resolver factory binds the real resolver — the panel reads the
SAME governed source the CLI reads (no second model table).

Five survivors, one per real decision:
  1. Catalog default==effective + overlay override + broken-overlay error-fallback row.
  2. Harness dimension (default harness, pi override flag + auto-profile).
  3. Detail 200/404/400-bad-id.
  4. Profiles registry + full pi model set incl. kimi label.
  5. Policy GET missing-empty/persisted/invalid-409 + lifecycle-runs snapshot verbatim +
     filters + step-ledger metadata-only (no payload body leak) + ledger filters.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

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

pytestmark = pytest.mark.unit


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia").mkdir(parents=True)
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
# 1. Catalog default==effective + overlay override + broken-overlay error row
# ---------------------------------------------------------------------------


def test_catalog_default_override_and_error_fallback(tmp_path: Path) -> None:
    catalog = governed_workflow_catalog()

    # (a) No overlay: effective == default, nothing overridden.
    store_a = _store(tmp_path / "a")
    view_a = render_api_workflow_catalog(catalog, _resolver_factory(store_a))
    status_a, payload_a = _decode(view_a(qs={}))
    assert status_a == 200
    ids = {w["workflow_id"] for w in payload_a["workflows"]}
    assert "implementation_reviews" in ids
    impl_a = next(w for w in payload_a["workflows"] if w["workflow_id"] == "implementation_reviews")
    step_a = impl_a["steps"][0]
    assert step_a["default_profile"] == step_a["effective_profile"]
    assert step_a["is_overridden"] is False
    assert step_a["source"] == PolicySource.LIBRARY_DEFAULT.value

    # (b) Overlay override: effective diverges from default and is flagged.
    store_b = _store(tmp_path / "b")
    store_b.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={"default": {"implementation_reviews": {"implement": "codex-review-deep"}}},
        )
    )
    view_b = render_api_workflow_catalog(catalog, _resolver_factory(store_b))
    _status_b, payload_b = _decode(view_b(qs={}))
    impl_b = next(w for w in payload_b["workflows"] if w["workflow_id"] == "implementation_reviews")
    implement_b = next(s for s in impl_b["steps"] if s["step"] == "implement")
    assert implement_b["effective_profile"] == "codex-review-deep"
    assert implement_b["is_overridden"] is True
    assert implement_b["source"] == PolicySource.DEFAULT_OVERLAY.value

    # (c) Broken overlay (unknown step) → per-workflow error, but harness fields still present.
    store_c = _store(tmp_path / "c")
    store_c.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={"default": {"implementation_reviews": {"no_such_step": "codex-review-deep"}}},
        )
    )
    view_c = render_api_workflow_catalog(catalog, _resolver_factory(store_c))
    _status_c, payload_c = _decode(view_c(qs={}))
    impl_c = next(w for w in payload_c["workflows"] if w["workflow_id"] == "implementation_reviews")
    assert "error" in impl_c
    step_c = impl_c["steps"][0]
    assert step_c["default_harness"] == "codex"
    assert step_c["harness"] == "codex"
    assert step_c["harness_overridden"] is False


# ---------------------------------------------------------------------------
# 2. Harness dimension: default harness + pi override flag + auto-profile
# ---------------------------------------------------------------------------


def test_harness_dimension_default_and_override(tmp_path: Path) -> None:
    catalog = governed_workflow_catalog()

    # Default: catalog default harness, no override flag, per-harness default profiles exposed.
    store_default = _store(tmp_path / "default")
    view_default = render_api_workflow_catalog(catalog, _resolver_factory(store_default))
    _status, payload_default = _decode(view_default(qs={}))
    impl_default = next(
        w for w in payload_default["workflows"] if w["workflow_id"] == "implementation_reviews"
    )
    step_default = impl_default["steps"][0]
    assert step_default["default_harness"] == "codex"
    assert step_default["harness"] == "codex"
    assert step_default["harness_overridden"] is False
    assert step_default["default_profiles"]["codex"] == "codex-implementation-standard"
    assert step_default["default_profiles"]["pi"] == "pi-implementation-standard"

    # Override: overlay `harness: pi` resolves pi + auto-selects the pi default profile.
    store_pi = _store(tmp_path / "pi")
    store_pi.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={"default": {"implementation_reviews": {}}},
            step_harness_overlay={"default": {"implementation_reviews": {"implement": "pi"}}},
        )
    )
    view_pi = render_api_workflow_catalog(catalog, _resolver_factory(store_pi))
    _status_pi, payload_pi = _decode(view_pi(qs={}))
    impl_pi = next(
        w for w in payload_pi["workflows"] if w["workflow_id"] == "implementation_reviews"
    )
    implement_pi = next(s for s in impl_pi["steps"] if s["step"] == "implement")
    assert implement_pi["default_harness"] == "codex"
    assert implement_pi["harness"] == "pi"
    assert implement_pi["harness_overridden"] is True
    assert implement_pi["effective_profile"] == "pi-implementation-standard"
    assert implement_pi["is_overridden"] is True


# ---------------------------------------------------------------------------
# 3. Detail 200/404/400-bad-id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("workflow_id", "expected_status", "expected_error"),
    [
        pytest.param("implementation_reviews", 200, None, id="detail-known-workflow-200"),
        pytest.param("nope", 404, "not_found", id="detail-unknown-workflow-404"),
        pytest.param("../etc", 404, "not_found", id="detail-traversal-id-404"),
    ],
)
def test_catalog_detail(
    tmp_path: Path, workflow_id: str, expected_status: int, expected_error: str | None
) -> None:
    store = _store(tmp_path)
    catalog = governed_workflow_catalog()
    view = render_api_workflow_catalog_detail(catalog, _resolver_factory(store))

    status, payload = _decode(view(workflow_id=workflow_id, qs={}))

    assert status == expected_status
    if expected_status == 200:
        assert payload["workflow_id"] == "implementation_reviews"
        assert len(payload["steps"]) > 0
    else:
        assert payload["error"] == expected_error


# ---------------------------------------------------------------------------
# 4. Profiles registry + full pi model set incl. kimi label
# ---------------------------------------------------------------------------


def test_profiles_registry_and_pi_model_choices() -> None:
    view = render_api_workflow_model_profiles()
    status, payload = _decode(view())

    assert status == 200
    ids = {p["id"] for p in payload["profiles"]}
    assert "codex-implementation-standard" in ids
    assert "pi-reasoning-high" in ids

    choices = payload["model_choices"]
    assert "pi" in choices and "codex" in choices

    pi_values = [c["value"] for c in choices["pi"]]
    assert "moonshotai/kimi-k2.5:high" in pi_values
    assert set(pi_values) == {
        "openai-codex/gpt-5.3-codex-spark:high",
        "openai-codex/gpt-5.3-codex-spark:low",
        "openai-codex/gpt-5.3-codex-spark:medium",
        "moonshotai/kimi-k2.5:high",
    }

    kimi = next(c for c in choices["pi"] if c["value"] == "moonshotai/kimi-k2.5:high")
    assert kimi["label"] == "OpenRouter — moonshotai/kimi-k2.5 (high)"

    gpt = next(c for c in choices["pi"] if c["value"] == "openai-codex/gpt-5.3-codex-spark:high")
    assert gpt["label"] == "openai-codex/gpt-5.3-codex-spark (high)"
    assert "moonshotai/kimi-k2.5:high" not in [c["value"] for c in choices["codex"]]


# ---------------------------------------------------------------------------
# 5. Policy GET states + lifecycle-runs snapshot/filters + step-ledger
#    metadata-only + ledger filters
# ---------------------------------------------------------------------------


def _run_with_snapshot(
    run_id: str, *, profile: str, workflow_id: str = "implementation_reviews"
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
                model="gpt-5.3-codex-spark",
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


def test_policy_state_and_runs_and_ledger(tmp_path: Path) -> None:
    # (a) Policy GET: missing overlay -> empty default at 200 (missing != invalid).
    store = _store(tmp_path)
    view_policy = render_api_workflow_model_policy(store)
    status_missing, payload_missing = _decode(view_policy(qs={}))
    assert status_missing == 200
    assert payload_missing["exists"] is False
    assert payload_missing["policy"]["contexts"]["default"]["workflows"] == {}

    # (b) Policy GET: persisted overlay round-trips verbatim.
    store.save(
        WorkflowModelPolicyOverlay(
            policy_id="default",
            contexts={"default": {"implementation_reviews": {"implement": "codex-review-deep"}}},
        )
    )
    status_persisted, payload_persisted = _decode(view_policy(qs={}))
    assert status_persisted == 200
    assert payload_persisted["exists"] is True
    steps = payload_persisted["policy"]["contexts"]["default"]["workflows"][
        "implementation_reviews"
    ]["steps"]
    assert steps["implement"] == "codex-review-deep"

    # (c) Policy GET: invalid JSON on disk -> 409.
    store_bad = _store(tmp_path / "bad")
    store_bad.path.parent.mkdir(parents=True, exist_ok=True)
    store_bad.path.write_text("{not json", encoding="utf-8")
    view_bad = render_api_workflow_model_policy(store_bad)
    status_bad, payload_bad = _decode(view_bad(qs={}))
    assert status_bad == 409
    assert payload_bad["error"] == "invalid_policy"

    # (d) Lifecycle-runs: persisted snapshot is read verbatim, never re-resolved.
    run_store = JsonLifecycleRunStore(_workspace(tmp_path / "runs"))
    run_store.save(_run_with_snapshot("run-1", profile="codex-implementation-standard"))
    view_runs = render_api_lifecycle_runs(run_store)
    status_runs, payload_runs = _decode(view_runs(qs={}))
    assert status_runs == 200
    assert len(payload_runs["runs"]) == 1
    snap = payload_runs["runs"][0]["workflow_policy"]
    assert snap["steps"][0]["model_profile"] == "codex-implementation-standard"

    # (e) Lifecycle-runs: filters by workflow and context.
    run_store.save(
        _run_with_snapshot("run-b", profile="codex-review-deep", workflow_id="release_definition")
    )
    status_wf, payload_wf = _decode(view_runs(qs={"workflow": ["implementation_reviews"]}))
    assert status_wf == 200
    assert [r["run_id"] for r in payload_wf["runs"]] == ["run-1"]
    status_ctx, payload_ctx = _decode(view_runs(qs={"context": ["other-ctx"]}))
    assert status_ctx == 200
    assert payload_ctx["runs"] == []

    # (f) Step ledger: metadata-only exposure — NO payload body leak.
    ledger_store = JsonLifecycleRunStore(_workspace(tmp_path / "ledger"))
    ledger_store.save(_run_with_ledger("led-1"))
    view_ledger = render_api_workflow_step_ledger(ledger_store)
    status_ledger, payload_ledger = _decode(view_ledger(qs={}))
    assert status_ledger == 200
    assert len(payload_ledger["runs"]) == 1
    ledger_steps = payload_ledger["runs"][0]["workflow_steps"]
    assert len(ledger_steps) == 1
    record = ledger_steps[0]
    assert record["producer_step"] == "release_scope"
    assert record["payload_ref"].endswith(".step-payload.json")
    assert record["content_hash"] == "a" * 64
    assert "payload" not in record
    assert '"payload"' not in json.dumps(payload_ledger)

    # (g) Step ledger: filters by run and context.
    ledger_store.save(_run_with_ledger("led-b"))
    status_run_filter, payload_run_filter = _decode(view_ledger(qs={"run": ["led-1"]}))
    assert status_run_filter == 200
    assert [r["run_id"] for r in payload_run_filter["runs"]] == ["led-1"]
    status_ledger_ctx, payload_ledger_ctx = _decode(view_ledger(qs={"context": ["other-ctx"]}))
    assert status_ledger_ctx == 200
    assert payload_ledger_ctx["runs"] == []
