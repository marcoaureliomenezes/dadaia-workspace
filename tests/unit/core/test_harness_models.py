"""Unit tests for the discrete per-harness Layer-2 model catalog (T-24-04, WS-2).

LAW 2 (v0.1.44, supersedes ADR-B): pi → 4 discrete options (incl. OpenRouter
``moonshotai/kimi-k2.5``), codex → 2; both allowlist-validated; never
``claude-*``. Every catalog id resolves via the union of ``model_registry.REGISTRY``
codex ids and the curated Layer-2 allowlist (``LAYER2_EXTRA_MODEL_IDS``).
"""

from __future__ import annotations

from unittest import mock

import pytest

from dadaia_workspace.core import harness_models
from dadaia_workspace.core.harness_models import (
    CODEX_HARNESS,
    PI_HARNESS,
    HarnessModelOption,
    model_choices,
    options_for,
    validate,
)
from dadaia_workspace.core.model_registry import REGISTRY


def test_pi_has_exactly_four_options() -> None:
    # v0.1.44: pi opened to the curated OpenRouter set (moonshotai/kimi-k2.5), so 3 → 4.
    assert len(options_for(PI_HARNESS)) == 4


def test_codex_has_exactly_two_options() -> None:
    assert len(options_for(CODEX_HARNESS)) == 2


def test_pi_catalog_is_the_confirmed_operator_set() -> None:
    assert options_for(PI_HARNESS) == (
        HarnessModelOption("gpt-5.5", "high"),
        HarnessModelOption("gpt-5.5", "low"),
        HarnessModelOption("gpt-5.3-codex", "medium"),
        HarnessModelOption("moonshotai/kimi-k2.5", "high"),
    )


def test_codex_catalog_is_the_confirmed_operator_set() -> None:
    assert options_for(CODEX_HARNESS) == (
        HarnessModelOption("gpt-5.5", "high"),
        HarnessModelOption("gpt-5.5", "medium"),
    )


def test_gpt_only_invariant_no_claude_id_anywhere() -> None:
    """The HARD invariant: no ``claude-*`` id appears in any Layer-2 catalog."""
    for harness in harness_models.harnesses():
        for option in options_for(harness):
            assert not option.model_id.startswith("claude-"), (
                f"{harness} catalog leaked a Claude id: {option.model_id}"
            )


def test_every_catalog_id_is_in_the_layer2_allowlist() -> None:
    """No second drifting table: each catalog id is in the registry-codex|allowlist union."""
    known = harness_models.known_layer2_model_ids()
    for harness in harness_models.harnesses():
        for option in options_for(harness):
            assert option.model_id in known, f"{option.model_id} is not in the Layer-2 allowlist"


@pytest.mark.parametrize(
    ("harness", "model", "expected"),
    [
        (PI_HARNESS, "gpt-5.5:high", HarnessModelOption("gpt-5.5", "high")),
        (PI_HARNESS, "gpt-5.5:low", HarnessModelOption("gpt-5.5", "low")),
        (PI_HARNESS, "gpt-5.3-codex:medium", HarnessModelOption("gpt-5.3-codex", "medium")),
        (CODEX_HARNESS, "gpt-5.5:high", HarnessModelOption("gpt-5.5", "high")),
        (CODEX_HARNESS, "gpt-5.5:medium", HarnessModelOption("gpt-5.5", "medium")),
    ],
)
def test_valid_pairs_resolve(harness: str, model: str, expected: HarnessModelOption) -> None:
    assert validate(harness, model) == expected


def test_unambiguous_bare_model_id_resolves() -> None:
    """A bare id with a single effort resolves without the ``:effort`` suffix."""
    assert validate(PI_HARNESS, "gpt-5.3-codex") == HarnessModelOption("gpt-5.3-codex", "medium")


def test_ambiguous_bare_model_id_is_rejected() -> None:
    """``gpt-5.5`` has two efforts for codex, so a bare id must not silently pick one."""
    with pytest.raises(ValueError) as exc:
        validate(CODEX_HARNESS, "gpt-5.5")
    assert "gpt-5.5:high" in str(exc.value)
    assert "gpt-5.5:medium" in str(exc.value)


def test_invalid_model_raises_with_valid_set_listed() -> None:
    with pytest.raises(ValueError) as exc:
        validate(PI_HARNESS, "gpt-9.9:high")
    message = str(exc.value)
    for choice in model_choices(PI_HARNESS):
        assert choice in message


def test_validate_for_harness_with_no_catalog_raises() -> None:
    with pytest.raises(ValueError) as exc:
        validate("fake", "gpt-5.5:high")
    assert "no discrete model catalog" in str(exc.value)


def test_model_choices_are_disambiguated_pairs() -> None:
    assert model_choices(CODEX_HARNESS) == ("gpt-5.5:high", "gpt-5.5:medium")
    assert model_choices(PI_HARNESS) == (
        "gpt-5.5:high",
        "gpt-5.5:low",
        "gpt-5.3-codex:medium",
        "moonshotai/kimi-k2.5:high",
    )


def test_options_for_unknown_harness_is_empty() -> None:
    assert options_for("nonexistent") == ()


# ---------------------------------------------------------------------------
# T-44-11 (AC-5, R6) — Layer-2-native model allowlist; REGISTRY untouched.
# ---------------------------------------------------------------------------


def test_layer2_extra_model_ids_is_the_curated_named_set() -> None:
    """The allowlist is a minimal, explicitly-named set (no wildcard) — this release: moonshotai/kimi-k2.5."""
    assert set(harness_models.LAYER2_EXTRA_MODEL_IDS) == {"moonshotai/kimi-k2.5"}


def test_known_layer2_model_ids_is_codex_union_extra() -> None:
    """The single public membership helper unions registry codex ids with the allowlist."""
    known = harness_models.known_layer2_model_ids()
    # contains every registry codex id ...
    for entry in REGISTRY:
        assert entry.codex_id in known
    # ... and the curated OpenRouter id.
    assert "moonshotai/kimi-k2.5" in known
    assert known == frozenset(e.codex_id for e in REGISTRY) | harness_models.LAYER2_EXTRA_MODEL_IDS


def test_registry_is_unchanged_by_harness_models_allowlist() -> None:
    """R6: the OpenRouter ids are NOT inserted into model_registry.REGISTRY."""
    codex_ids = {entry.codex_id for entry in REGISTRY}
    assert "moonshotai/kimi-k2.5" not in codex_ids
    # No registry entry was fabricated to carry the OpenRouter id.
    assert all(not entry.codex_id.startswith("kimi") for entry in REGISTRY)


def test_codex_tier_views_does_not_raise_with_allowlist_present() -> None:
    """R6: the codex runtime hot path (codex_tier_views) still resolves with no ValueError."""
    from dadaia_workspace.core.model_registry import codex_tier_views

    views = codex_tier_views()
    assert len(views) >= 1
    # No tier collapsed onto a fabricated OpenRouter id.
    assert all(view.codex_id != "moonshotai/kimi-k2.5" for view in views)


# ---------------------------------------------------------------------------
# T-44-12 (AC-5) — pi catalog opened; invariant relaxed to the allowlist union.
# ---------------------------------------------------------------------------


def test_pi_catalog_contains_the_openrouter_option() -> None:
    """The curated OpenRouter id is a present, selectable pi option, validated via the union."""
    assert HarnessModelOption("moonshotai/kimi-k2.5", "high") in options_for(PI_HARNESS)
    assert validate(PI_HARNESS, "moonshotai/kimi-k2.5:high") == HarnessModelOption(
        "moonshotai/kimi-k2.5", "high"
    )
    assert validate(PI_HARNESS, "moonshotai/kimi-k2.5") == HarnessModelOption(
        "moonshotai/kimi-k2.5", "high"
    )


def test_codex_catalog_unchanged_no_openrouter_id() -> None:
    """The codex catalog is NOT opened — codex runs only on registry codex ids."""
    assert all(opt.model_id != "moonshotai/kimi-k2.5" for opt in options_for(CODEX_HARNESS))


def test_assert_ids_known_accepts_openrouter_id_via_union() -> None:
    """The relaxed invariant accepts an allowlisted OpenRouter id."""
    catalog = {PI_HARNESS: (HarnessModelOption("moonshotai/kimi-k2.5", "high"),)}
    with mock.patch.object(harness_models, "_CATALOG", catalog):
        harness_models._assert_ids_known()  # must not raise


def test_assert_ids_known_rejects_claude_id_even_in_union() -> None:
    """The no-claude safety bound is retained — a claude-* id still raises."""
    catalog = {PI_HARNESS: (HarnessModelOption("claude-opus-4-8", "high"),)}
    with (
        mock.patch.object(harness_models, "_CATALOG", catalog),
        pytest.raises(ValueError) as exc,
    ):
        harness_models._assert_ids_known()
    assert "claude" in str(exc.value).lower()


def test_assert_ids_known_rejects_id_outside_union() -> None:
    """An id present in neither the registry nor the allowlist still raises."""
    catalog = {PI_HARNESS: (HarnessModelOption("totally-unknown-9.9", "high"),)}
    with (
        mock.patch.object(harness_models, "_CATALOG", catalog),
        pytest.raises(ValueError) as exc,
    ):
        harness_models._assert_ids_known()
    assert "allowlist" in str(exc.value).lower()
