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
no-``claude-*`` Layer-2 invariant), uses a non-Layer-2 harness, or is deprecated without a
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
#   pi:    (openai-codex/gpt-5.5, high|medium|low)
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
        model_id="openai-codex/gpt-5.5",
        effort="medium",
        purpose="Standard implementation/worker effort on PI.",
    ),
    WorkflowModelProfile(
        id="pi-reasoning-high",
        harness="pi",
        label="PI — reasoning (high)",
        model_id="openai-codex/gpt-5.5",
        effort="high",
        purpose="Deep-reasoning review/gate effort on PI.",
    ),
    WorkflowModelProfile(
        id="pi-reasoning-low",
        harness="pi",
        label="PI — reasoning (low)",
        model_id="openai-codex/gpt-5.5",
        effort="low",
        purpose="Low-cost mechanical effort on PI.",
    ),
    WorkflowModelProfile(
        id="pi-openrouter-kimi-high",
        harness="pi",
        label="OpenRouter — kimi-k2.5 (high)",
        model_id="moonshotai/kimi-k2.5",
        effort="high",
        purpose="OpenRouter moonshotai/kimi-k2.5 (high reasoning) as a governed PI worker "
        "(v0.1.44 allowlist-validated Layer-2-native id; corrected to the valid "
        "OpenRouter-namespaced id in v0.1.66 FR3 — the prior 'kimi-2.7' literal was "
        "rejected by OpenRouter). Carries no registry pricing row — cost reports "
        "'unknown', never fabricated.",
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
                "Layer-2 is allowlist-validated; claude-* is never a Layer-2 worker (ADR-B)"
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


# ---------------------------------------------------------------------------
# Operator-local profile merge (WS-PROFILES / T-30-C-02).
#
# The operator may register their own Layer-2 profiles in a workspace-local store
# (loaded through :class:`LocalModelProfileStorePort`). They are merged on top of the
# built-in registry so :func:`list_profiles` / :func:`profiles_for` / :func:`resolve`
# surface built-in + operator profiles, while :class:`UnknownProfileError` stays
# fail-closed. **Default-first (L3):** the operator registry defaults to empty, so when no
# local store exists the public functions behave byte-identically to the built-in-only
# world. The merge re-runs the same governance assertions the built-in registry runs (a
# bad operator profile fails loud), and a built-in id is never shadowed by an operator id.
# ---------------------------------------------------------------------------

#: The merged-in operator profiles (empty until a local store is loaded). Process-level,
#: mutated only through :func:`load_operator_profiles` / :func:`clear_operator_profiles`.
_OPERATOR_PROFILES: tuple[WorkflowModelProfile, ...] = ()


def _assert_operator_profiles_resolve(profiles: tuple[WorkflowModelProfile, ...]) -> None:
    """Fail loudly if an operator profile is ungoverned or collides with a built-in.

    Mirrors :func:`_assert_profiles_resolve` for the operator set: every operator profile
    must name a Layer-2 harness, never a ``claude-*`` model id, resolve to a real catalog
    option, carry a replacement when deprecated, and **never** reuse a built-in profile id
    (a built-in is authoritative — an operator cannot silently redefine it).
    """
    built_in_ids = {p.id for p in _BUILT_IN}
    seen: set[str] = set()
    for profile in profiles:
        if profile.id in built_in_ids:
            raise ValueError(
                f"operator profile {profile.id!r} collides with a built-in profile id; "
                "operator profiles must use distinct ids"
            )
        if profile.id in seen:
            raise ValueError(f"duplicate operator profile id {profile.id!r}")
        seen.add(profile.id)
        if profile.harness not in _LAYER2_HARNESSES:
            raise ValueError(
                f"operator profile {profile.id!r} names non-Layer-2 harness "
                f"{profile.harness!r}; Layer-2 harnesses: {sorted(_LAYER2_HARNESSES)}"
            )
        if profile.model_id.startswith("claude-"):
            raise ValueError(
                f"operator profile {profile.id!r} names a Claude id {profile.model_id!r}; "
                "Layer-2 is allowlist-validated; claude-* is never a Layer-2 worker (ADR-B)"
            )
        option = HarnessModelOption(profile.model_id, _as_effort(profile.effort))
        if option not in harness_models.options_for(profile.harness):
            valid = ", ".join(harness_models.model_choices(profile.harness))
            raise ValueError(
                f"operator profile {profile.id!r} resolves to "
                f"{profile.model_id}:{profile.effort}, not a {profile.harness} catalog "
                f"option; valid: {valid}"
            )
        if profile.deprecated and not profile.replacement:
            raise ValueError(
                f"deprecated operator profile {profile.id!r} must declare a replacement"
            )


def load_operator_profiles(store: object) -> None:
    """Load + merge operator profiles from a :class:`LocalModelProfileStorePort`.

    Idempotent: replaces the current operator set with the store's profiles. A **missing**
    store yields an empty set (default-first — L3); a **present-but-invalid** store raises
    through the store's own typed error (the store validates ``harness == "pi"`` per L1 and
    rejects API-key-bearing fields per L8), and the merge then re-asserts governance and the
    no-built-in-collision invariant. The argument is typed ``object`` to keep ``features``
    from importing the infrastructure adapter; it must expose ``load() -> tuple[...]``.
    """
    global _OPERATOR_PROFILES
    loaded = store.load()  # type: ignore[attr-defined]
    profiles = tuple(loaded)
    _assert_operator_profiles_resolve(profiles)
    _OPERATOR_PROFILES = profiles


def clear_operator_profiles() -> None:
    """Reset the operator set to empty (default-first). Used at teardown / re-bind."""
    global _OPERATOR_PROFILES
    _OPERATOR_PROFILES = ()


def _all_profiles() -> tuple[WorkflowModelProfile, ...]:
    """Built-in profiles followed by any merged operator profiles (default-first)."""
    return (*_BUILT_IN, *_OPERATOR_PROFILES)


def list_profiles() -> tuple[WorkflowModelProfile, ...]:
    """Return all profiles (built-in + merged operator) in presentation order.

    Built-in first, then operator profiles. With no local store loaded the operator set is
    empty, so this is byte-identical to the built-in-only registry (L3 — default-first).
    """
    return _all_profiles()


def profiles_for(harness: str) -> tuple[WorkflowModelProfile, ...]:
    """Return the profiles for *harness* (built-in + operator; empty for ``fake``/unknown)."""
    return tuple(p for p in _all_profiles() if p.harness == harness)


def resolve(profile_id: str) -> WorkflowModelProfile:
    """Resolve a profile id to its :class:`WorkflowModelProfile` (built-in or operator).

    Raises:
        UnknownProfileError: if *profile_id* is neither a built-in nor a merged operator
            profile; the message lists the valid ids (fail-closed).
    """
    for profile in _all_profiles():
        if profile.id == profile_id:
            return profile
    valid = ", ".join(p.id for p in _all_profiles())
    raise UnknownProfileError(f"unknown model profile {profile_id!r}; valid profiles: {valid}")


def to_option(profile: WorkflowModelProfile) -> HarnessModelOption:
    """Return the discrete :class:`HarnessModelOption` a profile resolves to."""
    return HarnessModelOption(profile.model_id, _as_effort(profile.effort))


__all__ = [
    "UnknownProfileError",
    "clear_operator_profiles",
    "list_profiles",
    "load_operator_profiles",
    "profiles_for",
    "resolve",
    "to_option",
]
