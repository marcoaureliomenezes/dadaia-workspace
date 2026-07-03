"""Unit tests for the workflow-model-policy governance doctor (T-28-D-02).

The doctor keeps the governance layer from rotting (AC-10). It owns a single home
(``features/lifecycle/policy_doctor.py``) and a single invariant-id namespace (``WMP-*``,
mirroring the ``BL-*`` backlog-doctor style). The checks:

* WMP-1 — every workflow id unique in the governed catalog.
* WMP-2 — every step id unique within a workflow.
* WMP-3 — every governed step has a default profile per supported harness that resolves
  and whose harness matches.
* WMP-4 — every fragment id a governed step references resolves via the FragmentLoader.
* WMP-5 — every governed step that runs a worker declares a non-empty output schema, and
  each referenced fragment declares one too.
* WMP-6 — every persisted overlay override references an existing workflow/step/profile
  with a matching harness; an invalid overlay file fails actionably (never crashes).
* WMP-7 — no ``claude``/``opencode`` Layer-2 residue in any built-in profile or governed
  catalog step.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.lifecycle.policy_doctor import (
    Finding,
    PolicyDoctorCode,
    Severity,
    run_policy_doctor,
)
from dadaia_workspace.features.lifecycle.policy_resolver import (
    CatalogStep,
    CatalogWorkflow,
    WorkflowCatalog,
)
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write_overlay(workspace: Path, payload: object) -> None:
    path = workspace / ".dadaia" / "states" / "workflow_model_policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


def _doctor(workspace: Path, *, catalog: WorkflowCatalog | None = None) -> list[Finding]:
    """Run the WMP doctor with the real JSON overlay store injected (FR1a).

    The doctor no longer constructs the store itself (the container/CLI injects it); tests
    compose the real :class:`JsonWorkflowModelPolicyStore` rooted at the fixture workspace so
    the on-disk overlay under ``.dadaia/states/`` is loaded exactly as production does.
    """
    store = JsonWorkflowModelPolicyStore(workspace)
    return run_policy_doctor(store=store, catalog=catalog)


# ---------------------------------------------------------------------------
# Clean tree
# ---------------------------------------------------------------------------


def test_clean_tree_no_overlay_passes(tmp_path: Path) -> None:
    """The built-in catalog + profiles + no overlay must produce zero ERROR findings."""
    workspace = _workspace(tmp_path)
    findings = _doctor(workspace)
    errors = [f for f in findings if f.severity is Severity.ERROR]
    assert errors == [], [f.to_dict() for f in errors]


# ---------------------------------------------------------------------------
# WMP-6 — overlay overrides
# ---------------------------------------------------------------------------


def test_overlay_unknown_step_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_overlay(
        workspace,
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {
                        "implementation": {"steps": {"no_such_step": "codex-review-deep"}}
                    }
                }
            },
        },
    )
    findings = _doctor(workspace)
    codes = {f.code for f in findings if f.severity is Severity.ERROR}
    assert PolicyDoctorCode.WMP_OVERLAY in codes
    msg = " ".join(f.message for f in findings if f.code is PolicyDoctorCode.WMP_OVERLAY)
    assert "no_such_step" in msg


def test_overlay_harness_mismatch_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    # implement resolves to a codex step by default; a pi profile mismatches its harness.
    _write_overlay(
        workspace,
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {
                        "implementation": {"steps": {"implement": "pi-implementation-standard"}}
                    }
                }
            },
        },
    )
    findings = _doctor(workspace)
    assert PolicyDoctorCode.WMP_OVERLAY in {
        f.code for f in findings if f.severity is Severity.ERROR
    }


def test_overlay_unknown_profile_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_overlay(
        workspace,
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {"implement": "not-a-profile"}}}
                }
            },
        },
    )
    findings = _doctor(workspace)
    assert PolicyDoctorCode.WMP_OVERLAY in {
        f.code for f in findings if f.severity is Severity.ERROR
    }


def test_valid_overlay_passes(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_overlay(
        workspace,
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {"implement": "codex-review-deep"}}}
                }
            },
        },
    )
    findings = _doctor(workspace)
    assert [f for f in findings if f.severity is Severity.ERROR] == []


# ---------------------------------------------------------------------------
# WMP-8 — invalid state file does not crash
# ---------------------------------------------------------------------------


def test_invalid_policy_json_is_actionable_error_not_crash(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    path = workspace / ".dadaia" / "states" / "workflow_model_policy.json"
    path.write_text("{ this is not json", encoding="utf-8")
    findings = _doctor(workspace)  # must not raise
    overlay_errors = [
        f for f in findings if f.code is PolicyDoctorCode.WMP_STATE and f.severity is Severity.ERROR
    ]
    assert overlay_errors
    assert (
        "invalid" in overlay_errors[0].message.lower()
        or "json" in overlay_errors[0].message.lower()
    )


def test_unknown_top_level_field_is_actionable_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_overlay(
        workspace,
        {"schema_version": "workflow-model-policy-v1", "bogus": 1, "contexts": {}},
    )
    findings = _doctor(workspace)
    assert PolicyDoctorCode.WMP_STATE in {f.code for f in findings if f.severity is Severity.ERROR}


# ---------------------------------------------------------------------------
# WMP-1/2/3/4/5/7 — catalog/profile invariants on the real built-in catalog
# ---------------------------------------------------------------------------


def test_catalog_invariants_hold_on_builtins(tmp_path: Path) -> None:
    """The real governed catalog + built-in profiles satisfy WMP-1..5 and WMP-7."""
    workspace = _workspace(tmp_path)
    findings = _doctor(workspace)
    bad = {
        PolicyDoctorCode.WMP_WORKFLOW_ID,
        PolicyDoctorCode.WMP_STEP_ID,
        PolicyDoctorCode.WMP_PROFILE,
        PolicyDoctorCode.WMP_FRAGMENT,
        PolicyDoctorCode.WMP_OUTPUT_SCHEMA,
        PolicyDoctorCode.WMP_LAYER2_RESIDUE,
    }
    offending = [f for f in findings if f.code in bad and f.severity is Severity.ERROR]
    assert offending == [], [f.to_dict() for f in offending]


def test_to_dict_round_trip(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    findings = _doctor(workspace)
    for f in findings:
        d = f.to_dict()
        assert set(d) >= {"code", "severity", "message"}
        assert d["code"].startswith("WMP-")


# ---------------------------------------------------------------------------
# Fixture-driven proof the catalog checks actually bite (deliberately broken catalogs)
# ---------------------------------------------------------------------------


def _step(
    label: str, *, harness: str, profile: str, schema: str | None = "agent-run-result-v1"
) -> CatalogStep:
    return CatalogStep(
        label=label,
        role="software-engineer",
        default_harness=harness,
        default_profile=profile,
        fragments=(),
        output_schema=schema,
    )


def test_duplicate_workflow_id_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    wf = CatalogWorkflow(
        workflow_id="dup",
        steps=(_step("a", harness="codex", profile="codex-review-deep"),),
    )
    broken = WorkflowCatalog(workflows=(wf, wf))
    findings = _doctor(workspace, catalog=broken)
    assert PolicyDoctorCode.WMP_WORKFLOW_ID in {f.code for f in findings}


def test_duplicate_step_id_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(
            _step("same", harness="codex", profile="codex-review-deep"),
            _step("same", harness="codex", profile="codex-review-deep"),
        ),
    )
    findings = _doctor(workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_STEP_ID in {f.code for f in findings}


def test_claude_harness_residue_in_catalog_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(_step("a", harness="claude", profile="codex-review-deep"),),
    )
    findings = _doctor(workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_LAYER2_RESIDUE in {f.code for f in findings}


def test_opencode_harness_residue_in_catalog_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(_step("a", harness="opencode", profile="codex-review-deep"),),
    )
    findings = _doctor(workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_LAYER2_RESIDUE in {f.code for f in findings}


def test_fragment_driven_step_missing_output_schema_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    step = CatalogStep(
        label="a",
        role="software-engineer",
        default_harness="codex",
        default_profile="codex-review-deep",
        fragments=("implementation.implement_tdd",),
        output_schema=None,
    )
    wf = CatalogWorkflow(workflow_id="w", steps=(step,))
    findings = _doctor(workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_OUTPUT_SCHEMA in {f.code for f in findings}


def test_generic_step_without_fragments_no_output_schema_obligation(tmp_path: Path) -> None:
    """A not-yet-fragment-migrated worker step (no fragments) is not WMP-5-flagged."""
    workspace = _workspace(tmp_path)
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(_step("a", harness="codex", profile="codex-review-deep", schema=None),),
    )
    findings = _doctor(workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_OUTPUT_SCHEMA not in {f.code for f in findings}


def test_default_profile_harness_mismatch_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    # pi profile declared as default for a codex step.
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(_step("a", harness="codex", profile="pi-implementation-standard"),),
    )
    findings = _doctor(workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_PROFILE in {f.code for f in findings}


def test_unresolved_fragment_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    step = CatalogStep(
        label="a",
        role="software-engineer",
        default_harness="codex",
        default_profile="codex-review-deep",
        fragments=("nonexistent.fragment",),
        output_schema="agent-run-result-v1",
    )
    wf = CatalogWorkflow(workflow_id="w", steps=(step,))
    findings = _doctor(workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_FRAGMENT in {f.code for f in findings}


# ---------------------------------------------------------------------------
# T-29-D-01 — the harness dimension (v0.1.29). An overlay can now override a
# step's harness; the doctor must validate it through the same shared resolver.
# ---------------------------------------------------------------------------


def _harness_overlay(workflow: str, *, step: str, harness: str) -> dict[str, object]:
    """A persisted overlay that only overrides a step's harness (no profile override)."""
    return {
        "schema_version": "workflow-model-policy-v1",
        "policy_id": "default",
        "contexts": {
            "default": {"workflows": {workflow: {"harnesses": {step: harness}}}},
        },
    }


def test_overlay_step_harness_pi_resolves_via_auto_profile(tmp_path: Path) -> None:
    """A harness-only overlay (pi) on a step with a pi default profile is valid (auto-profile)."""
    workspace = _workspace(tmp_path)
    _write_overlay(workspace, _harness_overlay("implementation", step="implement", harness="pi"))
    findings = _doctor(workspace)
    assert [f for f in findings if f.severity is Severity.ERROR] == [], [
        f.to_dict() for f in findings if f.severity is Severity.ERROR
    ]


# Layering (T-29-D-01): a FORBIDDEN Layer-2 harness (claude/opencode) in an overlay is
# rejected one layer earlier than the doctor's resolver check — at STORE LOAD, by the
# overlay schema/parse enum (harness in {codex,pi}). It therefore surfaces as a WMP-STATE
# error (an invalid/unloadable overlay), not WMP-OVERLAY/WMP-LAYER2-RESIDUE. The invariant
# the doctor must uphold is: a forbidden Layer-2 harness in the overlay is a HARD ERROR and
# never silently passes — regardless of which WMP code reports it. The resolver-level
# WMP-OVERLAY check still guards the residual paths the schema does NOT constrain (an unknown
# workflow/step harness override, or a valid harness with no step default profile), proven by
# the unknown-workflow test below + the valid-pi auto-profile test above.
_FORBIDDEN_HARNESS_CODES = {
    PolicyDoctorCode.WMP_STATE,
    PolicyDoctorCode.WMP_OVERLAY,
    PolicyDoctorCode.WMP_LAYER2_RESIDUE,
}


def test_overlay_step_harness_forbidden_layer2_is_hard_error(tmp_path: Path) -> None:
    """An overlay step-harness naming a forbidden Layer-2 harness (claude) is a hard error."""
    workspace = _workspace(tmp_path)
    _write_overlay(
        workspace, _harness_overlay("implementation", step="implement", harness="claude")
    )
    findings = _doctor(workspace)  # must not raise
    codes = {f.code for f in findings if f.severity is Severity.ERROR}
    assert codes & _FORBIDDEN_HARNESS_CODES, (
        "a forbidden Layer-2 step harness in the overlay must be a hard doctor error, "
        f"got {[c.value for c in codes]}"
    )


def test_overlay_default_harness_forbidden_layer2_is_hard_error(tmp_path: Path) -> None:
    """A forbidden default_harness (claude) is caught as a hard error (schema → WMP-STATE)."""
    workspace = _workspace(tmp_path)
    _write_overlay(
        workspace,
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {"workflows": {"implementation": {"default_harness": "claude"}}},
            },
        },
    )
    findings = _doctor(workspace)  # must not raise
    codes = {f.code for f in findings if f.severity is Severity.ERROR}
    assert codes & _FORBIDDEN_HARNESS_CODES, (
        "a forbidden Layer-2 default harness must be a hard doctor error, "
        f"got {[c.value for c in codes]}"
    )


def test_overlay_harness_unknown_workflow_is_error(tmp_path: Path) -> None:
    """A harness override targeting a workflow not in the governed catalog is flagged."""
    workspace = _workspace(tmp_path)
    _write_overlay(workspace, _harness_overlay("ghost", step="implement", harness="pi"))
    findings = _doctor(workspace)
    msg = " ".join(f.message for f in findings if f.code is PolicyDoctorCode.WMP_OVERLAY)
    assert "ghost" in msg


def test_persona_resolution_clean_tree_no_persona_findings(tmp_path: Path) -> None:
    """WMP-PERSONA (AC-4): the shipped catalog produces zero persona-resolution findings."""
    workspace = _workspace(tmp_path)
    findings = _doctor(workspace)
    persona = [f for f in findings if f.code is PolicyDoctorCode.WMP_PERSONA]
    assert persona == [], [f.to_dict() for f in persona]


def test_doctor_surfaces_persona_resolution_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A model-driven step whose role resolves to project-manager / no persona atom is
    surfaced by the aggregated doctor as a WMP-PERSONA ERROR (AC-4 anti-regression)."""
    from dadaia_workspace.features.lifecycle import persona_doctor

    monkeypatch.setattr(
        persona_doctor,
        "model_driven_step_roles",
        lambda: {"ghost.pm_step": "project-manager", "ghost.dangling": "no-such-persona"},
    )
    workspace = _workspace(tmp_path)
    findings = _doctor(workspace)  # must not raise
    persona = [f for f in findings if f.code is PolicyDoctorCode.WMP_PERSONA]
    assert len(persona) == 2, [f.to_dict() for f in findings]
    assert all(f.severity is Severity.ERROR for f in persona)
    joined = " ".join(f.message for f in persona)
    assert "project-manager" in joined
    assert "no-such-persona" in joined


def test_completed_catalog_with_closure_passes_all_wmp(tmp_path: Path) -> None:
    """T-29-D-01 (AC-8): WMP-1..WMP-7 pass over the completed catalog (closure added)."""
    workspace = _workspace(tmp_path)
    findings = _doctor(workspace)
    errors = [f for f in findings if f.severity is Severity.ERROR]
    assert errors == [], [f.to_dict() for f in errors]
    # And closure is actually in the governed catalog the doctor validated.
    from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog

    assert governed_workflow_catalog().workflow("closure") is not None
