"""AC-2 — the typed core harness registry is the single roster source (v0.1.58 T-58-11).

Covers:
* the canonical L1 entry roster and the projection vocabulary;
* ``parse_harness_name`` (the one registered name / bad-name-listing-error);
* a grep proving the tuple/set roster literals are GONE from the repointed sites.

The grep is the enforcement behind AC-9(a): reverting any repointed site to a bare
roster literal re-introduces the forbidden substring and fails this test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import (
    L1_ENTRY_HARNESSES,
    PROJECTION_TARGETS,
    parse_harness_name,
)

pytestmark = pytest.mark.unit

_PKG = Path(__file__).resolve().parents[3] / "dadaia_workspace"


# ---------------------------------------------------------------------------
# Rosters + vocabularies golden.
# ---------------------------------------------------------------------------


def test_roster_vocabulary_golden() -> None:
    roster = ("claude", "codex", "kimi-code", "cursor", "devin", "copilot")
    assert roster == L1_ENTRY_HARNESSES
    assert ("agents", *roster) == PROJECTION_TARGETS
    assert ("agents", *L1_ENTRY_HARNESSES) == PROJECTION_TARGETS


# ---------------------------------------------------------------------------
# parse_harness_name — exactly one registered record (0.4.7 T-047-73: `all` and the
# comma subset are gone; `dadaia harness add` is how a second harness enters).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("claude", "claude"),
        ("  codex  ", "codex"),
        ("Kimi-Code", "kimi-code"),
    ],
)
def test_parse_harness_name_accept_table(raw: str, expected: str) -> None:
    assert parse_harness_name(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["bogus", "all", "codex,kimi-code", "", "  ,  "],
)
def test_parse_harness_name_reject_table(raw: str) -> None:
    with pytest.raises(ValueError) as exc:
        parse_harness_name(raw)
    msg = str(exc.value)
    assert repr(raw) in msg
    for registered in ("claude", "codex", "kimi-code"):
        assert registered in msg


# ---------------------------------------------------------------------------
# Grep — roster literals are gone from all remaining repointed sites.
# ---------------------------------------------------------------------------

# Each site maps to (spaceless forbidden roster literal, required registry reference).
_L1_SITES: dict[str, tuple[str, str]] = {
    # 0.4.7 T-047-72: install/doctor scope on the PROFILE roster, so the site consumes
    # the L1 roster directly.
    "infrastructure/public_assets.py": (
        '("agents","claude","codex","pi")',
        "L1_ENTRY_HARNESSES",
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
