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
# R1 contract — L2 roster ⇔ model catalog (order-independent) standalone.
# ---------------------------------------------------------------------------


def test_l2_roster_matches_model_catalog_as_set() -> None:
    """The identity L2 roster and the Layer-2 model catalog never fork (R1).

    ``harness_models.harnesses()`` is PI-first; ``L2_WORKER_HARNESSES`` keeps canonical
    order ``("codex", "pi")`` — so the contract is set-equality, not sequence-equality.
    """
    assert frozenset(L2_WORKER_HARNESSES) == frozenset(harness_models.harnesses())


# ---------------------------------------------------------------------------
# Rosters + vocabularies golden.
# ---------------------------------------------------------------------------


def test_roster_vocabulary_golden() -> None:
    assert L1_ENTRY_HARNESSES == ("claude", "codex", "pi")
    assert L2_WORKER_HARNESSES == ("codex", "pi")
    assert PROJECTION_TARGETS == ("agents", "claude", "codex", "pi")
    assert ("agents", *L1_ENTRY_HARNESSES) == PROJECTION_TARGETS
    assert frozenset({"all", "agents", "claude", "codex", "pi"}) == INSTALL_TARGETS
    assert frozenset({"all", *PROJECTION_TARGETS}) == INSTALL_TARGETS


# ---------------------------------------------------------------------------
# Capability predicates.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("harness", "expect_l1", "expect_l2", "expect_worker"),
    [
        ("claude", True, False, False),
        ("codex", True, True, True),
        ("pi", True, True, True),
        ("bogus", False, False, False),
        ("fake", False, False, False),
        ("opencode", False, False, False),
        ("", False, False, False),
    ],
)
def test_capability_predicates_table(
    harness: str, expect_l1: bool, expect_l2: bool, expect_worker: bool
) -> None:
    assert is_l1(harness) is expect_l1
    assert is_l2(harness) is expect_l2
    assert can_be_workflow_worker(harness) is expect_worker


# ---------------------------------------------------------------------------
# parse_harness_set ACCEPT paths.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("all", ("claude", "codex", "pi")),
        ("codex,pi", ("codex", "pi")),
        # input order does not leak — result is always canonical L1 order.
        ("pi,codex", ("codex", "pi")),
        ("claude", ("claude",)),
        (" PI , pi ", ("pi",)),
        ("CLAUDE,Codex", ("claude", "codex")),
    ],
)
def test_parse_harness_set_accept_table(raw: str, expected: tuple[str, ...]) -> None:
    assert parse_harness_set(raw) == expected


# ---------------------------------------------------------------------------
# parse_harness_set REJECT paths.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expect_in_message"),
    [
        ("bogus", ["bogus", "claude", "codex", "pi"]),
        ("claude,zzz", ["zzz"]),
        ("", []),
        ("  ,  ", []),
    ],
)
def test_parse_harness_set_reject_table(raw: str, expect_in_message: list[str]) -> None:
    with pytest.raises(ValueError) as exc:
        parse_harness_set(raw)
    msg = str(exc.value)
    for fragment in expect_in_message:
        assert fragment in msg


# ---------------------------------------------------------------------------
# Grep — the roster literals are GONE from all 7 repointed sites, and the derived
# model_profiles site still derives (not a bare literal).
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


def test_roster_literal_absent_registry_consumed_and_model_profiles_derives() -> None:
    """AC-2 / AC-9(a,a′): each repointed site has NO bare roster literal, and DOES consume
    the registry. Reverting a site to a hard-coded roster tuple/set fails this test. The
    4th ``_LAYER2_HARNESSES`` site (``model_profiles.py``) is DERIVED from the model
    catalog constants (reconciled by the R1 contract test above), NOT repointed and NOT a
    bare literal."""
    for rel, (forbidden, required) in {**_L1_SITES, **_L2_SITES}.items():
        source = (_PKG / rel).read_text(encoding="utf-8")
        spaceless = source.replace(" ", "")
        assert forbidden not in spaceless, (
            f"{rel} still carries the bare roster literal {forbidden!r} — it must resolve "
            "through core/harness_registry (v0.1.58 FR1)."
        )
        assert required in source, f"{rel} does not consume the registry (missing {required!r})."

    profiles_source = (_PKG / "features/lifecycle/model_profiles.py").read_text(encoding="utf-8")
    spaceless_profiles = profiles_source.replace(" ", "")
    assert 'frozenset({"codex","pi"})' not in spaceless_profiles
    assert "harness_models.CODEX_HARNESS" in profiles_source
    assert "harness_models.PI_HARNESS" in profiles_source
