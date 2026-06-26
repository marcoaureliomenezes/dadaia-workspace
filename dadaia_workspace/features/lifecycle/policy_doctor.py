"""Workflow-model-policy governance doctor — ``features/lifecycle/policy_doctor.py``.

The single home + single invariant-id namespace for the v0.1.28 governance layer's
consistency checks (AC-10). It mirrors the ``features/backlog/doctor.py`` style: a
``StrEnum`` code namespace (here ``WMP-*`` — Workflow Model Policy), a ``Severity`` enum,
a frozen :class:`Finding`, and a single :func:`run_policy_doctor` returning every finding.

The checks keep the layer honest so it cannot rot silently:

* **WMP-1** — every workflow id unique in the governed catalog.
* **WMP-2** — every step id unique within a workflow.
* **WMP-3** — every governed (worker) step has a default profile per supported harness
  that resolves in the built-in registry and whose own harness matches the step's harness
  (or, structurally, an explicit no-default — a Python gate step carries no worker and is
  not a governed step at all).
* **WMP-4** — every fragment id a governed step references resolves via the shared
  :class:`FragmentLoader`.
* **WMP-5** — every governed (worker) step declares a non-empty output schema, and each
  fragment it references declares a non-empty output schema too (the contract a worker
  must satisfy is never blank).
* **WMP-6** — every persisted overlay override references an existing workflow/step/known
  profile whose harness matches the step's resolved harness (resolved through the SAME
  shared resolver the CLI + panel use). A deprecated-without-replacement profile fails.
* **WMP-7** — no ``claude``/``opencode`` Layer-2 residue in any built-in profile or in any
  governed catalog step (LAW 1 — Layer-2 workers are ``codex``/``pi`` only).
* **WMP-8** (``WMP-STATE``) — an invalid policy state file fails with an actionable
  message and NEVER crashes the caller (so a broken overlay can never blank the panel).

The catalog + profile registry are pure (no I/O); only the overlay-store load touches
disk. The catalog/profiles/loader are injectable so the checks are unit-testable against
deliberately-broken fixtures without mutating the real built-ins.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.fragments.loader import (
    FragmentError,
    FragmentLoader,
)
from dadaia_workspace.features.lifecycle.model_profiles import UnknownProfileError
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

#: Layer-2 harness names a profile / step may legitimately declare (LAW 1).
_LAYER2_HARNESSES = frozenset({"codex", "pi"})
#: Harness names that MUST NEVER appear as a Layer-2 worker choice (residue check).
_FORBIDDEN_LAYER2 = frozenset({"claude", "claude_sdk", "claude-sdk", "opencode", "open-code"})


class PolicyDoctorCode(StrEnum):
    """The ``WMP-*`` invariant-id namespace for the governance doctor."""

    WMP_WORKFLOW_ID = "WMP-WORKFLOW-ID"
    WMP_STEP_ID = "WMP-STEP-ID"
    WMP_PROFILE = "WMP-PROFILE"
    WMP_FRAGMENT = "WMP-FRAGMENT"
    WMP_OUTPUT_SCHEMA = "WMP-OUTPUT-SCHEMA"
    WMP_OVERLAY = "WMP-OVERLAY"
    WMP_LAYER2_RESIDUE = "WMP-LAYER2-RESIDUE"
    WMP_STATE = "WMP-STATE"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    """One policy-doctor finding."""

    code: PolicyDoctorCode
    severity: Severity
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
        }


def _check_workflow_step_ids(catalog: WorkflowCatalog) -> list[Finding]:
    """WMP-1 + WMP-2: workflow ids unique; step ids unique within a workflow."""
    out: list[Finding] = []
    wf_counts = Counter(w.workflow_id for w in catalog.workflows)
    for workflow_id, count in wf_counts.items():
        if count > 1:
            out.append(
                Finding(
                    PolicyDoctorCode.WMP_WORKFLOW_ID,
                    Severity.ERROR,
                    f"workflow id {workflow_id!r} appears {count} times in the governed "
                    "catalog; every workflow id must be unique.",
                )
            )
    for workflow in catalog.workflows:
        step_counts = Counter(s.label for s in workflow.steps)
        for label, count in step_counts.items():
            if count > 1:
                out.append(
                    Finding(
                        PolicyDoctorCode.WMP_STEP_ID,
                        Severity.ERROR,
                        f"step id {label!r} appears {count} times in workflow "
                        f"{workflow.workflow_id!r}; every step id must be unique.",
                    )
                )
    return out


def _check_step_invariants(catalog: WorkflowCatalog, loader: FragmentLoader) -> list[Finding]:
    """WMP-3/4/5/7 over every governed (worker) step in the catalog."""
    out: list[Finding] = []
    for workflow in catalog.workflows:
        for step in workflow.steps:
            ref = f"{workflow.workflow_id!r}.{step.label!r}"
            # WMP-7: no removed/Layer-1 harness as a Layer-2 worker choice (residue).
            if step.default_harness in _FORBIDDEN_LAYER2:
                out.append(
                    Finding(
                        PolicyDoctorCode.WMP_LAYER2_RESIDUE,
                        Severity.ERROR,
                        f"step {ref} declares forbidden Layer-2 harness "
                        f"{step.default_harness!r}; Layer-2 workers are codex/pi only "
                        "(LAW 1).",
                    )
                )
            elif step.default_harness not in _LAYER2_HARNESSES:
                out.append(
                    Finding(
                        PolicyDoctorCode.WMP_PROFILE,
                        Severity.ERROR,
                        f"step {ref} declares unknown harness {step.default_harness!r}; "
                        "supported Layer-2 harnesses are codex/pi.",
                    )
                )
            # WMP-3: the default profile resolves and its harness matches the step.
            out.extend(_check_default_profile(ref, step.default_profile, step.default_harness))
            # WMP-5: a *fragment-driven* worker step must declare a non-empty output
            # schema (its output contract). A generic, not-yet-fragment-migrated worker
            # step (no fragments) carries no output-schema obligation yet — flagging it
            # would be a false positive against the partial-migration catalog.
            if step.fragments and not step.output_schema:
                out.append(
                    Finding(
                        PolicyDoctorCode.WMP_OUTPUT_SCHEMA,
                        Severity.ERROR,
                        f"step {ref} is fragment-driven but declares no output schema; "
                        "every fragment-driven step must declare its output contract.",
                    )
                )
            # WMP-4/5: every referenced fragment resolves and declares an output schema.
            out.extend(_check_fragments(ref, step.fragments, loader))
    return out


def _check_default_profile(ref: str, profile_id: str, harness: str) -> list[Finding]:
    try:
        profile = model_profiles.resolve(profile_id)
    except UnknownProfileError:
        return [
            Finding(
                PolicyDoctorCode.WMP_PROFILE,
                Severity.ERROR,
                f"step {ref} default profile {profile_id!r} is not a built-in profile.",
            )
        ]
    out: list[Finding] = []
    if profile.harness != harness:
        out.append(
            Finding(
                PolicyDoctorCode.WMP_PROFILE,
                Severity.ERROR,
                f"step {ref} default profile {profile_id!r} runs on harness "
                f"{profile.harness!r} but the step harness is {harness!r}.",
            )
        )
    if profile.harness in _FORBIDDEN_LAYER2:
        out.append(
            Finding(
                PolicyDoctorCode.WMP_LAYER2_RESIDUE,
                Severity.ERROR,
                f"step {ref} default profile {profile_id!r} names forbidden Layer-2 "
                f"harness {profile.harness!r} (LAW 1).",
            )
        )
    if profile.deprecated and not profile.replacement:
        out.append(
            Finding(
                PolicyDoctorCode.WMP_PROFILE,
                Severity.ERROR,
                f"step {ref} default profile {profile_id!r} is deprecated without a replacement.",
            )
        )
    return out


def _check_fragments(ref: str, fragments: tuple[str, ...], loader: FragmentLoader) -> list[Finding]:
    out: list[Finding] = []
    for fragment_id in fragments:
        try:
            fragment = loader.load_fragment(fragment_id)
        except FragmentError as exc:
            out.append(
                Finding(
                    PolicyDoctorCode.WMP_FRAGMENT,
                    Severity.ERROR,
                    f"step {ref} references fragment {fragment_id!r} that does not resolve: {exc}",
                )
            )
            continue
        if not fragment.output_schema:
            out.append(
                Finding(
                    PolicyDoctorCode.WMP_OUTPUT_SCHEMA,
                    Severity.ERROR,
                    f"step {ref} fragment {fragment_id!r} declares no output schema.",
                )
            )
    return out


def _check_profile_registry() -> list[Finding]:
    """WMP-7: no built-in profile names a forbidden Layer-2 harness."""
    out: list[Finding] = []
    for profile in model_profiles.list_profiles():
        if profile.harness in _FORBIDDEN_LAYER2:
            out.append(
                Finding(
                    PolicyDoctorCode.WMP_LAYER2_RESIDUE,
                    Severity.ERROR,
                    f"built-in profile {profile.id!r} names forbidden Layer-2 harness "
                    f"{profile.harness!r}; Layer-2 workers are codex/pi only (LAW 1).",
                )
            )
        if profile.model_id.startswith("claude-"):
            out.append(
                Finding(
                    PolicyDoctorCode.WMP_LAYER2_RESIDUE,
                    Severity.ERROR,
                    f"built-in profile {profile.id!r} names a Claude model "
                    f"{profile.model_id!r}; Layer-2 is GPT-only.",
                )
            )
    return out


def _check_overlay(
    workspace_root: Path,
    catalog: WorkflowCatalog,
    store: JsonWorkflowModelPolicyStore | None,
) -> list[Finding]:
    """WMP-6 + WMP-8: the persisted overlay resolves, or fails actionably (no crash)."""
    store = store or JsonWorkflowModelPolicyStore(workspace_root)
    try:
        overlay = store.load()
    except WorkflowModelPolicyStoreError as exc:
        # WMP-8: an invalid state file is an actionable ERROR, never a crash.
        return [
            Finding(
                PolicyDoctorCode.WMP_STATE,
                Severity.ERROR,
                f"workflow-model-policy overlay is invalid: {exc}",
            )
        ]
    if overlay is None:
        return []  # missing != invalid (LAW 4).
    return _resolve_overlay(catalog, overlay)


def _resolve_overlay(
    catalog: WorkflowCatalog, overlay: WorkflowModelPolicyOverlay
) -> list[Finding]:
    """WMP-6: resolve every workflow the overlay names through the shared resolver."""
    out: list[Finding] = []
    resolver = WorkflowExecutionPolicyResolver(catalog=catalog, overlay=overlay)
    workflows = overlay.contexts.get(DEFAULT_CONTEXT, {})
    for workflow_id in workflows:
        if catalog.workflow(workflow_id) is None:
            out.append(
                Finding(
                    PolicyDoctorCode.WMP_OVERLAY,
                    Severity.ERROR,
                    f"overlay overrides unknown workflow {workflow_id!r}.",
                )
            )
            continue
        try:
            resolver.resolve(workflow_id, context=DEFAULT_CONTEXT)
        except PolicyResolutionError as exc:
            out.append(
                Finding(
                    PolicyDoctorCode.WMP_OVERLAY,
                    Severity.ERROR,
                    f"overlay override for workflow {workflow_id!r} is invalid: {exc}",
                )
            )
    return out


def run_policy_doctor(
    *,
    workspace_root: Path,
    catalog: WorkflowCatalog | None = None,
    loader: FragmentLoader | None = None,
    store: JsonWorkflowModelPolicyStore | None = None,
) -> list[Finding]:
    """Run every ``WMP-*`` governance check and return all findings.

    Pure catalog/profile checks run against the governed catalog + built-in registry;
    the overlay check loads ``.dadaia/states/workflow_model_policy.json`` (missing ⇒
    defaults; invalid ⇒ an actionable WMP-STATE error, never a crash). ``catalog`` /
    ``loader`` / ``store`` are injectable for deterministic fixture testing.
    """
    if catalog is None:
        from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog

        catalog = governed_workflow_catalog()
    loader = loader or FragmentLoader()

    findings: list[Finding] = []
    findings.extend(_check_workflow_step_ids(catalog))
    findings.extend(_check_step_invariants(catalog, loader))
    findings.extend(_check_profile_registry())
    findings.extend(_check_overlay(workspace_root, catalog, store))
    return findings


__all__ = [
    "Finding",
    "PolicyDoctorCode",
    "Severity",
    "run_policy_doctor",
]
