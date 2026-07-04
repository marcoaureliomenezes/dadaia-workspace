"""AC-2 — the typed core harness registry is the single roster source (v0.1.58 T-58-11).

Covers:
* the canonical L1 entry / L2 worker rosters and the projection/install vocabularies;
* the capability predicates (``claude`` is L1-only — never a Layer-2 worker);
* ``parse_harness_set`` (``all`` / comma-subset / bad-name-listing-error);
* the R1 order-independent contract that ``L2_WORKER_HARNESSES`` and the Layer-2 model
  catalog (``harness_models.harnesses()``) never fork — reconciling the derived
  ``model_profiles.py`` site that is NOT repointed;
* a grep proving the tuple/set roster literals are GONE from all 7 repointed sites (4 L1 +
  3 L2) and that the derived ``model_profiles`` site still derives (not a bare literal).

The grep is the enforcement behind AC-9(a) / (a′): reverting any repointed site to a bare
roster literal re-introduces the forbidden substring and fails this test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core import harness_models
from dadaia_workspace.core.harness_registry import (
    INSTALL_TARGETS,
    L1_ENTRY_HARNESSES,
    L2_WORKER_HARNESSES,
    PROJECTION_TARGETS,
    can_be_workflow_worker,
    is_l1,
    is_l2,
    parse_harness_set,
)

pytestmark = pytest.mark.unit

_PKG = Path(__file__).resolve().parents[3] / "dadaia_workspace"


# ---------------------------------------------------------------------------
# Rosters + vocabularies
# ---------------------------------------------------------------------------


def test_l1_entry_roster_is_canonical() -> None:
    assert L1_ENTRY_HARNESSES == ("claude", "codex", "pi")


def test_l2_worker_roster_is_canonical() -> None:
    assert L2_WORKER_HARNESSES == ("codex", "pi")


def test_projection_targets_are_agents_plus_l1() -> None:
    assert PROJECTION_TARGETS == ("agents", "claude", "codex", "pi")
    assert ("agents", *L1_ENTRY_HARNESSES) == PROJECTION_TARGETS


def test_install_targets_are_projection_plus_all() -> None:
    assert frozenset({"all", "agents", "claude", "codex", "pi"}) == INSTALL_TARGETS
    assert frozenset({"all", *PROJECTION_TARGETS}) == INSTALL_TARGETS


# ---------------------------------------------------------------------------
# Capability predicates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("harness", ["claude", "codex", "pi"])
def test_is_l1_true_for_entry_harnesses(harness: str) -> None:
    assert is_l1(harness) is True


@pytest.mark.parametrize("harness", ["bogus", "fake", "opencode", ""])
def test_is_l1_false_for_non_entry(harness: str) -> None:
    assert is_l1(harness) is False


def test_claude_is_never_layer2() -> None:
    assert is_l2("claude") is False
    assert can_be_workflow_worker("claude") is False


@pytest.mark.parametrize("harness", ["codex", "pi"])
def test_l2_workers(harness: str) -> None:
    assert is_l2(harness) is True
    assert can_be_workflow_worker(harness) is True


# ---------------------------------------------------------------------------
# parse_harness_set
# ---------------------------------------------------------------------------


def test_parse_harness_set_all() -> None:
    assert parse_harness_set("all") == ("claude", "codex", "pi")


def test_parse_harness_set_subset_canonical_order() -> None:
    assert parse_harness_set("codex,pi") == ("codex", "pi")
    # input order does not leak — result is always canonical L1 order.
    assert parse_harness_set("pi,codex") == ("codex", "pi")


def test_parse_harness_set_single() -> None:
    assert parse_harness_set("claude") == ("claude",)


def test_parse_harness_set_dedup_and_whitespace_and_case() -> None:
    assert parse_harness_set(" PI , pi ") == ("pi",)
    assert parse_harness_set("CLAUDE,Codex") == ("claude", "codex")


def test_parse_harness_set_bogus_raises_with_listing() -> None:
    with pytest.raises(ValueError) as exc:
        parse_harness_set("bogus")
    msg = str(exc.value)
    assert "bogus" in msg
    # the message lists every valid harness (a listing error).
    assert "claude" in msg and "codex" in msg and "pi" in msg


def test_parse_harness_set_partial_unknown_raises() -> None:
    with pytest.raises(ValueError) as exc:
        parse_harness_set("claude,zzz")
    assert "zzz" in str(exc.value)


def test_parse_harness_set_empty_raises() -> None:
    with pytest.raises(ValueError):
        parse_harness_set("")
    with pytest.raises(ValueError):
        parse_harness_set("  ,  ")


# ---------------------------------------------------------------------------
# R1 contract — L2 roster ⇔ model catalog (order-independent)
# ---------------------------------------------------------------------------


def test_l2_roster_matches_model_catalog_as_set() -> None:
    """The identity L2 roster and the Layer-2 model catalog never fork (R1).

    ``harness_models.harnesses()`` is PI-first; ``L2_WORKER_HARNESSES`` keeps canonical
    order ``("codex", "pi")`` — so the contract is set-equality, not sequence-equality.
    """
    assert frozenset(L2_WORKER_HARNESSES) == frozenset(harness_models.harnesses())


# ---------------------------------------------------------------------------
# Grep — the roster literals are GONE from all 7 repointed sites
# ---------------------------------------------------------------------------

# Each site maps to (spaceless forbidden roster literal, required registry reference).
_L1_SITES: dict[str, tuple[str, str]] = {
    "features/panel/views/api_workflows.py": ('"claude","codex"', "is_l1("),
    "features/panel/views/api_agents.py": ('"claude","codex"', "is_l1("),
    "infrastructure/public_assets_common.py": (
        '{"all","agents","claude","codex","pi"}',
        "INSTALL_TARGETS",
    ),
    "infrastructure/public_assets.py": (
        '("agents","claude","codex","pi")',
        "PROJECTION_TARGETS",
    ),
}
_L2_SITES: dict[str, tuple[str, str]] = {
    "features/lifecycle/policy_doctor.py": ('frozenset({"codex","pi"})', "L2_WORKER_HARNESSES"),
    "features/lifecycle/policy_resolver.py": ('frozenset({"codex","pi"})', "L2_WORKER_HARNESSES"),
    "infrastructure/json_workflow_model_policy_store.py": (
        'frozenset({"codex","pi"})',
        "L2_WORKER_HARNESSES",
    ),
}


@pytest.mark.parametrize("rel", [*_L1_SITES, *_L2_SITES])
def test_roster_literal_absent_and_registry_consumed(rel: str) -> None:
    """AC-2 / AC-9(a,a′): each repointed site has NO bare roster literal, and DOES consume
    the registry. Reverting a site to a hard-coded roster tuple/set fails this test."""
    forbidden, required = ({**_L1_SITES, **_L2_SITES})[rel]
    source = (_PKG / rel).read_text(encoding="utf-8")
    spaceless = source.replace(" ", "")
    assert forbidden not in spaceless, (
        f"{rel} still carries the bare roster literal {forbidden!r} — it must resolve "
        "through core/harness_registry (v0.1.58 FR1)."
    )
    assert required in source, f"{rel} does not consume the registry (missing {required!r})."


def test_model_profiles_derived_site_is_reconciled_not_repointed() -> None:
    """The 4th ``_LAYER2_HARNESSES`` site (``model_profiles.py``) is DERIVED from the model
    catalog constants (reconciled by the R1 contract test), NOT repointed and NOT a bare
    literal."""
    source = (_PKG / "features/lifecycle/model_profiles.py").read_text(encoding="utf-8")
    spaceless = source.replace(" ", "")
    assert 'frozenset({"codex","pi"})' not in spaceless
    assert "harness_models.CODEX_HARNESS" in source
    assert "harness_models.PI_HARNESS" in source
