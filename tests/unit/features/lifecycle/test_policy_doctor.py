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

from dadaia_workspace.features.lifecycle.policy_doctor import (
    PolicyDoctorCode,
    Severity,
    run_policy_doctor,
)
from dadaia_workspace.features.lifecycle.policy_resolver import (
    CatalogStep,
    CatalogWorkflow,
    WorkflowCatalog,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write_overlay(workspace: Path, payload: object) -> None:
    path = workspace / ".dadaia" / "states" / "workflow_model_policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# Clean tree
# ---------------------------------------------------------------------------


def test_clean_tree_no_overlay_passes(tmp_path: Path) -> None:
    """The built-in catalog + profiles + no overlay must produce zero ERROR findings."""
    workspace = _workspace(tmp_path)
    findings = run_policy_doctor(workspace_root=workspace)
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
    findings = run_policy_doctor(workspace_root=workspace)
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
    findings = run_policy_doctor(workspace_root=workspace)
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
    findings = run_policy_doctor(workspace_root=workspace)
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
    findings = run_policy_doctor(workspace_root=workspace)
    assert [f for f in findings if f.severity is Severity.ERROR] == []


# ---------------------------------------------------------------------------
# WMP-8 — invalid state file does not crash
# ---------------------------------------------------------------------------


def test_invalid_policy_json_is_actionable_error_not_crash(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    path = workspace / ".dadaia" / "states" / "workflow_model_policy.json"
    path.write_text("{ this is not json", encoding="utf-8")
    findings = run_policy_doctor(workspace_root=workspace)  # must not raise
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
    findings = run_policy_doctor(workspace_root=workspace)
    assert PolicyDoctorCode.WMP_STATE in {f.code for f in findings if f.severity is Severity.ERROR}


# ---------------------------------------------------------------------------
# WMP-1/2/3/4/5/7 — catalog/profile invariants on the real built-in catalog
# ---------------------------------------------------------------------------


def test_catalog_invariants_hold_on_builtins(tmp_path: Path) -> None:
    """The real governed catalog + built-in profiles satisfy WMP-1..5 and WMP-7."""
    workspace = _workspace(tmp_path)
    findings = run_policy_doctor(workspace_root=workspace)
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
    findings = run_policy_doctor(workspace_root=workspace)
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
    findings = run_policy_doctor(workspace_root=workspace, catalog=broken)
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
    findings = run_policy_doctor(workspace_root=workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_STEP_ID in {f.code for f in findings}


def test_claude_harness_residue_in_catalog_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(_step("a", harness="claude", profile="codex-review-deep"),),
    )
    findings = run_policy_doctor(workspace_root=workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_LAYER2_RESIDUE in {f.code for f in findings}


def test_opencode_harness_residue_in_catalog_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(_step("a", harness="opencode", profile="codex-review-deep"),),
    )
    findings = run_policy_doctor(workspace_root=workspace, catalog=WorkflowCatalog(workflows=(wf,)))
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
    findings = run_policy_doctor(workspace_root=workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_OUTPUT_SCHEMA in {f.code for f in findings}


def test_generic_step_without_fragments_no_output_schema_obligation(tmp_path: Path) -> None:
    """A not-yet-fragment-migrated worker step (no fragments) is not WMP-5-flagged."""
    workspace = _workspace(tmp_path)
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(_step("a", harness="codex", profile="codex-review-deep", schema=None),),
    )
    findings = run_policy_doctor(workspace_root=workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_OUTPUT_SCHEMA not in {f.code for f in findings}


def test_default_profile_harness_mismatch_is_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    # pi profile declared as default for a codex step.
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(_step("a", harness="codex", profile="pi-implementation-standard"),),
    )
    findings = run_policy_doctor(workspace_root=workspace, catalog=WorkflowCatalog(workflows=(wf,)))
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
    findings = run_policy_doctor(workspace_root=workspace, catalog=WorkflowCatalog(workflows=(wf,)))
    assert PolicyDoctorCode.WMP_FRAGMENT in {f.code for f in findings}
