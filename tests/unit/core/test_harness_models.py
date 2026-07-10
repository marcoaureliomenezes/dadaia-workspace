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

# ---------------------------------------------------------------------------
# HARD invariants kept standalone: no claude-* anywhere in a Layer-2 catalog, and
# every catalog id resolves via the registry-codex|allowlist union.
# ---------------------------------------------------------------------------


def test_gpt_only_invariant_no_claude_id_anywhere() -> None:
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


# ---------------------------------------------------------------------------
# Catalog golden: counts, exact confirmed sets, model_choices pairs, the T-44-11/12
# OpenRouter opening (pi contains it, codex is unchanged).
# ---------------------------------------------------------------------------


def test_catalog_golden() -> None:
    # v0.1.44: pi opened to the curated OpenRouter set (moonshotai/kimi-k2.5), so 3 → 4.
    assert len(options_for(PI_HARNESS)) == 4
    assert len(options_for(CODEX_HARNESS)) == 2

    assert options_for(PI_HARNESS) == (
        HarnessModelOption("gpt-5.5", "high"),
        HarnessModelOption("gpt-5.5", "low"),
        HarnessModelOption("gpt-5.3-codex", "medium"),
        HarnessModelOption("moonshotai/kimi-k2.5", "high"),
    )
    assert options_for(CODEX_HARNESS) == (
        HarnessModelOption("gpt-5.5", "high"),
        HarnessModelOption("gpt-5.5", "medium"),
    )

    assert model_choices(CODEX_HARNESS) == ("gpt-5.5:high", "gpt-5.5:medium")
    assert model_choices(PI_HARNESS) == (
        "gpt-5.5:high",
        "gpt-5.5:low",
        "gpt-5.3-codex:medium",
        "moonshotai/kimi-k2.5:high",
    )

    # T-44-12: the curated OpenRouter id is a present, selectable pi option.
    assert HarnessModelOption("moonshotai/kimi-k2.5", "high") in options_for(PI_HARNESS)
    # T-44-11: the codex catalog is NOT opened — codex runs only on registry codex ids.
    assert all(opt.model_id != "moonshotai/kimi-k2.5" for opt in options_for(CODEX_HARNESS))


# ---------------------------------------------------------------------------
# validate() ACCEPT paths.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("harness", "model", "expected"),
    [
        (PI_HARNESS, "gpt-5.5:high", HarnessModelOption("gpt-5.5", "high")),
        (PI_HARNESS, "gpt-5.5:low", HarnessModelOption("gpt-5.5", "low")),
        (PI_HARNESS, "gpt-5.3-codex:medium", HarnessModelOption("gpt-5.3-codex", "medium")),
        (CODEX_HARNESS, "gpt-5.5:high", HarnessModelOption("gpt-5.5", "high")),
        (CODEX_HARNESS, "gpt-5.5:medium", HarnessModelOption("gpt-5.5", "medium")),
        # A bare id with a single effort resolves without the ":effort" suffix.
        (PI_HARNESS, "gpt-5.3-codex", HarnessModelOption("gpt-5.3-codex", "medium")),
        # The OpenRouter id validates via the union, both suffixed and bare.
        (
            PI_HARNESS,
            "moonshotai/kimi-k2.5:high",
            HarnessModelOption("moonshotai/kimi-k2.5", "high"),
        ),
        (PI_HARNESS, "moonshotai/kimi-k2.5", HarnessModelOption("moonshotai/kimi-k2.5", "high")),
    ],
)
def test_validate_accept_table(harness: str, model: str, expected: HarnessModelOption) -> None:
    assert validate(harness, model) == expected


# ---------------------------------------------------------------------------
# validate() REJECT paths.
# ---------------------------------------------------------------------------


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


def test_options_for_unknown_harness_is_empty() -> None:
    assert options_for("nonexistent") == ()


# ---------------------------------------------------------------------------
# T-44-11 (AC-5, R6) — Layer-2-native model allowlist law.
# ---------------------------------------------------------------------------


def test_layer2_allowlist_law() -> None:
    # The allowlist is a minimal, explicitly-named set (no wildcard) — this release:
    # moonshotai/kimi-k2.5.
    assert set(harness_models.LAYER2_EXTRA_MODEL_IDS) == {"moonshotai/kimi-k2.5"}

    # The single public membership helper unions registry codex ids with the allowlist.
    known = harness_models.known_layer2_model_ids()
    for entry in REGISTRY:
        assert entry.codex_id in known
    assert "moonshotai/kimi-k2.5" in known
    assert known == frozenset(e.codex_id for e in REGISTRY) | harness_models.LAYER2_EXTRA_MODEL_IDS

    # R6: the OpenRouter ids are NOT inserted into model_registry.REGISTRY.
    codex_ids = {entry.codex_id for entry in REGISTRY}
    assert "moonshotai/kimi-k2.5" not in codex_ids
    assert all(not entry.codex_id.startswith("kimi") for entry in REGISTRY)

    # R6: the codex runtime hot path (codex_tier_views) still resolves with no
    # ValueError, and no tier collapsed onto a fabricated OpenRouter id.
    from dadaia_workspace.core.model_registry import codex_tier_views

    views = codex_tier_views()
    assert len(views) >= 1
    assert all(view.codex_id != "moonshotai/kimi-k2.5" for view in views)

    # _assert_ids_known accepts an allowlisted OpenRouter id.
    accept_catalog = {PI_HARNESS: (HarnessModelOption("moonshotai/kimi-k2.5", "high"),)}
    with mock.patch.object(harness_models, "_CATALOG", accept_catalog):
        harness_models._assert_ids_known()  # must not raise

    # _assert_ids_known rejects a claude-* id even present in the union (the no-claude
    # safety bound is retained).
    claude_catalog = {PI_HARNESS: (HarnessModelOption("claude-opus-4-8", "high"),)}
    with (
        mock.patch.object(harness_models, "_CATALOG", claude_catalog),
        pytest.raises(ValueError) as claude_exc,
    ):
        harness_models._assert_ids_known()
    assert "claude" in str(claude_exc.value).lower()

    # _assert_ids_known rejects an id present in neither the registry nor the
    # allowlist.
    unknown_catalog = {PI_HARNESS: (HarnessModelOption("totally-unknown-9.9", "high"),)}
    with (
        mock.patch.object(harness_models, "_CATALOG", unknown_catalog),
        pytest.raises(ValueError) as unknown_exc,
    ):
        harness_models._assert_ids_known()
    assert "allowlist" in str(unknown_exc.value).lower()
