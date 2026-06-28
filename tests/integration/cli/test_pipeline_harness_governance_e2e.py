"""v0.1.29 / T-29-A-08 — PI-as-Layer-2 governed-selection proof (D-5, AC-4/AC-5).

Drives the REAL ``WorkflowExecutionPolicyResolver`` → ``apply_resolved_policy`` →
``LifecyclePipeline`` → ``FakeAgentRuntime`` and proves PI is now selectable as a Layer-2
worker through the governed policy:

- **CLI path (AC-4):** an ``implementation`` run resolved onto PI (``default_harness="pi"``,
  the resolver layer the CLI ``--harness pi`` threads into) resolves PI profiles, threads
  the resolved PI model into each step request, and records ``harness=pi`` on every snapshot
  step entry — asserted through ``FakeAgentRuntime.received_models`` (NOT the adapter kind,
  which is always FAKE) and the persisted run snapshot.
- **Overlay path (AC-5):** the same three assertions hold when the harness change comes from
  a persisted overlay (``default_harness: pi``) with no CLI flag.
- **Default-first / back-compat (AC-10):** no flags + no overlay → every step codex; an
  overlay with no harness fields resolves to the catalog default.

All hermetic: no live provider, tmp workspace only. ``FakeAgentRuntime.runtime_kind()`` is
always FAKE — the proof is on the resolved_model + the snapshot, never the adapter kind.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.lifecycle.pipeline import (
    LifecyclePipeline,
    apply_resolved_policy,
    implementation_ladder,
)
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime

_PI_MODELS = {"gpt-5.3-codex-spark", "gpt-5.5"}


def _init_workspace(path: Path) -> Path:
    states = path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"version": "1", "contexts": []}), encoding="utf-8"
    )
    (path / "repos").mkdir(exist_ok=True)
    return path


def _approving() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="approved",
        artifact_refs=(".dadaia/handoff/dadaia-workspace/step.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _run(workspace: Path, snapshot: object) -> tuple[FakeAgentRuntime, object]:
    recorder = FakeAgentRuntime(result=_approving())
    store = container.build_lifecycle_run_store(workspace)
    pipe = LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.29",
        run_store=store,
        runtime_factory=lambda kind: recorder,  # type: ignore[arg-type, return-value]
        policy_snapshot=snapshot,  # type: ignore[arg-type]
    )
    # The base ladder is built on FAKE (the deterministic test adapter); apply_resolved_policy
    # threads the resolved PI model while preserving FAKE so the fake adapter runs.
    steps = apply_resolved_policy(implementation_ladder(AgentRuntimeKind.FAKE), snapshot)  # type: ignore[arg-type]
    pipe.run("harness-proof", steps)
    return recorder, store.load("harness-proof")


def _assert_all_pi(recorder: FakeAgentRuntime, persisted: object) -> None:
    # (a) every recorded resolved_model is on PI; (b) its model is a PI catalog model.
    models = recorder.received_models
    assert models and all(m is not None for m in models)
    for m in models:
        assert m is not None
        assert m.harness == "pi"
        assert m.model in _PI_MODELS
    # (c) the persisted snapshot records harness=pi for every step.
    assert persisted is not None
    snap = persisted.workflow_policy  # type: ignore[attr-defined]
    assert snap is not None
    for entry in snap.steps:
        assert entry.harness == "pi"
        assert entry.model in _PI_MODELS


# ---------------------------------------------------------------------------
# AC-4 — CLI path (resolver default_harness="pi")
# ---------------------------------------------------------------------------


def test_cli_harness_pi_resolves_pi_end_to_end(tmp_path: Path) -> None:
    workspace = _init_workspace(tmp_path)
    resolver = container.build_workflow_policy_resolver(workspace, context="dadaia-workspace")
    snapshot = resolver.resolve("implementation", context="default", default_harness="pi")

    # Snapshot sanity: implement runs the PI standard profile, reviews the PI deep profile.
    assert snapshot.step("implement").model_profile == "pi-implementation-standard"  # type: ignore[union-attr]
    assert snapshot.step("review_qa").model_profile == "pi-reasoning-high"  # type: ignore[union-attr]

    recorder, persisted = _run(workspace, snapshot)
    _assert_all_pi(recorder, persisted)


def test_cli_flag_harness_pi_show_policy_resolves_pi_per_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-29-C-03 — the real ``dadaia lifecycle pipeline --harness pi --show-policy`` FLAG
    (not just the resolver kwarg) threads through the CLI into the shared resolver, so the
    governed snapshot resolves harness=pi + a PI catalog model for every step.
    ``--show-policy`` resolves + emits the snapshot WITHOUT running an adapter, keeping the
    proof hermetic (no PI binary, no credits)."""
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = CliRunner().invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0.1.29",
            "--harness",
            "pi",
            "--show-policy",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    steps = payload["steps"]
    assert steps, payload
    for entry in steps:
        assert entry["harness"] == "pi", entry
        assert entry["model"] in _PI_MODELS, entry


# ---------------------------------------------------------------------------
# AC-5 — overlay path (default_harness: pi, no CLI flag)
# ---------------------------------------------------------------------------


def test_overlay_default_harness_pi_resolves_pi_end_to_end(tmp_path: Path) -> None:
    workspace = _init_workspace(tmp_path)
    store = container.build_workflow_model_policy_store(workspace)
    overlay = store.parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {"workflows": {"implementation": {"steps": {}, "default_harness": "pi"}}}
            },
        }
    )
    store.save(overlay)

    resolver = container.build_workflow_policy_resolver(workspace, context="dadaia-workspace")
    snapshot = resolver.resolve("implementation", context="default")  # no CLI flag
    recorder, persisted = _run(workspace, snapshot)
    _assert_all_pi(recorder, persisted)


def test_panel_put_default_harness_pi_overlay_drives_execution(tmp_path: Path) -> None:
    """T-29-C-04 — an overlay persisted through the PANEL PUT route (``default_harness: pi``,
    no CLI flag) makes a subsequent ``implementation`` run resolve PI for every step and
    record harness=pi in the snapshot. Proves the panel-persisted overlay actually drives
    execution — the same write path the codex/pi toggle uses (validate → atomic write)."""
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowExecutionPolicyResolver,
    )
    from dadaia_workspace.features.panel.views.workflow_policy import (
        render_put_workflow_model_policy,
    )
    from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog
    from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
        WorkflowModelPolicyOverlay,
    )

    workspace = _init_workspace(tmp_path)
    store = container.build_workflow_model_policy_store(workspace)
    catalog = governed_workflow_catalog()

    def _factory(
        context: str, *, overlay: WorkflowModelPolicyOverlay | None = None
    ) -> WorkflowExecutionPolicyResolver:
        resolved = overlay if overlay is not None else store.load()
        return WorkflowExecutionPolicyResolver(catalog=catalog, overlay=resolved)

    put = render_put_workflow_model_policy(store, _factory)
    body = json.dumps(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {"workflows": {"implementation": {"steps": {}, "default_harness": "pi"}}}
            },
        }
    ).encode("utf-8")
    status, _ct, _payload = put(
        body=body, content_type="application/json", qs={"context": ["default"]}
    )
    assert status == 200, _payload

    # Fresh resolver reads the PUT-persisted overlay from disk — no CLI flag, no in-memory hint.
    resolver = container.build_workflow_policy_resolver(workspace, context="dadaia-workspace")
    snapshot = resolver.resolve("implementation", context="default")
    recorder, persisted = _run(workspace, snapshot)
    _assert_all_pi(recorder, persisted)


def test_overlay_step_harness_pi_only_that_step(tmp_path: Path) -> None:
    workspace = _init_workspace(tmp_path)
    store = container.build_workflow_model_policy_store(workspace)
    overlay = store.parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {}, "harnesses": {"implement": "pi"}}}
                }
            },
        }
    )
    store.save(overlay)
    resolver = container.build_workflow_policy_resolver(workspace, context="dadaia-workspace")
    snapshot = resolver.resolve("implementation", context="default")
    recorder, persisted = _run(workspace, snapshot)

    models = recorder.received_models
    assert models[0] is not None and models[0].harness == "pi"
    assert models[1] is not None and models[1].harness == "codex"
    assert persisted is not None
    snap = persisted.workflow_policy  # type: ignore[attr-defined]
    assert snap.step("implement").harness == "pi"
    assert snap.step("review_qa").harness == "codex"


# ---------------------------------------------------------------------------
# AC-10 — default-first / back-compat
# ---------------------------------------------------------------------------


def test_default_first_no_overlay_no_flag_resolves_codex(tmp_path: Path) -> None:
    workspace = _init_workspace(tmp_path)
    resolver = container.build_workflow_policy_resolver(workspace, context="dadaia-workspace")
    snapshot = resolver.resolve("implementation", context="default")
    recorder, persisted = _run(workspace, snapshot)

    for m in recorder.received_models:
        assert m is not None and m.harness == "codex"
    assert persisted is not None
    for entry in persisted.workflow_policy.steps:  # type: ignore[attr-defined]
        assert entry.harness == "codex"


def test_back_compat_overlay_without_harness_resolves_catalog_default(tmp_path: Path) -> None:
    workspace = _init_workspace(tmp_path)
    store = container.build_workflow_model_policy_store(workspace)
    # A v0.1.28-shaped overlay (profile override only, no harness fields).
    overlay = store.parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {"implement": "codex-review-deep"}}}
                }
            },
        }
    )
    store.save(overlay)
    resolver = container.build_workflow_policy_resolver(workspace, context="dadaia-workspace")
    snapshot = resolver.resolve("implementation", context="default")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.harness == "codex"
    assert impl.model_profile == "codex-review-deep"
