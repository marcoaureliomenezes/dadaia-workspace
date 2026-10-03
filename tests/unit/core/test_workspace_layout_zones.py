"""Intent: CONTRACT — 0.4.6 AC1 (FR1: the zone registry's rows and its derived views); size: SMALL.

Expected values come from SPEC §3/§4 (FR1, FR5, FR8) and architect A, never from the
module under test: the 12 rows in order (ADRs 0147 (1), 0148 (6)), the three TTL zones
(handoff and tmp a day, reaped seven days), the three closed canons, the creators per zone, and the pure exception-glob parser.
"""

from __future__ import annotations

import dataclasses

import pytest

from dadaia_workspace.core import workspace_layout as wl

C, K = wl.Creator, wl.ZoneClass
#: SPEC FR1/FR5/FR8 + architect A: (name, class, creator, ttl seconds), in registry order.
_SPEC_ZONES = [
    ("agentic", K.PROJECTION, C.INSTALL, None),
    ("hooks", K.PROJECTION, C.INSTALL, None),
    ("states", K.STATE, C.INIT, None),
    ("sessions", K.PROTECTED, C.RUNTIME, None),
    ("handoff", K.OUTPUT, C.RUNTIME, 86_400),
    ("reports", K.OUTPUT, C.RUNTIME, None),
    ("tmp", K.EPHEMERAL, C.RUNTIME, 86_400),
    ("reaped", K.EPHEMERAL, C.RUNTIME, 604_800),
    ("dist", K.STATE, C.RUNTIME, None),
    ("mcps", K.OPERATOR, C.OPERATOR, None),
    ("references", K.OPERATOR, C.OPERATOR, None),
    (".venv", K.MANAGED, C.INIT, None),
]
_SPEC_STATES_CANON = {
    "spec_contexts.json",
    "server_registry.json",
    "install_ledger.json",
    "agent_model_policy.json",
    "agent_model_policy.json.last-good.json",
    "privacy_denylist.json",
    "harness_profile.json",
    "AGENTS.md",
}


def test_registry_holds_the_twelve_spec_zones_in_order() -> None:
    """sa-tool-caches-land-outside-the-cache-zone#B40-2: no .cache zone (ADR 0080); 0.4.7 FR6b:
    ``reaped/`` is its own row held 7 days, never a TTL override inside ``tmp``."""
    rows = [(z.name, z.cls, z.creator, z.ttl_seconds) for z in wl.DADAIA_ZONES]
    assert rows == _SPEC_ZONES
    assert wl.zone_names() == frozenset(name for name, *_ in _SPEC_ZONES)
    with pytest.raises(dataclasses.FrozenInstanceError):
        wl.DADAIA_ZONES[0].ttl_seconds = 1  # type: ignore[misc]


def test_derived_views_follow_the_registry() -> None:
    """TTL, canon, walked, additive and table views are projections of the one registry."""
    assert [z.name for z in wl.zones_with_ttl()] == ["handoff", "tmp", "reaped"]
    assert {z.name: z.canon for z in wl.zones_with_canon()} == {
        "states": frozenset(_SPEC_STATES_CANON),
        "sessions": frozenset({"*.json"}),
        "dist": frozenset({"spec-contexts.json"}),
    }
    assert [z.name for z in wl.walked_zones()] == [name for name, *_ in _SPEC_ZONES[:9]]
    assert wl.additive_prefixes() == (
        ".dadaia/handoff/",
        ".dadaia/reports/",
        ".dadaia/tmp/",
        ".dadaia/reaped/",
    )
    rows = {row[0]: row for row in wl.zone_table_rows()}
    assert rows["tmp"][2:] == ("ephemeral", "86400", "runtime")
    assert rows["references"][2:] == ("operator", "never", "operator")
    assert frozenset({"AGENTS.md", ".gitignore"}) == wl.DADAIA_ROOT_FILES
    assert wl.DADAIAIGNORE in wl.ROOT_ALLOWED_FILES and "worktrees" in wl.ROOT_ALLOWED_DIRS
    # ADR 0133 SPEC risk: the floor is what init/install create, plus the CLI's PROTECTED zone
    zones = [z for z in wl.DADAIA_ZONES if z in wl.provisioned_zones() or z.cls is K.PROTECTED]
    made = {"AGENTS.md", *wl.LEVEL1_SEEDS, *(f".dadaia/{z.name}" for z in zones)}
    assert set(wl.CORE_FLOOR) <= made


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", (), id="empty"),
        pytest.param("# only a comment\n\n   \n", (), id="comments-and-blanks"),
        pytest.param("  *.iml \n.idea\n", ("*.iml", ".idea"), id="stripped-in-order"),
        pytest.param(
            ".idea\n# note\n.idea\n*.iml\n.idea", (".idea", "*.iml"), id="dedupe-keeps-first"
        ),
        pytest.param(
            # A directory glob written gitignore-style names the directory: ``fnmatch``
            # never matches a trailing slash, so the parser drops it (and dedupes across).
            "z_img/\n.playwright-mcp/\nz_img\n",
            ("z_img", ".playwright-mcp"),
            id="directory-slash-dropped",
        ),
    ],
)
def test_parse_dadaiaignore(text: str, expected: tuple[str, ...]) -> None:
    """``.dadaiaignore`` parses to stripped, deduped, slash-free root-relative patterns."""
    assert wl.parse_dadaiaignore(text) == (expected, (), ())


def test_dadaiaignore_invalid_lines_and_segment_scope() -> None:
    """ADR 0093: ``!``, ``**``, an absolute path or ``..`` is invalid, never a pattern; ``*``
    stays inside one segment, so a root pattern admits nothing below the root."""
    text = "!keep\nnotes/**\n/abs\na/../b\n*.png\n[protected]\nsecrets/\n**/k\n"
    invalid = ("!keep", "notes/**", "/abs", "a/../b", "**/k")
    assert wl.parse_dadaiaignore(text) == (("*.png",), ("secrets",), invalid)
    assert wl.protected_glob("worktrees/r/n/secrets/k", ("secrets",)) == "secrets"
    assert wl.protected_glob("secrets/k", ("secrets",)) is None  # repo-relative only
    assert wl.verdict("shot.png", False, ("*.png",), (), ()) == "operator"
    assert wl.verdict(".dadaia/shot.png", False, ("*.png",), (), ()) == "slop"
    assert wl.verdict(".dadaia/shot.png", False, (".dadaia/*.png",), (), ()) == "operator"
