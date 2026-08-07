"""AC-2 — the typed core harness registry is the single roster source (v0.1.58 T-58-11).

Covers:
* the canonical L1 entry roster and the projection/install vocabularies;
* the capability predicate ``is_l1``;
* ``parse_harness_set`` (``all`` / comma-subset / bad-name-listing-error);
* a grep proving the tuple/set roster literals are GONE from the repointed sites.

The grep is the enforcement behind AC-9(a): reverting any repointed site to a bare
roster literal re-introduces the forbidden substring and fails this test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import (
    INSTALL_TARGETS,
    L1_ENTRY_HARNESSES,
    PROJECTION_TARGETS,
    is_l1,
    parse_harness_set,
)

pytestmark = pytest.mark.unit

_PKG = Path(__file__).resolve().parents[3] / "dadaia_workspace"


# ---------------------------------------------------------------------------
# Rosters + vocabularies golden.
# ---------------------------------------------------------------------------


def test_roster_vocabulary_golden() -> None:
    assert L1_ENTRY_HARNESSES == ("claude", "codex", "pi", "kimi-code")
    assert PROJECTION_TARGETS == ("agents", "claude", "codex", "pi", "kimi-code")
    assert ("agents", *L1_ENTRY_HARNESSES) == PROJECTION_TARGETS
    assert frozenset({"all", "agents", "claude", "codex", "pi", "kimi-code"}) == INSTALL_TARGETS
    assert frozenset({"all", *PROJECTION_TARGETS}) == INSTALL_TARGETS


# ---------------------------------------------------------------------------
# Capability predicates.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("harness", "expect_l1"),
    [
        ("claude", True),
        ("codex", True),
        ("pi", True),
        ("kimi-code", True),
        ("bogus", False),
        ("fake", False),
        ("opencode", False),
        ("", False),
    ],
)
def test_capability_predicates_table(harness: str, expect_l1: bool) -> None:
    assert is_l1(harness) is expect_l1


# ---------------------------------------------------------------------------
# parse_harness_set ACCEPT paths.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("all", ("claude", "codex", "pi", "kimi-code")),
        ("codex,pi", ("codex", "pi")),
        # input order does not leak — result is always canonical L1 order.
        ("kimi-code,pi,codex", ("codex", "pi", "kimi-code")),
        ("claude", ("claude",)),
        (" PI , pi ", ("pi",)),
        ("CLAUDE,Codex", ("claude", "codex")),
        ("Kimi-Code", ("kimi-code",)),
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
# Grep — roster literals are gone from all remaining repointed sites.
# ---------------------------------------------------------------------------

# Each site maps to (spaceless forbidden roster literal, required registry reference).
_L1_SITES: dict[str, tuple[str, str]] = {
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


def test_roster_literal_absent_and_registry_consumed() -> None:
    """AC-2 / AC-9(a): each repointed site has NO bare roster literal, and DOES consume
    the registry. Reverting a site to a hard-coded roster tuple/set fails this test."""
    for rel, (forbidden, required) in _L1_SITES.items():
        source = (_PKG / rel).read_text(encoding="utf-8")
        spaceless = source.replace(" ", "")
        assert forbidden not in spaceless, (
            f"{rel} still carries the bare roster literal {forbidden!r} — it must resolve "
            "through core/harness_registry (v0.1.58 FR1)."
        )
        assert required in source, f"{rel} does not consume the registry (missing {required!r})."
