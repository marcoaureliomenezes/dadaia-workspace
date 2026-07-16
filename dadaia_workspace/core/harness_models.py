"""Discrete per-harness Layer-2 model catalog (LAW 2) — ``core/harness_models.py``.

The operator's two-layer model (v0.1.24 ADR-B) makes the Layer-2 worker model a
**discrete choice on the CLI call**, not a tier abstraction. Each Layer-2 harness
exposes an ordered, finite set of ``(model_id, reasoning_effort)`` options:

- **pi → 4 options:** ``(openai-codex/gpt-5.3-codex-spark, high)``,
  ``(openai-codex/gpt-5.3-codex-spark, low)``,
  ``(openai-codex/gpt-5.3-codex-spark, medium)``,
  ``(moonshotai/kimi-k2.5, high)``
- **codex → 2 options:** ``(gpt-5.3-codex-spark, high)``, ``(gpt-5.3-codex-spark, medium)``

**Allowlist-validated invariant (ADR-B, opened v0.1.44).** PI runs on the operator's
*Codex* subscription for GPT models, while a curated non-GPT Layer-2-native
OpenRouter worker id (:data:`LAYER2_EXTRA_MODEL_IDS`, currently
``moonshotai/kimi-k2.5``) is permitted alongside the registry Codex ids. Provider-
qualified ``openai-codex`` ids are mandatory so PI cannot resolve an ambiguous GPT
name through another provider. OpenRouter GPT ids are deliberately excluded so a GPT
workflow cannot silently bypass the operator's Codex subscription. The retained safety
bound is **no ``claude-*`` id** (including the region-restricted ``claude-fable-5``)
can ever appear at Layer 2 — claude is never a Layer-2 worker. Layer-1 Claude (the
``CLAUDE_SDK`` adapter) is unaffected — this catalog governs Layer-2 worker selection
only.

**Single source of truth, no second drifting table.** Every model id named here MUST
be in :func:`known_layer2_model_ids` — the registry ``codex_id`` set, its
provider-qualified ``openai-codex/`` projection for PI, UNION the curated
Layer-2-native allowlist. The catalog is validated against that union at import time
(:func:`_assert_ids_known`), so a registry id rename, or an OpenRouter id missing from
the allowlist, surfaces here loudly instead of silently drifting. The catalog itself is
explicit *data* keyed by harness (parameterized below) — confirming or changing a
model is a one-line data edit, NOT a tier-derivation change.

Layering: pure data over ``core/model_registry`` (itself zero-I/O ``core`` data), so
this stays import-linter clean in ``core``.
"""

from __future__ import annotations

from dataclasses import dataclass

from dadaia_workspace.core.model_registry import REGISTRY, CodexEffort

#: The Layer-2 harness names that select a discrete model (LAW 1). ``fake`` carries
#: no model (it is the deterministic test adapter), so it is intentionally absent
#: from the catalog — :func:`options_for` returns an empty tuple for unknown harnesses
#: and :func:`validate` is only called for harnesses that take a model.
PI_HARNESS = "pi"
CODEX_HARNESS = "codex"


@dataclass(frozen=True)
class HarnessModelOption:
    """One discrete Layer-2 model choice: a ``(model_id, reasoning_effort)`` pair.

    ``model_id`` is an allowlist-validated Layer-2 worker id (never ``claude-*`` — see
    module docstring) that MUST be in :func:`known_layer2_model_ids` (a registry
    ``codex_id``, its provider-qualified PI projection, or a curated OpenRouter id).
    ``effort`` is the Codex reasoning-effort axis the worker runs at.
    """

    model_id: str
    effort: CodexEffort


# ---------------------------------------------------------------------------
# THE CATALOG — explicit allowlist-validated data keyed by harness (ADR-B,
# operator 2026-06-26; opened to a curated OpenRouter set v0.1.44 / AC-5).
#
# Order is presentation order (most → least capable). Parameterized as data so a
# future id/effort change is a single data edit, NOT a tier-derivation change.
# Every id must be in :func:`known_layer2_model_ids` and must never be ``claude-*``.
# The pi catalog includes the curated OpenRouter option(s); the codex catalog is
# unchanged (codex runs only on registry codex ids).
# ---------------------------------------------------------------------------
_CATALOG: dict[str, tuple[HarnessModelOption, ...]] = {
    PI_HARNESS: (
        HarnessModelOption("openai-codex/gpt-5.3-codex-spark", "high"),
        HarnessModelOption("openai-codex/gpt-5.3-codex-spark", "low"),
        HarnessModelOption("openai-codex/gpt-5.3-codex-spark", "medium"),
        HarnessModelOption("moonshotai/kimi-k2.5", "high"),
    ),
    CODEX_HARNESS: (
        HarnessModelOption("gpt-5.3-codex-spark", "high"),
        HarnessModelOption("gpt-5.3-codex-spark", "medium"),
    ),
}


# ---------------------------------------------------------------------------
# Layer-2-native worker-model allowlist (v0.1.44 / AC-5, R6).
#
# pi's model set is opened from registry-codex-ids-only to registry-codex-ids
# PLUS a small, curated, Layer-2-native allowlist of OpenRouter worker-model ids.
# These ids are NOT inserted into ``model_registry.REGISTRY``: that table is keyed
# ``claude_id → codex_id`` and feeds THREE derived views including
# ``codex_tier_views()`` / ``_codex_id_for_tier()`` on the codex runtime hot path —
# a synthetic-alias entry would collide a tier (``len > 1`` → ``ValueError``) and
# fabricate a pricing row. The allowlist is therefore a Layer-2-native set kept here.
#
# Pricing stays honest: these ids carry no registry pricing row, so
# ``telemetry.pricing.compute_cost`` returns ``None`` ("unknown" — never fabricated)
# for them. Membership is named and explicit — no wildcard.
# ---------------------------------------------------------------------------
LAYER2_EXTRA_MODEL_IDS: frozenset[str] = frozenset({"moonshotai/kimi-k2.5"})


def _known_codex_ids() -> frozenset[str]:
    """The set of ``codex_id`` strings the registry recognises."""
    return frozenset(entry.codex_id for entry in REGISTRY)


def pi_codex_subscription_model_ids() -> frozenset[str]:
    """Provider-qualified PI model ids backed by the Codex subscription."""
    return frozenset(f"openai-codex/{model_id}" for model_id in _known_codex_ids())


def known_layer2_model_ids() -> frozenset[str]:
    """The full set of model ids a Layer-2 worker selection may name.

    The single source of truth for Layer-2 model-id membership: the registry
    ``codex_id`` set, its provider-qualified PI Codex-subscription projection, UNION
    the Layer-2-native allowlist (:data:`LAYER2_EXTRA_MODEL_IDS`). Both the catalog invariant
    (:func:`_assert_ids_known`) and the operator-overlay store validate against
    this one public helper, so neither leaks the private ``_known_codex_ids``
    across the layer boundary nor drifts from the other.
    """
    return _known_codex_ids() | pi_codex_subscription_model_ids() | LAYER2_EXTRA_MODEL_IDS


def _assert_ids_known() -> None:
    """Fail loudly at import if any catalog id is outside the Layer-2 allowlist.

    This is the no-second-drifting-table guard: the catalog may only name model ids
    that :func:`known_layer2_model_ids` carries (registry ``codex_id``s UNION the
    curated Layer-2-native allowlist). A registry rename that orphans a catalog id,
    or an OpenRouter id absent from the allowlist, raises here rather than drifting
    silently.

    The catalog is **allowlist-validated**, not GPT-only: a curated OpenRouter id is
    accepted, but a ``claude-*`` id is **never** a Layer-2 worker id and still raises
    (the no-``claude-*`` safety bound is retained).

    Raises:
        ValueError: if a catalog ``model_id`` is a ``claude-*`` id, or is absent from
            :func:`known_layer2_model_ids`.
    """
    known = known_layer2_model_ids()
    for harness, options in _CATALOG.items():
        for option in options:
            if option.model_id.startswith("claude-"):
                raise ValueError(
                    f"Layer-2 catalog for {harness!r} names a Claude id "
                    f"{option.model_id!r}; claude is never a Layer-2 worker id (ADR-B)"
                )
            if option.model_id not in known:
                raise ValueError(
                    f"Layer-2 catalog for {harness!r} names {option.model_id!r}, "
                    "which is not in the allowlist (registry codex_ids | "
                    "LAYER2_EXTRA_MODEL_IDS)"
                )


_assert_ids_known()


def harnesses() -> tuple[str, ...]:
    """Return the Layer-2 harness names that carry a discrete model catalog."""
    return tuple(_CATALOG)


def options_for(harness: str) -> tuple[HarnessModelOption, ...]:
    """Return the ordered discrete model options for *harness* (empty if none).

    A harness with no catalog (e.g. ``fake``, or an unknown name) yields ``()``.
    """
    return _CATALOG.get(harness, ())


def model_choices(harness: str) -> tuple[str, ...]:
    """Return the human-facing CLI ``--model`` choices for *harness*.

    Each choice is ``"<model_id>:<effort>"`` so the two distinct codex profiles of the
    same model id remain individually selectable (``gpt-5.3-codex-spark:high`` vs ``gpt-5.3-codex-spark:medium``).
    Order matches :func:`options_for`.
    """
    return tuple(f"{opt.model_id}:{opt.effort}" for opt in options_for(harness))


def validate(harness: str, model: str) -> HarnessModelOption:
    """Resolve a ``(harness, model)`` selection to its discrete option.

    *model* is matched against each option's ``"<model_id>:<effort>"`` choice string
    (the canonical CLI form) and, as a convenience, against a bare ``model_id`` **only
    when that id is unambiguous** for the harness (exactly one effort). This keeps the
    unambiguous ids ergonomic while forcing ``openai-codex/gpt-5.3-codex-spark`` to be
    disambiguated by effort.

    Args:
        harness: the Layer-2 harness name (e.g. ``"pi"``, ``"codex"``).
        model: the chosen model, as ``"<model_id>:<effort>"`` or an unambiguous
            bare ``model_id``.

    Returns:
        The resolved :class:`HarnessModelOption`.

    Raises:
        ValueError: if *harness* has no catalog or *model* is not one of its options.
            The message lists the harness's valid choices.
    """
    options = options_for(harness)
    if not options:
        valid = ", ".join(harnesses())
        raise ValueError(
            f"harness {harness!r} has no discrete model catalog; harnesses with a catalog: {valid}"
        )
    # Exact "<model_id>:<effort>" match (canonical form).
    for option in options:
        if model == f"{option.model_id}:{option.effort}":
            return option
    # Unambiguous bare-model_id convenience match.
    bare = [option for option in options if option.model_id == model]
    if len(bare) == 1:
        return bare[0]
    valid = ", ".join(model_choices(harness))
    raise ValueError(f"invalid model {model!r} for harness {harness!r}; valid options: {valid}")
