"""Built-in model-profile registry — ``features/lifecycle/model_profiles.py``.

Named, governed Layer-2 model profiles (D-2: **built-in only** this release) layered
over the single discrete catalog in :mod:`dadaia_workspace.core.harness_models`. A
profile (e.g. ``codex-implementation-standard``) gives the operator a stable, inspectable
governance unit instead of a raw ``<id>:<effort>`` string, while every profile's
``(model_id, effort)`` MUST resolve to a real :class:`HarnessModelOption` — so this is
**never a second drifting model table**.

The no-second-table guard mirrors ``harness_models._assert_ids_known``:
:func:`_assert_profiles_resolve` runs at import time and fails loudly if any profile names
a ``(model_id, effort)`` pair the catalog does not carry, names a ``claude-*`` id (the
GPT-only Layer-2 invariant), uses a non-Layer-2 harness, or is deprecated without a
``replacement`` that itself exists.

Layering: ``features`` over ``core`` data — zero I/O.
"""

from __future__ import annotations

from typing import get_args

from dadaia_workspace.core import harness_models
from dadaia_workspace.core.harness_models import HarnessModelOption
from dadaia_workspace.core.model_registry import CodexEffort
from dadaia_workspace.core.models.workflow_execution import WorkflowModelProfile

_VALID_EFFORTS: frozenset[str] = frozenset(get_args(CodexEffort))


class UnknownProfileError(ValueError):
    """Raised when a profile id is not in the built-in registry."""


def _as_effort(effort: str) -> CodexEffort:
    """Narrow a profile's ``effort`` string to the ``CodexEffort`` literal.

    Raises:
        ValueError: if *effort* is not one of the catalog's reasoning-effort values.
    """
    if effort not in _VALID_EFFORTS:
        raise ValueError(
            f"invalid reasoning effort {effort!r}; valid: {', '.join(sorted(_VALID_EFFORTS))}"
        )
    # ``effort`` is now provably one of the literal members.
    return effort  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# THE BUILT-IN PROFILES — D-2 (Codex profiles + recommended PI aliases).
#
# Each profile resolves to one discrete option in core.harness_models:
#   codex: (gpt-5.5, high), (gpt-5.5, medium)
#   pi:    (gpt-5.5, high), (gpt-5.5, low), (gpt-5.3-codex, medium)
# Changing a profile's model is a one-line data edit here; the import-time assert ties it
# back to the catalog (which itself ties back to model_registry.REGISTRY).
# ---------------------------------------------------------------------------
_BUILT_IN: tuple[WorkflowModelProfile, ...] = (
    WorkflowModelProfile(
        id="codex-implementation-standard",
        harness="codex",
        label="Codex — implementation (standard)",
        model_id="gpt-5.5",
        effort="medium",
        purpose="Standard implementation/worker effort on Codex.",
    ),
    WorkflowModelProfile(
        id="codex-review-deep",
        harness="codex",
        label="Codex — review (deep)",
        model_id="gpt-5.5",
        effort="high",
        purpose="Deep-reasoning review/gate effort on Codex.",
    ),
    WorkflowModelProfile(
        id="pi-implementation-standard",
        harness="pi",
        label="PI — implementation (standard)",
        model_id="gpt-5.3-codex",
        effort="medium",
        purpose="Standard implementation/worker effort on PI.",
    ),
    WorkflowModelProfile(
        id="pi-reasoning-high",
        harness="pi",
        label="PI — reasoning (high)",
        model_id="gpt-5.5",
        effort="high",
        purpose="Deep-reasoning review/gate effort on PI.",
    ),
    WorkflowModelProfile(
        id="pi-reasoning-low",
        harness="pi",
        label="PI — reasoning (low)",
        model_id="gpt-5.5",
        effort="low",
        purpose="Low-cost mechanical effort on PI.",
    ),
)

#: Layer-2 harness names a profile may declare (LAW 1). ``fake`` carries no model.
_LAYER2_HARNESSES = frozenset({harness_models.CODEX_HARNESS, harness_models.PI_HARNESS})


def _assert_profiles_resolve() -> None:
    """Fail loudly at import if any built-in profile is ungoverned (no-second-table guard).

    Raises:
        ValueError: if a profile names a non-Layer-2 harness, a ``claude-*`` model id, a
            ``(model_id, effort)`` pair absent from the catalog, a duplicate id, or is
            deprecated without a ``replacement`` that itself exists in the registry.
    """
    ids: set[str] = set()
    by_id = {p.id: p for p in _BUILT_IN}
    for profile in _BUILT_IN:
        if profile.id in ids:
            raise ValueError(f"duplicate model-profile id {profile.id!r}")
        ids.add(profile.id)
        if profile.harness not in _LAYER2_HARNESSES:
            raise ValueError(
                f"profile {profile.id!r} names non-Layer-2 harness {profile.harness!r}; "
                f"Layer-2 harnesses: {sorted(_LAYER2_HARNESSES)}"
            )
        if profile.model_id.startswith("claude-"):
            raise ValueError(
                f"profile {profile.id!r} names a Claude id {profile.model_id!r}; "
                "Layer-2 is GPT-only (ADR-B)"
            )
        option = HarnessModelOption(profile.model_id, _as_effort(profile.effort))
        if option not in harness_models.options_for(profile.harness):
            valid = ", ".join(harness_models.model_choices(profile.harness))
            raise ValueError(
                f"profile {profile.id!r} resolves to {profile.model_id}:{profile.effort}, "
                f"not a {profile.harness} catalog option; valid: {valid}"
            )
        if profile.deprecated and not profile.replacement:
            raise ValueError(
                f"deprecated profile {profile.id!r} must declare a replacement profile id"
            )
    for profile in _BUILT_IN:
        if profile.replacement and profile.replacement not in by_id:
            raise ValueError(
                f"profile {profile.id!r} names replacement {profile.replacement!r}, "
                "which is not a known profile id"
            )


_assert_profiles_resolve()


def list_profiles() -> tuple[WorkflowModelProfile, ...]:
    """Return all built-in profiles in presentation order."""
    return _BUILT_IN


def profiles_for(harness: str) -> tuple[WorkflowModelProfile, ...]:
    """Return the built-in profiles for *harness* (empty for ``fake``/unknown)."""
    return tuple(p for p in _BUILT_IN if p.harness == harness)


def resolve(profile_id: str) -> WorkflowModelProfile:
    """Resolve a profile id to its :class:`WorkflowModelProfile`.

    Raises:
        UnknownProfileError: if *profile_id* is not a built-in profile; the message lists
            the valid ids.
    """
    for profile in _BUILT_IN:
        if profile.id == profile_id:
            return profile
    valid = ", ".join(p.id for p in _BUILT_IN)
    raise UnknownProfileError(f"unknown model profile {profile_id!r}; valid profiles: {valid}")


def to_option(profile: WorkflowModelProfile) -> HarnessModelOption:
    """Return the discrete :class:`HarnessModelOption` a profile resolves to."""
    return HarnessModelOption(profile.model_id, _as_effort(profile.effort))


__all__ = [
    "UnknownProfileError",
    "list_profiles",
    "profiles_for",
    "resolve",
    "to_option",
]
