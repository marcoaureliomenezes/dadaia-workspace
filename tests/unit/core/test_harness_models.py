"""Unit tests for the discrete per-harness Layer-2 model catalog (T-24-04, WS-2).

LAW 2 (ADR-B): pi → 3 discrete options, codex → 2; both GPT-only (no ``claude-*``);
every catalog id is a ``codex_id`` in the single ``model_registry.REGISTRY``.
"""

from __future__ import annotations

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


def test_pi_has_exactly_three_options() -> None:
    assert len(options_for(PI_HARNESS)) == 3


def test_codex_has_exactly_two_options() -> None:
    assert len(options_for(CODEX_HARNESS)) == 2


def test_pi_catalog_is_the_confirmed_operator_set() -> None:
    assert options_for(PI_HARNESS) == (
        HarnessModelOption("gpt-5.5", "high"),
        HarnessModelOption("gpt-5.5", "low"),
        HarnessModelOption("gpt-5.3-codex", "medium"),
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


def test_every_catalog_id_exists_as_registry_codex_id() -> None:
    """No second drifting table: each catalog id is a registry ``codex_id``."""
    known = {entry.codex_id for entry in REGISTRY}
    for harness in harness_models.harnesses():
        for option in options_for(harness):
            assert option.model_id in known, f"{option.model_id} is not a codex_id in REGISTRY"


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
    )


def test_options_for_unknown_harness_is_empty() -> None:
    assert options_for("nonexistent") == ()
