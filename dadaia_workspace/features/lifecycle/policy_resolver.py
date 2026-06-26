"""The single shared workflow execution-policy resolver — ``policy_resolver.py``.

:class:`WorkflowExecutionPolicyResolver` is **the** seam both the CLI and the panel
consume to turn a workflow id + context + CLI overrides into a frozen
:class:`WorkflowPolicySnapshot`. Resolving once, here, is what guarantees CLI and panel
never disagree on which model a step runs.

**Precedence (per step):** ``CLI override > context overlay > default overlay > library
default``. Only the ``default`` context overlay is honored this release (D-2); a
non-``default`` context resolves to the library default (the overlay store already makes a
non-``default`` key inert). The four sources collapse to two overlay layers in practice
because only ``default`` is honored — but the precedence vocabulary is recorded on the
snapshot for auditability.

**M3 (Wave A independence):** the library step defaults come from
:mod:`dadaia_workspace.features.lifecycle.model_profiles` directly — NOT the Wave-B
``dadaia_catalog``. :func:`library_workflow_catalog` builds the catalog by introspecting
the implementation pipeline (``implementation_ladder``) and naming a default profile per
step. Wave B will later make ``dadaia_catalog`` the governed catalog and feed it here, but
Wave A is green on its own.

Validation: every override (overlay or CLI) must reference a catalog step id, a known
profile id (:mod:`model_profiles`), and a profile whose harness matches the step's
resolved harness; a deprecated profile without a replacement is a hard failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.core.models.workflow_execution import (
    PolicySource,
    WorkflowModelProfile,
    WorkflowPolicySnapshot,
    WorkflowPolicyStepEntry,
)
from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.model_profiles import UnknownProfileError
from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    DEFAULT_CONTEXT,
    WorkflowModelPolicyOverlay,
)

#: The precedence vocabulary recorded on every snapshot (descending precedence).
_PRECEDENCE: tuple[str, ...] = (
    PolicySource.CLI.value,
    PolicySource.CONTEXT_OVERLAY.value,
    PolicySource.DEFAULT_OVERLAY.value,
    PolicySource.LIBRARY_DEFAULT.value,
)


class PolicyResolutionError(ValueError):
    """Raised when a workflow id is unknown or an override is invalid."""


@dataclass(frozen=True)
class StepOverride:
    """One CLI ``--step-model`` override: a step label → a profile id (D-3)."""

    step: str
    profile_id: str


@dataclass(frozen=True)
class CatalogStep:
    """One governed step in the library workflow catalog (M3 — built in Wave A).

    ``default_harness`` is the Layer-2 harness the step defaults to; ``default_profile``
    is the built-in profile id for that harness. ``fragments`` / ``output_schema`` are
    carried for the run snapshot's auditability.
    """

    label: str
    role: str
    default_harness: str
    default_profile: str
    fragments: tuple[str, ...] = ()
    output_schema: str | None = None


@dataclass(frozen=True)
class CatalogWorkflow:
    """One governed workflow: an ordered list of :class:`CatalogStep`."""

    workflow_id: str
    steps: tuple[CatalogStep, ...]

    def step(self, label: str) -> CatalogStep | None:
        for entry in self.steps:
            if entry.label == label:
                return entry
        return None


@dataclass(frozen=True)
class WorkflowCatalog:
    """The governed workflow catalog the resolver reads (M3: from model_profiles)."""

    workflows: tuple[CatalogWorkflow, ...] = field(default_factory=tuple)

    def workflow(self, workflow_id: str) -> CatalogWorkflow | None:
        for entry in self.workflows:
            if entry.workflow_id == workflow_id:
                return entry
        return None


# Map a pipeline ``AgentRuntimeKind`` to the Layer-2 harness name the catalog uses.
_KIND_TO_HARNESS: dict[AgentRuntimeKind, str] = {
    AgentRuntimeKind.CODEX_EXEC: "codex",
    AgentRuntimeKind.PI_HEADLESS: "pi",
}

# Default profile id per implementation-pipeline step (M3 — sourced from model_profiles).
# Implementation runs the standard worker profile; review/gate steps run the deep profile.
_IMPLEMENTATION_STEP_PROFILE: dict[str, str] = {
    "implement": "codex-implementation-standard",
    "review_qa": "codex-review-deep",
    "review_security": "codex-review-deep",
    "review_code": "codex-review-deep",
}


def library_workflow_catalog() -> WorkflowCatalog:
    """Build the Wave-A library workflow catalog from the pipeline + ``model_profiles``.

    The implementation pipeline (``implementation_ladder``) is the D-4 demo path and the
    only governed workflow Wave A needs. Each step's default profile is named from
    ``_IMPLEMENTATION_STEP_PROFILE`` and validated against the profile registry; the
    fragments + output schema are carried from the pipeline step for snapshot fidelity.
    """
    ladder = implementation_ladder(AgentRuntimeKind.CODEX_EXEC)
    steps: list[CatalogStep] = []
    for pstep in ladder:
        harness = _KIND_TO_HARNESS.get(pstep.runtime_kind, "codex")
        profile_id = _IMPLEMENTATION_STEP_PROFILE.get(pstep.label, "codex-implementation-standard")
        # Validate the default profile exists and matches the step harness at build time.
        profile = model_profiles.resolve(profile_id)
        if profile.harness != harness:
            raise PolicyResolutionError(
                f"library default profile {profile_id!r} (harness {profile.harness!r}) "
                f"does not match step {pstep.label!r} harness {harness!r}"
            )
        fragments = (pstep.fragment_id, *pstep.shared_fragment_ids) if pstep.fragment_id else ()
        steps.append(
            CatalogStep(
                label=pstep.label,
                role=pstep.role,
                default_harness=harness,
                default_profile=profile_id,
                fragments=fragments,
                output_schema="agent-run-result-v1",
            )
        )
    return WorkflowCatalog(
        workflows=(CatalogWorkflow(workflow_id="implementation", steps=tuple(steps)),)
    )


class WorkflowExecutionPolicyResolver:
    """Resolve a workflow's per-step model policy (the shared CLI+panel seam)."""

    def __init__(
        self,
        *,
        catalog: WorkflowCatalog,
        overlay: WorkflowModelPolicyOverlay | None = None,
    ) -> None:
        self._catalog = catalog
        self._overlay = overlay

    def resolve(
        self,
        workflow_id: str,
        *,
        context: str = DEFAULT_CONTEXT,
        cli_overrides: tuple[StepOverride, ...] = (),
        prefix_hash: str | None = None,
        now: datetime | None = None,
    ) -> WorkflowPolicySnapshot:
        """Resolve the full per-step policy for *workflow_id* into a frozen snapshot.

        Raises:
            PolicyResolutionError: if *workflow_id* is unknown, an override targets an
                unknown step, names an unknown/deprecated-dead profile, or names a profile
                whose harness does not match the step's harness.
        """
        workflow = self._catalog.workflow(workflow_id)
        if workflow is None:
            valid = ", ".join(w.workflow_id for w in self._catalog.workflows) or "(none)"
            raise PolicyResolutionError(
                f"unknown workflow {workflow_id!r}; governed workflows: {valid}"
            )

        cli_by_step = {ov.step: ov.profile_id for ov in cli_overrides}
        # Validate CLI override step ids against the catalog (fail before resolving).
        for step_label in cli_by_step:
            if workflow.step(step_label) is None:
                valid = ", ".join(s.label for s in workflow.steps)
                raise PolicyResolutionError(
                    f"--step-model targets unknown step {step_label!r} of "
                    f"workflow {workflow_id!r}; valid steps: {valid}"
                )

        # Validate the (honored) default-context overlay step ids against the catalog, so a
        # stale overlay step id is a hard failure rather than a silently-ignored no-op (D-2:
        # only the `default` context is honored, so only it is validated/applied).
        if self._overlay is not None and context == DEFAULT_CONTEXT:
            overlay_steps = self._overlay.contexts.get(context, {}).get(workflow_id, {})
            for step_label in overlay_steps:
                if workflow.step(step_label) is None:
                    valid = ", ".join(s.label for s in workflow.steps)
                    raise PolicyResolutionError(
                        f"overlay targets unknown step {step_label!r} of "
                        f"workflow {workflow_id!r}; valid steps: {valid}"
                    )

        entries: list[WorkflowPolicyStepEntry] = []
        for step in workflow.steps:
            entries.append(self._resolve_step(workflow_id, step, context, cli_by_step))

        resolved_at = (now or datetime.now(tz=UTC)).isoformat().replace("+00:00", "Z")
        return WorkflowPolicySnapshot(
            workflow_id=workflow_id,
            policy_id=self._overlay.policy_id if self._overlay else DEFAULT_CONTEXT,
            resolved_at=resolved_at,
            source_precedence=_PRECEDENCE,
            overlay_id=self._overlay.policy_id if self._overlay else None,
            steps=tuple(entries),
            prefix_hash=prefix_hash,
        )

    def _resolve_step(
        self,
        workflow_id: str,
        step: CatalogStep,
        context: str,
        cli_by_step: dict[str, str],
    ) -> WorkflowPolicyStepEntry:
        # Precedence: CLI > default-overlay (only `default` context, D-2) > library default.
        profile_id = step.default_profile
        source = PolicySource.LIBRARY_DEFAULT

        overlay_profile = (
            self._overlay.step_profile(context, workflow_id, step.label)
            if self._overlay is not None
            else None
        )
        if overlay_profile is not None:
            profile_id = overlay_profile
            source = PolicySource.DEFAULT_OVERLAY

        cli_profile = cli_by_step.get(step.label)
        if cli_profile is not None:
            profile_id = cli_profile
            source = PolicySource.CLI

        profile = self._validate_profile(workflow_id, step, profile_id, source)
        return WorkflowPolicyStepEntry(
            step=step.label,
            harness=profile.harness,
            model_profile=profile.id,
            model=profile.model_id,
            reasoning=profile.effort,
            source=source,
            fragments=step.fragments,
            output_schema=step.output_schema,
        )

    def _validate_profile(
        self,
        workflow_id: str,
        step: CatalogStep,
        profile_id: str,
        source: PolicySource,
    ) -> WorkflowModelProfile:
        try:
            profile = model_profiles.resolve(profile_id)
        except UnknownProfileError as exc:
            raise PolicyResolutionError(
                f"{source.value} override for step {step.label!r} of workflow "
                f"{workflow_id!r}: {exc}"
            ) from exc
        if profile.harness != step.default_harness:
            raise PolicyResolutionError(
                f"{source.value} override profile {profile_id!r} runs on harness "
                f"{profile.harness!r}, but step {step.label!r} of workflow {workflow_id!r} "
                f"resolves to harness {step.default_harness!r}"
            )
        if profile.deprecated and not profile.replacement:
            raise PolicyResolutionError(
                f"profile {profile_id!r} is deprecated without a replacement; "
                "pick a current profile"
            )
        return profile


__all__ = [
    "CatalogStep",
    "CatalogWorkflow",
    "PolicyResolutionError",
    "StepOverride",
    "WorkflowCatalog",
    "WorkflowExecutionPolicyResolver",
    "library_workflow_catalog",
]
