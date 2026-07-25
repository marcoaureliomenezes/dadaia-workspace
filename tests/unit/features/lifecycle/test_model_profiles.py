"""Unit tests for the built-in model-profile registry (T-28-A-02).

The registry layers **named** profiles over the discrete ``core.harness_models``
catalog. Every profile resolves to a real ``HarnessModelOption`` (asserted at import
time, mirroring ``harness_models._assert_ids_known``), so the registry can never become
a second drifting model table. D-2: built-in profiles only; no ``claude-*`` id; a
deprecated profile must carry a ``replacement``.

CRITICAL: no-claude-Layer-2 residue; kimi pin (OpenRouter rejects the old literal — keep the
exact id assert).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core import harness_models
from dadaia_workspace.core.harness_models import HarnessModelOption
from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.model_profiles import UnknownProfileError
from dadaia_workspace.features.telemetry.pricing import PRICING_TABLE

# ---------------------------------------------------------------------------
# ① registry↔catalog invariants param
# ---------------------------------------------------------------------------


def test_registry_catalog_invariants() -> None:
    """Every-profile-resolves + to_option round-trip + unique-ids + deprecated-carries-
    replacement + non-empty built-in — all iterate the same registry, one invariants fn."""
    profiles = model_profiles.list_profiles()
    assert profiles, "registry must ship at least one built-in profile"
    assert all(p.source == "built-in" for p in profiles)

    ids = [p.id for p in profiles]
    assert len(ids) == len(set(ids)), "profile ids must be unique"

    for profile in profiles:
        # No second drifting table: each profile's (model_id, effort) is a real catalog option.
        options = harness_models.options_for(profile.harness)
        assert HarnessModelOption(profile.model_id, profile.effort) in options, (
            f"profile {profile.id!r} does not resolve to a {profile.harness} catalog option"
        )
        if profile.deprecated:
            assert profile.replacement, (
                f"deprecated profile {profile.id!r} must declare a replacement"
            )
            model_profiles.resolve(profile.replacement)  # the replacement is itself known

    resolved = model_profiles.resolve("codex-review-deep")
    option = model_profiles.to_option(resolved)
    assert option in harness_models.options_for("codex")
    assert option.model_id == resolved.model_id
    assert option.effort == resolved.effort

    with pytest.raises(UnknownProfileError) as exc:
        model_profiles.resolve("does-not-exist")
    assert "does-not-exist" in str(exc.value)  # actionable message lists valid ids


# ---------------------------------------------------------------------------
# ② Layer-2 residue: no claude-* id + harness ∈ {codex, pi}
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ③ profiles_for filter / coverage / unknown-empty
# ---------------------------------------------------------------------------


def test_profiles_for_filters_covers_both_harnesses_and_unknown_is_empty() -> None:
    # ② Layer-2 residue: no claude-* id + harness in {codex, pi}.
    for profile in model_profiles.list_profiles():
        assert not profile.model_id.startswith("claude-")
        assert profile.harness in {"codex", "pi"}

    harnesses = {p.harness for p in model_profiles.list_profiles()}
    assert "codex" in harnesses
    assert "pi" in harnesses

    codex = model_profiles.profiles_for("codex")
    assert codex
    assert all(p.harness == "codex" for p in codex)
    pi = model_profiles.profiles_for("pi")
    assert pi
    assert all(p.harness == "pi" for p in pi)

    assert model_profiles.profiles_for("fake") == ()
    assert model_profiles.profiles_for("nonsense") == ()


# ---------------------------------------------------------------------------
# CRITICAL keep — kimi OpenRouter governed pin
# ---------------------------------------------------------------------------


def test_openrouter_kimi_profile_is_a_governed_pi_option() -> None:
    """v0.1.45 T-45-06: the OpenRouter kimi option is selectable via a governed pi profile.

    The picker persists PROFILE IDS (the resolver rejects a raw
    ``moonshotai/kimi-k2.5:high`` override), so kimi becomes end-to-end selectable only
    through a built-in profile. The profile resolves to the discrete pi catalog option
    ``moonshotai/kimi-k2.5:high`` — passing the no-second-table guard because that
    option already lives in ``options_for('pi')`` and its id is in
    ``known_layer2_model_ids()`` (v0.1.44).

    v0.1.66 FR3: the pinned id is a **deliberate pin update** — the prior
    ``kimi-2.7`` literal was itself the bug (OpenRouter rejects it); the valid,
    namespaced id is ``moonshotai/kimi-k2.5``.
    """
    profile = model_profiles.resolve("pi-openrouter-kimi-high")
    assert profile.harness == "pi"
    assert profile.model_id == "moonshotai/kimi-k2.5"
    assert profile.effort == "high"
    # Governed: resolves to a real pi catalog option (never a second drifting table).
    option = model_profiles.to_option(profile)
    assert option in harness_models.options_for("pi")
    assert option == HarnessModelOption("moonshotai/kimi-k2.5", "high")
    # It surfaces in the per-harness picker source (profiles_for drives the pi dropdown).
    assert profile in model_profiles.profiles_for("pi")


def test_pi_gpt_profiles_use_codex_subscription_ids() -> None:
    pi_gpt_profiles = [
        profile
        for profile in model_profiles.profiles_for("pi")
        if "gpt" in profile.model_id.lower()
    ]
    assert pi_gpt_profiles
    assert all(profile.model_id.startswith("openai-codex/") for profile in pi_gpt_profiles)
    assert {profile.id for profile in pi_gpt_profiles} == {
        "pi-implementation-standard",
        "pi-reasoning-high",
        "pi-reasoning-low",
    }


def test_terra_profile_is_a_governed_codex_option() -> None:
    """v0.2.9 follow-up: gpt-5.6-terra (medium reasoning) is selectable via a governed
    codex profile — the fallback for workspaces whose gpt-5.3-codex-spark credit is
    exhausted. Resolves to the discrete codex catalog option.

    The operator codex remap made terra ALSO the plugin-tier ``codex_id``, retiring the
    former "terra is never a registry codex_id" pin. The two protections that pin
    actually bought are asserted directly instead, so retiring it costs no coverage:
    terra resolves no pricing row of its own (``PRICING_TABLE`` is keyed by
    ``claude_id``), and it collapses no tier (``codex_tier_views`` stays injective on
    the ``(codex_id, effort)`` pair — pinned by its own test).
    """
    profile = model_profiles.resolve("codex-implementation-terra")
    assert profile.harness == "codex"
    assert profile.model_id == "gpt-5.6-terra"
    assert profile.effort == "medium"
    option = model_profiles.to_option(profile)
    assert option in harness_models.options_for("codex")
    assert option == HarnessModelOption("gpt-5.6-terra", "medium")
    assert "gpt-5.6-terra" in harness_models.known_layer2_model_ids()
    # Reachable through BOTH sets now — and still listed in the curated Layer-2
    # allowlist, which ``json_local_model_profile_store`` validates against WITHOUT the
    # registry codex ids (dropping it would revoke the credit-exhaustion escape hatch).
    assert "gpt-5.6-terra" in {entry.codex_id for entry in harness_models.REGISTRY}
    assert "gpt-5.6-terra" in harness_models.LAYER2_EXTRA_MODEL_IDS
    # No fabricated pricing: the pricing table is keyed by claude_id, so a codex id
    # never resolves a row of its own.
    assert "gpt-5.6-terra" not in PRICING_TABLE
    assert profile in model_profiles.profiles_for("codex")
