"""The single shared workflow execution-policy resolver — ``policy_resolver.py``.

:class:`WorkflowExecutionPolicyResolver` is **the** seam both the CLI and the panel
consume to turn a workflow id + context + CLI overrides into a frozen
:class:`WorkflowPolicySnapshot`. Resolving once, here, is what guarantees CLI and panel
never disagree on which model a step runs.

**Precedence (per step):** ``CLI override > context overlay > default overlay > library
default``. Per-context overlays are honored (WS-OVERLAYS, replacing the D-2 collapse): a
non-``default`` context resolves a step's profile/harness through its ``extends`` chain
(``context → extends… → default``), the nearest level that defines a value winning. The
overlay store parse-validates the ``extends`` graph (no cycle / no missing parent), so the
chain walk here is total. An unresolvable ref (unknown profile, harness/profile mismatch,
deprecated-without-replacement, or a stale overlay step id anywhere in the chain) is a hard
failure (fail-closed). The precedence vocabulary is recorded on the snapshot for
auditability.

**Production catalog source.** The resolver the CLI + panel run on is fed the **governed**
catalog from
:func:`dadaia_workspace.features.workflows.dadaia_catalog.governed_workflow_catalog` (wired
via ``container.build_workflow_model_profile_registry``) — that is the single governed
source of truth, with one home for the per-harness default-by-purpose map
(:data:`DEFAULT_PROFILE_BY_HARNESS_PURPOSE`, which the catalog imports from here).
A Wave-A-independent standalone catalog builder (introspecting the implementation
pipeline, sharing these profile defaults) lives in the tests as
``tests/unit/features/lifecycle/_workflow_catalog.py`` — it was never the production
source consumed by the container, so it was relocated out of this module in v0.1.53.

Validation: every override (overlay or CLI) must reference a catalog step id, a known
profile id (:mod:`model_profiles`), and a profile whose harness matches the step's
resolved harness; a deprecated profile without a replacement is a hard failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from dadaia_workspace.core.harness_registry import L2_WORKER_HARNESSES
from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.core.models.workflow_execution import (
    DEFAULT_CONTEXT,
    PolicySource,
    WorkflowModelPolicyOverlay,
    WorkflowModelProfile,
    WorkflowPolicySnapshot,
    WorkflowPolicyStepEntry,
)
from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.model_profiles import UnknownProfileError

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
class StepHarnessOverride:
    """One CLI ``--step-harness`` override: a step label → a Layer-2 harness (D-1)."""

    step: str
    harness: str


@dataclass(frozen=True)
class CatalogStep:
    """One governed step in the library workflow catalog (M3 — built in Wave A).

    ``default_harness`` is the Layer-2 harness the step defaults to; ``default_profile``
    is the built-in profile id for that harness. ``default_profiles`` (v0.1.29 / T-29-A-01)
    maps every supported harness to its built-in default profile id so the resolver can
    auto-select a profile per *effective* harness (D-1). ``fragments`` / ``output_schema``
    are carried for the run snapshot's auditability.
    """

    label: str
    role: str
    default_harness: str
    default_profile: str
    default_profiles: dict[str, str] = field(default_factory=dict)
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

#: The Layer-2 worker harnesses an effective-harness override may name (LAW 1, v0.1.29).
#: ``claude``/``opencode`` are NOT Layer-2 workers; ``fake`` is the test adapter and is
#: never a *resolved* (governed) harness — it is handled at the pipeline/runtime layer.
#: Sourced from the single ``core/harness_registry`` roster (v0.1.58 FR1) — no fork.
_LAYER2_HARNESSES: frozenset[str] = frozenset(L2_WORKER_HARNESSES)

# Default profile id per implementation-pipeline step (M3 — sourced from model_profiles).
# Implementation runs the standard worker profile; review/gate steps run the deep profile.
_IMPLEMENTATION_STEP_PROFILE: dict[str, str] = {
    "implement": "codex-implementation-standard",
    "review_qa": "codex-review-deep",
    "review_security": "codex-review-deep",
    "review_code": "codex-review-deep",
}

# Per-harness default profile by step purpose — the **single shared home** (T-30-C-05 nit i;
# previously a verbatim twin in ``dadaia_catalog``). ``"standard"`` = a producing worker
# step, ``"deep"`` = a review/gate worker step. The governed catalog
# (:func:`dadaia_catalog.governed_workflow_catalog`, which imports this map) populates each
# ``CatalogStep.default_profiles`` from it so the resolver can auto-select a profile per
# effective harness (D-1). Governance is enforced by
# ``dadaia_catalog._assert_catalog_defaults_resolve`` at import time (every profile id
# resolves + harness matches). PI has no dedicated review profile, so its deep slot is
# ``pi-reasoning-high``.
DEFAULT_PROFILE_BY_HARNESS_PURPOSE: dict[str, dict[str, str]] = {
    # "light" is the mechanical-step tier (e.g. the close step): pi routes to its
    # low-effort profile; codex has no sub-medium catalog option, so light == standard.
    "codex": {
        "standard": "codex-implementation-standard",
        "deep": "codex-review-deep",
        "light": "codex-implementation-standard",
    },
    "pi": {
        "standard": "pi-implementation-standard",
        "deep": "pi-reasoning-high",
        "light": "pi-reasoning-low",
    },
}


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
        default_harness: str | None = None,
        step_harness_overrides: tuple[StepHarnessOverride, ...] = (),
        prefix_hash: str | None = None,
        now: datetime | None = None,
    ) -> WorkflowPolicySnapshot:
        """Resolve the full per-step policy for *workflow_id* into a frozen snapshot.

        The **effective harness** per step (D-1) resolves with precedence (highest wins)::

            CLI --step-harness > CLI --harness (default) > overlay step harness
                               > overlay default_harness > catalog step default

        When a harness override lands for a step with no explicit profile override, the
        resolver auto-selects that harness's default profile for the step's purpose; an
        explicit ``--step-model`` profile is never overridden. Every resolved profile must
        match its step's *effective* harness, not the catalog default.

        Raises:
            PolicyResolutionError: if *workflow_id* is unknown, an override targets an
                unknown step, names a non-Layer-2 harness, names an unknown/deprecated-dead
                profile, or names a profile whose harness does not match the step's
                *effective* harness.
        """
        workflow = self._catalog.workflow(workflow_id)
        if workflow is None:
            valid = ", ".join(w.workflow_id for w in self._catalog.workflows) or "(none)"
            raise PolicyResolutionError(
                f"unknown workflow {workflow_id!r}; governed workflows: {valid}"
            )

        cli_by_step = {ov.step: ov.profile_id for ov in cli_overrides}
        cli_harness_by_step = {ov.step: ov.harness for ov in step_harness_overrides}

        # Validate the Layer-2 harness inputs up front (LAW 1 / AC-9) — a non-codex/pi
        # harness is a clean rejection with a pointer, never a silent fallback.
        if default_harness is not None:
            self._assert_layer2_harness(default_harness, source="--harness")
        for label, harness in cli_harness_by_step.items():
            self._assert_layer2_harness(harness, source=f"--step-harness {label!r}")

        # Validate CLI override step ids against the catalog (fail before resolving).
        for step_label in {*cli_by_step, *cli_harness_by_step}:
            if workflow.step(step_label) is None:
                valid = ", ".join(s.label for s in workflow.steps)
                raise PolicyResolutionError(
                    f"override targets unknown step {step_label!r} of "
                    f"workflow {workflow_id!r}; valid steps: {valid}"
                )

        # Validate the resolved context's overlay step ids against the catalog (WS-OVERLAYS:
        # every context is honored, walking its `extends` chain — not only `default`). A
        # stale overlay step id anywhere in the chain is a hard failure rather than a
        # silently-ignored no-op. The store has already validated the `extends` graph (no
        # cycle / no missing parent), so walking it here is safe.
        if self._overlay is not None:
            for step_label in self._overlay_chain_steps(context, workflow_id):
                if workflow.step(step_label) is None:
                    valid = ", ".join(s.label for s in workflow.steps)
                    raise PolicyResolutionError(
                        f"overlay targets unknown step {step_label!r} of "
                        f"workflow {workflow_id!r}; valid steps: {valid}"
                    )

        entries: list[WorkflowPolicyStepEntry] = []
        for step in workflow.steps:
            entries.append(
                self._resolve_step(
                    workflow_id,
                    step,
                    context,
                    cli_by_step,
                    cli_default_harness=default_harness,
                    cli_harness_by_step=cli_harness_by_step,
                )
            )

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

    def _overlay_chain_steps(self, context: str, workflow_id: str) -> set[str]:
        """Return every step label the overlay overrides across *context*'s ``extends`` chain.

        Unions the profile-override steps and the per-step harness-override steps from each
        level of ``context → extends… → default`` so a stale step id anywhere in the chain
        is validated (WS-OVERLAYS). Returns the empty set when no overlay is bound.
        """
        if self._overlay is None:
            return set()
        steps: set[str] = set()
        for level in self._context_chain(context):
            steps |= set(self._overlay.contexts.get(level, {}).get(workflow_id, {}))
            steps |= set(self._overlay.step_harness_overlay.get(level, {}).get(workflow_id, {}))
        return steps

    def _context_chain(self, context: str) -> list[str]:
        """Return the ordered context chain ``[context, parent…, default]`` (WS-OVERLAYS).

        Mirrors the store's chain walk over the parse-validated ``extends`` graph (no cycle /
        no missing parent), so this terminates; a defensive ``seen`` guard breaks any
        pathological case. ``default`` is always the tail.
        """
        if self._overlay is None:
            return [context, DEFAULT_CONTEXT] if context != DEFAULT_CONTEXT else [DEFAULT_CONTEXT]
        chain: list[str] = []
        seen: set[str] = set()
        current: str | None = context
        while current is not None and current not in seen:
            chain.append(current)
            seen.add(current)
            current = self._overlay.extends.get(current)
        if DEFAULT_CONTEXT not in chain:
            chain.append(DEFAULT_CONTEXT)
        return chain

    def _assert_layer2_harness(self, harness: str, *, source: str) -> None:
        """Reject a harness that is not a Layer-2 worker (codex|pi) — AC-9."""
        if harness not in _LAYER2_HARNESSES:
            raise PolicyResolutionError(
                f"{source} names harness {harness!r}, which is not a Layer-2 worker; "
                f"Layer-2 workers are codex or pi only (claude is a Layer-1 entry harness, "
                f"opencode was removed)"
            )

    def _resolve_harness(
        self,
        workflow_id: str,
        step: CatalogStep,
        context: str,
        *,
        cli_default_harness: str | None,
        cli_harness_by_step: dict[str, str],
    ) -> str:
        """Compute a step's effective harness with the D-1 precedence chain.

        ``CLI --step-harness > CLI --harness (default) > overlay step harness
        > overlay default_harness > catalog step default``.
        """
        cli_step = cli_harness_by_step.get(step.label)
        if cli_step is not None:
            return cli_step
        if cli_default_harness is not None:
            return cli_default_harness
        if self._overlay is not None:
            overlay_step = self._overlay.step_harness(context, workflow_id, step.label)
            if overlay_step is not None:
                return overlay_step
            overlay_default = self._overlay.workflow_default_harness(context, workflow_id)
            if overlay_default is not None:
                return overlay_default
        return step.default_harness

    def _resolve_step(
        self,
        workflow_id: str,
        step: CatalogStep,
        context: str,
        cli_by_step: dict[str, str],
        *,
        cli_default_harness: str | None,
        cli_harness_by_step: dict[str, str],
    ) -> WorkflowPolicyStepEntry:
        effective_harness = self._resolve_harness(
            workflow_id,
            step,
            context,
            cli_default_harness=cli_default_harness,
            cli_harness_by_step=cli_harness_by_step,
        )

        # Profile precedence: CLI > overlay (resolved through the context's `extends` chain,
        # WS-OVERLAYS) > auto-selected default for the EFFECTIVE harness (D-1 auto-profile).
        # An explicit profile (CLI or overlay) is never overridden by harness auto-selection.
        profile_id = self._default_profile_for_harness(step, effective_harness)
        source = PolicySource.LIBRARY_DEFAULT
        explicit = False

        overlay_profile = (
            self._overlay.step_profile(context, workflow_id, step.label)
            if self._overlay is not None
            else None
        )
        if overlay_profile is not None:
            profile_id = overlay_profile
            source = PolicySource.DEFAULT_OVERLAY
            explicit = True

        cli_profile = cli_by_step.get(step.label)
        if cli_profile is not None:
            profile_id = cli_profile
            source = PolicySource.CLI
            explicit = True

        profile = self._validate_profile(
            workflow_id, step, profile_id, source, effective_harness, explicit=explicit
        )
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

    def _default_profile_for_harness(self, step: CatalogStep, harness: str) -> str:
        """Return the auto-selected library default profile id for *harness* (D-1).

        Uses the step's per-harness ``default_profiles`` map when it carries the effective
        harness; falls back to the step's catalog default profile when the effective harness
        equals the catalog default harness (the no-override path stays byte-identical, AC-10).
        """
        mapped = step.default_profiles.get(harness)
        if mapped is not None:
            return mapped
        if harness == step.default_harness:
            return step.default_profile
        raise PolicyResolutionError(
            f"step {step.label!r} has no default profile for effective harness {harness!r}; "
            f"declare one or pass an explicit profile override"
        )

    def _validate_profile(
        self,
        workflow_id: str,
        step: CatalogStep,
        profile_id: str,
        source: PolicySource,
        effective_harness: str,
        *,
        explicit: bool,
    ) -> WorkflowModelProfile:
        try:
            profile = model_profiles.resolve(profile_id)
        except UnknownProfileError as exc:
            raise PolicyResolutionError(
                f"{source.value} override for step {step.label!r} of workflow "
                f"{workflow_id!r}: {exc}"
            ) from exc
        if profile.harness != effective_harness:
            # An explicit profile that conflicts with the effective harness is the named
            # `--harness pi` + codex `--step-model` rejection (AC-2 conflict).
            detail = "override " if explicit else ""
            raise PolicyResolutionError(
                f"{source.value} {detail}profile {profile_id!r} runs on harness "
                f"{profile.harness!r}, but step {step.label!r} of workflow {workflow_id!r} "
                f"resolves to harness {effective_harness!r}"
            )
        if profile.deprecated and not profile.replacement:
            raise PolicyResolutionError(
                f"profile {profile_id!r} is deprecated without a replacement; "
                "pick a current profile"
            )
        return profile


__all__ = [
    "DEFAULT_PROFILE_BY_HARNESS_PURPOSE",
    "CatalogStep",
    "CatalogWorkflow",
    "PolicyResolutionError",
    "StepHarnessOverride",
    "StepOverride",
    "WorkflowCatalog",
    "WorkflowExecutionPolicyResolver",
]
