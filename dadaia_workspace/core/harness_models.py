"""Discrete per-harness Layer-2 model catalog (LAW 2) — ``core/harness_models.py``.

The operator's two-layer model (v0.1.24 ADR-B) makes the Layer-2 worker model a
**discrete choice on the CLI call**, not a tier abstraction. Each Layer-2 harness
exposes an ordered, finite set of ``(model_id, reasoning_effort)`` options:

- **pi → 3 options:** ``(gpt-5.5, high)``, ``(gpt-5.5, low)``, ``(gpt-5.3-codex, medium)``
- **codex → 2 options:** ``(gpt-5.5, high)``, ``(gpt-5.5, medium)``

**GPT-only invariant (ADR-B).** PI runs on the operator's *Codex* subscription, so
PI's Layer-2 models are GPT / codex model ids — never Claude ids. Both Layer-2
catalogs are therefore GPT-only **by construction**: no ``claude-*`` id (including the
region-restricted ``claude-fable-5``) can ever appear at Layer 2. Layer-1 Claude (the
``CLAUDE_SDK`` adapter) is unaffected — this catalog governs Layer-2 worker selection
only.

**Single source of truth, no second drifting table.** Every model id named here MUST
exist as a ``codex_id`` in :data:`model_registry.REGISTRY`. The catalog is validated
against the registry at import time (:func:`_assert_ids_known`), so a registry id
rename surfaces here loudly instead of silently drifting. The catalog itself is
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

    ``model_id`` is a GPT/codex id (never ``claude-*`` — see module docstring) that
    MUST exist as a ``codex_id`` in :data:`model_registry.REGISTRY`. ``effort`` is the
    Codex reasoning-effort axis the worker runs at.
    """

    model_id: str
    effort: CodexEffort


# ---------------------------------------------------------------------------
# THE CATALOG — explicit GPT-only data keyed by harness (ADR-B, operator 2026-06-26).
#
# Order is presentation order (most → least capable). Parameterized as data so a
# future id/effort change is a single data edit, NOT a tier-derivation change.
# ---------------------------------------------------------------------------
_CATALOG: dict[str, tuple[HarnessModelOption, ...]] = {
    PI_HARNESS: (
        HarnessModelOption("gpt-5.5", "high"),
        HarnessModelOption("gpt-5.5", "low"),
        HarnessModelOption("gpt-5.3-codex", "medium"),
    ),
    CODEX_HARNESS: (
        HarnessModelOption("gpt-5.5", "high"),
        HarnessModelOption("gpt-5.5", "medium"),
    ),
}


def _known_codex_ids() -> frozenset[str]:
    """The set of ``codex_id`` strings the registry recognises."""
    return frozenset(entry.codex_id for entry in REGISTRY)


def _assert_ids_known() -> None:
    """Fail loudly at import if any catalog id is not a registry ``codex_id``.

    This is the no-second-drifting-table guard: the catalog may only name model ids
    that the single registry already carries. A registry rename that orphans a
    catalog id raises here rather than drifting silently.

    Raises:
        ValueError: if a catalog ``model_id`` is absent from the registry, or if any
            ``model_id`` is a ``claude-*`` id (the GPT-only invariant).
    """
    known = _known_codex_ids()
    for harness, options in _CATALOG.items():
        for option in options:
            if option.model_id.startswith("claude-"):
                raise ValueError(
                    f"Layer-2 catalog for {harness!r} names a Claude id "
                    f"{option.model_id!r}; Layer-2 is GPT-only (ADR-B)"
                )
            if option.model_id not in known:
                raise ValueError(
                    f"Layer-2 catalog for {harness!r} names {option.model_id!r}, "
                    "which is not a codex_id in model_registry.REGISTRY"
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
    same model id remain individually selectable (``gpt-5.5:high`` vs ``gpt-5.5:medium``).
    Order matches :func:`options_for`.
    """
    return tuple(f"{opt.model_id}:{opt.effort}" for opt in options_for(harness))


def validate(harness: str, model: str) -> HarnessModelOption:
    """Resolve a ``(harness, model)`` selection to its discrete option.

    *model* is matched against each option's ``"<model_id>:<effort>"`` choice string
    (the canonical CLI form) and, as a convenience, against a bare ``model_id`` **only
    when that id is unambiguous** for the harness (exactly one effort). This keeps the
    common ``gpt-5.3-codex`` case ergonomic while forcing the ambiguous ``gpt-5.5`` to
    be disambiguated by effort.

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
