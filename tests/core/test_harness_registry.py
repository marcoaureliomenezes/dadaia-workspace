"""AC-2 (v0.1.58 T-58-11): the typed core harness registry is the single
roster source; ``parse_harness_name`` accepts exactly one registered name (0.4.7 T-047-73)."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.harness_registry import (
    L1_ENTRY_HARNESSES,
    PROJECTION_TARGETS,
    parse_harness_name,
)


def test_roster_vocabulary_golden() -> None:
    roster = ("claude", "codex", "kimi-code", "cursor", "devin", "copilot")
    assert roster == L1_ENTRY_HARNESSES
    assert ("agents", *roster) == PROJECTION_TARGETS


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("claude", "claude"),
        ("  codex  ", "codex"),
        ("Kimi-Code", "kimi-code"),
    ],
)
def test_parse_harness_name_accept_table(raw: str, expected: str) -> None:
    """A registered name, trimmed and case-folded, parses."""
    assert parse_harness_name(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["bogus", "all", "codex,kimi-code", "", "  ,  "],
)
def test_parse_harness_name_reject_table(raw: str) -> None:
    """``all``, a comma subset or an unknown name is refused, listing the registered names."""
    with pytest.raises(ValueError) as exc:
        parse_harness_name(raw)
    msg = str(exc.value)
    assert repr(raw) in msg
    for registered in ("claude", "codex", "kimi-code"):
        assert registered in msg
