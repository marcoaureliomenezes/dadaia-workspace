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
* WMP-PERSONA (AC-4) — every model-driven step's role resolves to a real persona atom.

CRITICAL: forbidden Layer-2 harness (claude/opencode) is a HARD error at whichever WMP code
reports it — param cases must survive.
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
# Clean tree — zero ERRORs. Absorbs the catalog-invariants / completed-catalog /
# persona-clean / valid-overlay restatements as extra asserts on the same doctor run.
# ---------------------------------------------------------------------------


def test_clean_tree_zero_errors_and_closure_merged(tmp_path: Path) -> None:
    """The built-in catalog + profiles + no overlay must produce zero ERROR findings across
    every WMP invariant (WMP-1..5, WMP-7, WMP-PERSONA), a valid overlay stays clean too, and
    the completed catalog (T-29-D-01 AC-8) includes closure."""
    workspace = _workspace(tmp_path)
    findings = _doctor(workspace)
    errors = [f for f in findings if f.severity is Severity.ERROR]
    assert errors == [], [f.to_dict() for f in errors]

    persona = [f for f in findings if f.code is PolicyDoctorCode.WMP_PERSONA]
    assert persona == [], [f.to_dict() for f in persona]

    for f in findings:
        d = f.to_dict()
        assert set(d) >= {"code", "severity", "message"}
        assert d["code"].startswith("WMP-")

    _write_overlay(
        workspace,
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation_reviews": {"steps": {"implement": "codex-review-deep"}}}
                }
            },
        },
    )
    valid_overlay_findings = _doctor(workspace)
    assert [f for f in valid_overlay_findings if f.severity is Severity.ERROR] == []

    from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog

    implementation = governed_workflow_catalog().workflow("implementation_reviews")
    assert implementation is not None
    assert implementation.step("close") is not None


# ---------------------------------------------------------------------------
# ① overlay-error matrix param: unknown step / unknown profile / harness mismatch /
#    unknown workflow (incl. harness-map-only)
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


@pytest.mark.parametrize(
    "case_id,overlay,expected_substring",
    [
        (
            "unknown-step",
            {
                "schema_version": "workflow-model-policy-v1",
                "policy_id": "default",
                "contexts": {
                    "default": {
                        "workflows": {
                            "implementation_reviews": {"steps": {"no_such_step": "codex-review-deep"}}
                        }
                    }
                },
            },
            "no_such_step",
        ),
        (
            "harness-mismatch",
            {
                "schema_version": "workflow-model-policy-v1",
                "policy_id": "default",
                "contexts": {
                    "default": {
                        "workflows": {
                            "implementation_reviews": {"steps": {"implement": "pi-implementation-standard"}}
                        }
                    }
                },
            },
            None,
        ),
        (
            "unknown-profile",
            {
                "schema_version": "workflow-model-policy-v1",
                "policy_id": "default",
                "contexts": {
                    "default": {
                        "workflows": {"implementation_reviews": {"steps": {"implement": "not-a-profile"}}}
                    }
                },
            },
            None,
        ),
        (
            "unknown-workflow-harness-map",
            _harness_overlay("ghost", step="implement", harness="pi"),
            "ghost",
        ),
    ],
    ids=["unknown-step", "harness-mismatch", "unknown-profile", "unknown-workflow-harness-map"],
)
def test_overlay_error_matrix(
    tmp_path: Path, case_id: str, overlay: dict[str, object], expected_substring: str | None
) -> None:
    workspace = _workspace(tmp_path)
    _write_overlay(workspace, overlay)
    findings = _doctor(workspace)
    assert PolicyDoctorCode.WMP_OVERLAY in {
        f.code for f in findings if f.severity is Severity.ERROR
    }
    if expected_substring is not None:
        msg = " ".join(f.message for f in findings if f.code is PolicyDoctorCode.WMP_OVERLAY)
        assert expected_substring in msg


# ---------------------------------------------------------------------------
# ② state-file hard errors param: invalid JSON no-crash / unknown top-level field /
#    forbidden Layer-2 step harness / forbidden default_harness
# ---------------------------------------------------------------------------

# Layering (T-29-D-01): a FORBIDDEN Layer-2 harness (claude/opencode) in an overlay is
# rejected one layer earlier than the doctor's resolver check — at STORE LOAD, by the
# overlay schema/parse enum (harness in {codex,pi}). It therefore surfaces as a WMP-STATE
# error (an invalid/unloadable overlay), not WMP-OVERLAY/WMP-LAYER2-RESIDUE. The invariant
# the doctor must uphold is: a forbidden Layer-2 harness in the overlay is a HARD ERROR and
# never silently passes — regardless of which WMP code reports it.
_FORBIDDEN_HARNESS_CODES = {
    PolicyDoctorCode.WMP_STATE,
    PolicyDoctorCode.WMP_OVERLAY,
    PolicyDoctorCode.WMP_LAYER2_RESIDUE,
}


@pytest.mark.parametrize(
    "case_id",
    [
        "invalid-json",
        "unknown-top-level-field",
        "forbidden-step-harness",
        "forbidden-default-harness",
    ],
)
def test_state_file_hard_errors_matrix(tmp_path: Path, case_id: str) -> None:
    workspace = _workspace(tmp_path)
    if case_id == "invalid-json":
        path = workspace / ".dadaia" / "states" / "workflow_model_policy.json"
        path.write_text("{ this is not json", encoding="utf-8")
        findings = _doctor(workspace)  # must not raise
        overlay_errors = [
            f
            for f in findings
            if f.code is PolicyDoctorCode.WMP_STATE and f.severity is Severity.ERROR
        ]
        assert overlay_errors
        assert (
            "invalid" in overlay_errors[0].message.lower()
            or "json" in overlay_errors[0].message.lower()
        )
    elif case_id == "unknown-top-level-field":
        _write_overlay(
            workspace,
            {"schema_version": "workflow-model-policy-v1", "bogus": 1, "contexts": {}},
        )
        findings = _doctor(workspace)
        assert PolicyDoctorCode.WMP_STATE in {
            f.code for f in findings if f.severity is Severity.ERROR
        }
    elif case_id == "forbidden-step-harness":
        _write_overlay(
            workspace, _harness_overlay("implementation_reviews", step="implement", harness="claude")
        )
        findings = _doctor(workspace)  # must not raise
        codes = {f.code for f in findings if f.severity is Severity.ERROR}
        assert codes & _FORBIDDEN_HARNESS_CODES, (
            "a forbidden Layer-2 step harness in the overlay must be a hard doctor error, "
            f"got {[c.value for c in codes]}"
        )
    else:  # forbidden-default-harness
        _write_overlay(
            workspace,
            {
                "schema_version": "workflow-model-policy-v1",
                "policy_id": "default",
                "contexts": {
                    "default": {"workflows": {"implementation_reviews": {"default_harness": "claude"}}},
                },
            },
        )
        findings = _doctor(workspace)  # must not raise
        codes = {f.code for f in findings if f.severity is Severity.ERROR}
        assert codes & _FORBIDDEN_HARNESS_CODES, (
            "a forbidden Layer-2 default harness must be a hard doctor error, "
            f"got {[c.value for c in codes]}"
        )


# ---------------------------------------------------------------------------
# ③ broken-catalog bites param over (catalog fixture, WMP code) + generic-step-no-
#    obligation negative
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


def _duplicate_workflow_catalog() -> WorkflowCatalog:
    wf = CatalogWorkflow(
        workflow_id="dup", steps=(_step("a", harness="codex", profile="codex-review-deep"),)
    )
    return WorkflowCatalog(workflows=(wf, wf))


def _duplicate_step_catalog() -> WorkflowCatalog:
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(
            _step("same", harness="codex", profile="codex-review-deep"),
            _step("same", harness="codex", profile="codex-review-deep"),
        ),
    )
    return WorkflowCatalog(workflows=(wf,))


def _claude_residue_catalog() -> WorkflowCatalog:
    wf = CatalogWorkflow(
        workflow_id="w", steps=(_step("a", harness="claude", profile="codex-review-deep"),)
    )
    return WorkflowCatalog(workflows=(wf,))


def _opencode_residue_catalog() -> WorkflowCatalog:
    wf = CatalogWorkflow(
        workflow_id="w", steps=(_step("a", harness="opencode", profile="codex-review-deep"),)
    )
    return WorkflowCatalog(workflows=(wf,))


def _missing_output_schema_catalog() -> WorkflowCatalog:
    step = CatalogStep(
        label="a",
        role="software-engineer",
        default_harness="codex",
        default_profile="codex-review-deep",
        fragments=("implementation.implement_tdd",),
        output_schema=None,
    )
    return WorkflowCatalog(workflows=(CatalogWorkflow(workflow_id="w", steps=(step,)),))


def _profile_harness_mismatch_catalog() -> WorkflowCatalog:
    wf = CatalogWorkflow(
        workflow_id="w",
        steps=(_step("a", harness="codex", profile="pi-implementation-standard"),),
    )
    return WorkflowCatalog(workflows=(wf,))


def _unresolved_fragment_catalog() -> WorkflowCatalog:
    step = CatalogStep(
        label="a",
        role="software-engineer",
        default_harness="codex",
        default_profile="codex-review-deep",
        fragments=("nonexistent.fragment",),
        output_schema="agent-run-result-v1",
    )
    return WorkflowCatalog(workflows=(CatalogWorkflow(workflow_id="w", steps=(step,)),))


_BROKEN_CATALOG_CASES = (
    ("duplicate-workflow-id", _duplicate_workflow_catalog, PolicyDoctorCode.WMP_WORKFLOW_ID),
    ("duplicate-step-id", _duplicate_step_catalog, PolicyDoctorCode.WMP_STEP_ID),
    ("claude-residue", _claude_residue_catalog, PolicyDoctorCode.WMP_LAYER2_RESIDUE),
    ("opencode-residue", _opencode_residue_catalog, PolicyDoctorCode.WMP_LAYER2_RESIDUE),
    ("missing-output-schema", _missing_output_schema_catalog, PolicyDoctorCode.WMP_OUTPUT_SCHEMA),
    ("profile-harness-mismatch", _profile_harness_mismatch_catalog, PolicyDoctorCode.WMP_PROFILE),
    ("unresolved-fragment", _unresolved_fragment_catalog, PolicyDoctorCode.WMP_FRAGMENT),
)


@pytest.mark.parametrize(
    "build_catalog,expected_code",
    [c[1:] for c in _BROKEN_CATALOG_CASES],
    ids=[c[0] for c in _BROKEN_CATALOG_CASES],
)
def test_broken_catalog_bites(
    tmp_path: Path, build_catalog, expected_code: PolicyDoctorCode
) -> None:
    workspace = _workspace(tmp_path)
    findings = _doctor(workspace, catalog=build_catalog())
    assert expected_code in {f.code for f in findings}

    if build_catalog is _missing_output_schema_catalog:
        # Negative control alongside the positive bite above: a not-yet-fragment-migrated
        # worker step (no fragments) is NOT WMP-5-flagged (only the fragment-driven step
        # with a missing schema is).
        control_wf = CatalogWorkflow(
            workflow_id="w",
            steps=(_step("a", harness="codex", profile="codex-review-deep", schema=None),),
        )
        control_findings = _doctor(
            _workspace(tmp_path / "control"), catalog=WorkflowCatalog(workflows=(control_wf,))
        )
        assert PolicyDoctorCode.WMP_OUTPUT_SCHEMA not in {f.code for f in control_findings}


# ---------------------------------------------------------------------------
# ④ pi harness-only overlay auto-profile valid + doctor-surfaces-persona-failure
# ---------------------------------------------------------------------------


def test_pi_harness_only_overlay_auto_profile_valid_and_persona_failure_surfaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A harness-only overlay (pi) on a step with a pi default profile is valid
    (auto-profile), and a model-driven step whose role resolves to project-manager / no
    persona atom is surfaced by the aggregated doctor as a WMP-PERSONA ERROR (AC-4
    anti-regression)."""
    workspace = _workspace(tmp_path)
    _write_overlay(
        workspace, _harness_overlay("implementation_reviews", step="implement", harness="pi")
    )
    findings = _doctor(workspace)
    assert [f for f in findings if f.severity is Severity.ERROR] == [], [
        f.to_dict() for f in findings if f.severity is Severity.ERROR
    ]

    from dadaia_workspace.features.lifecycle import persona_doctor

    monkeypatch.setattr(
        persona_doctor,
        "model_driven_step_roles",
        lambda: {"ghost.pm_step": "project-manager", "ghost.dangling": "no-such-persona"},
    )
    persona_workspace = _workspace(tmp_path / "persona")
    persona_findings = _doctor(persona_workspace)  # must not raise
    persona = [f for f in persona_findings if f.code is PolicyDoctorCode.WMP_PERSONA]
    assert len(persona) == 2, [f.to_dict() for f in persona_findings]
    assert all(f.severity is Severity.ERROR for f in persona)
    joined = " ".join(f.message for f in persona)
    assert "project-manager" in joined
    assert "no-such-persona" in joined
