"""Test-owned Wave-A library workflow catalog builder.

Relocated from ``policy_resolver.library_workflow_catalog`` in v0.1.53 (T-53-11): the
function had zero production consumers — the CLI/panel resolver runs on the *governed*
catalog from ``dadaia_catalog.governed_workflow_catalog``. It survives only as a test
fixture that builds a standalone catalog by introspecting the implementation pipeline,
so it lives with the tests that use it.
"""

from __future__ import annotations

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder
from dadaia_workspace.features.lifecycle.policy_resolver import (
    _IMPLEMENTATION_STEP_PROFILE,
    _KIND_TO_HARNESS,
    DEFAULT_PROFILE_BY_HARNESS_PURPOSE,
    CatalogStep,
    CatalogWorkflow,
    PolicyResolutionError,
    WorkflowCatalog,
)


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
        # T-29-A-01: per-harness default profiles so the resolver can auto-select a profile
        # for an effective-harness override. Review/gate steps default to the deep profile.
        purpose = "deep" if pstep.label.startswith("review") else "standard"
        default_profiles = {
            h: by_purpose[purpose] for h, by_purpose in DEFAULT_PROFILE_BY_HARNESS_PURPOSE.items()
        }
        fragments = (pstep.fragment_id, *pstep.shared_fragment_ids) if pstep.fragment_id else ()
        steps.append(
            CatalogStep(
                label=pstep.label,
                role=pstep.role,
                default_harness=harness,
                default_profile=profile_id,
                default_profiles=default_profiles,
                fragments=fragments,
                output_schema="agent-run-result-v1",
            )
        )
    return WorkflowCatalog(
        workflows=(CatalogWorkflow(workflow_id="implementation", steps=tuple(steps)),)
    )
