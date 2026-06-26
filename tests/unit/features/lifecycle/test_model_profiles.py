"""Unit tests for the built-in model-profile registry (T-28-A-02).

The registry layers **named** profiles over the discrete ``core.harness_models``
catalog. Every profile resolves to a real ``HarnessModelOption`` (asserted at import
time, mirroring ``harness_models._assert_ids_known``), so the registry can never become
a second drifting model table. D-2: built-in profiles only; no ``claude-*`` id; a
deprecated profile must carry a ``replacement``.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core import harness_models
from dadaia_workspace.core.harness_models import HarnessModelOption
from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.model_profiles import UnknownProfileError


def test_list_profiles_is_non_empty_and_built_in() -> None:
    profiles = model_profiles.list_profiles()
    assert profiles, "registry must ship at least one built-in profile"
    assert all(p.source == "built-in" for p in profiles)


def test_every_profile_model_id_resolves_to_an_option() -> None:
    # No second drifting table: each profile's (model_id, effort) is a real catalog option.
    for profile in model_profiles.list_profiles():
        options = harness_models.options_for(profile.harness)
        assert HarnessModelOption(profile.model_id, profile.effort) in options, (
            f"profile {profile.id!r} does not resolve to a {profile.harness} catalog option"
        )


def test_no_claude_model_id() -> None:
    for profile in model_profiles.list_profiles():
        assert not profile.model_id.startswith("claude-")


def test_no_claude_or_opencode_harness() -> None:
    for profile in model_profiles.list_profiles():
        assert profile.harness in {"codex", "pi"}


def test_profiles_cover_both_harnesses() -> None:
    harnesses = {p.harness for p in model_profiles.list_profiles()}
    assert "codex" in harnesses
    assert "pi" in harnesses


def test_profiles_for_filters_by_harness() -> None:
    codex = model_profiles.profiles_for("codex")
    assert codex
    assert all(p.harness == "codex" for p in codex)
    pi = model_profiles.profiles_for("pi")
    assert pi
    assert all(p.harness == "pi" for p in pi)


def test_profiles_for_unknown_harness_is_empty() -> None:
    assert model_profiles.profiles_for("fake") == ()
    assert model_profiles.profiles_for("nonsense") == ()


def test_resolve_returns_profile() -> None:
    profile = model_profiles.resolve("codex-implementation-standard")
    assert profile.harness == "codex"
    assert profile.model_id == "gpt-5.5"


def test_resolve_unknown_raises() -> None:
    with pytest.raises(UnknownProfileError) as exc:
        model_profiles.resolve("does-not-exist")
    # actionable message lists valid ids
    assert "does-not-exist" in str(exc.value)


def test_to_option_round_trips_to_catalog() -> None:
    profile = model_profiles.resolve("codex-review-deep")
    option = model_profiles.to_option(profile)
    assert option in harness_models.options_for("codex")
    assert option.model_id == profile.model_id
    assert option.effort == profile.effort


def test_deprecated_profiles_carry_replacement() -> None:
    for profile in model_profiles.list_profiles():
        if profile.deprecated:
            assert profile.replacement, (
                f"deprecated profile {profile.id!r} must declare a replacement"
            )
            # the replacement must itself be a known profile
            model_profiles.resolve(profile.replacement)


def test_profile_ids_are_unique() -> None:
    ids = [p.id for p in model_profiles.list_profiles()]
    assert len(ids) == len(set(ids))
