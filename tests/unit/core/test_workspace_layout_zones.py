"""Intent: CONTRACT — 0.4.6 AC1 (FR1: the zone registry's rows and its derived views); size: SMALL.

Expected values come from SPEC §3/§4 (FR1, FR5, FR8) and architect A, never from the
module under test: the 11 rows in order, the four TTL zones at 86,400 s, the three closed
canons, the creators per zone, and the pure exception-glob parser.
"""

from __future__ import annotations

import dataclasses

import pytest

from dadaia_workspace.core import workspace_layout as wl

_SPEC_ZONE_ORDER = [
    "agentic",
    "hooks",
    "states",
    "sessions",
    "handoff",
    "tmp",
    "mcps",
    ".cache",
    "dist",
    "references",
    ".venv",
]

_SPEC_STATES_CANON = {
    "spec_contexts.json",
    "server_registry.json",
    "install_ledger.json",
    "agent_model_policy.json",
    "agent_model_policy.json.last-good.json",
    "privacy_denylist.json",
    "instance_exceptions.txt",
    "backlog_subject_aliases.txt",
    "harness_profile.json",
    "presence",
    "AGENTS.md",
}


def _zone(name: str) -> wl.Zone:
    return next(z for z in wl.DADAIA_ZONES if z.name == name)


def test_registry_holds_the_eleven_spec_zones_in_order() -> None:
    assert [z.name for z in wl.DADAIA_ZONES] == _SPEC_ZONE_ORDER
    assert wl.zone_names() == frozenset(_SPEC_ZONE_ORDER)


def test_zone_record_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _zone("tmp").ttl_seconds = 1  # type: ignore[misc]


def test_ttl_zones_are_the_four_fr5_zones_at_one_day() -> None:
    ttl = {z.name: z.ttl_seconds for z in wl.zones_with_ttl()}
    assert ttl == {"handoff": 86_400, "tmp": 86_400, "mcps": 86_400, ".cache": 86_400}
    assert all(z.ttl_seconds is None for z in wl.DADAIA_ZONES if z.name not in ttl)


def test_closed_canons_are_states_sessions_dist() -> None:
    canon = {z.name: z.canon for z in wl.zones_with_canon()}
    assert canon == {
        "states": wl.STATES_CANON,
        "sessions": frozenset({"*.json"}),
        "dist": frozenset({"spec-contexts.json"}),
    }
    assert frozenset(_SPEC_STATES_CANON) == wl.STATES_CANON


def test_zone_classes_match_architect_table() -> None:
    cls = {z.name: z.cls for z in wl.DADAIA_ZONES}
    assert cls == {
        "agentic": wl.ZoneClass.PROJECTION,
        "hooks": wl.ZoneClass.PROJECTION,
        "states": wl.ZoneClass.STATE,
        "sessions": wl.ZoneClass.PROTECTED,
        "handoff": wl.ZoneClass.OUTPUT,
        "tmp": wl.ZoneClass.EPHEMERAL,
        "mcps": wl.ZoneClass.EPHEMERAL,
        ".cache": wl.ZoneClass.EPHEMERAL,
        "dist": wl.ZoneClass.STATE,
        "references": wl.ZoneClass.OPERATOR,
        ".venv": wl.ZoneClass.MANAGED,
    }


def test_creator_views_partition_the_registry() -> None:
    by_creator = {c: [z.name for z in wl.zones_created_by(c)] for c in wl.Creator}
    assert by_creator == {
        wl.Creator.INIT: ["states", ".venv"],
        wl.Creator.INSTALL: ["agentic", "hooks"],
        wl.Creator.RUNTIME: ["sessions", "handoff", "tmp", "mcps", ".cache", "dist"],
        wl.Creator.OPERATOR: ["references"],
    }


def test_walked_zones_exclude_operator_and_managed() -> None:
    assert [z.name for z in wl.walked_zones()] == _SPEC_ZONE_ORDER[:9]


def test_additive_prefixes_are_output_and_ephemeral_zones_in_registry_order() -> None:
    assert wl.additive_prefixes() == (
        ".dadaia/handoff/",
        ".dadaia/tmp/",
        ".dadaia/mcps/",
        ".dadaia/.cache/",
    )


def test_table_rows_render_ttl_as_seconds_or_never() -> None:
    rows = dict(zip([z.name for z in wl.DADAIA_ZONES], wl.zone_table_rows(), strict=True))
    assert rows["tmp"] == ("tmp", _zone("tmp").purpose, "ephemeral", "86400", "runtime")
    assert rows["references"][2:] == ("operator", "never", "operator")


def test_root_files_and_exceptions_path() -> None:
    assert frozenset({"AGENTS.md", ".gitignore"}) == wl.DADAIA_ROOT_FILES
    assert wl.INSTANCE_EXCEPTIONS == ".dadaia/states/instance_exceptions.txt"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", (), id="empty"),
        pytest.param("# only a comment\n\n   \n", (), id="comments-and-blanks"),
        pytest.param("  *.iml \n.idea\n", ("*.iml", ".idea"), id="stripped-in-order"),
        pytest.param(
            ".idea\n# note\n.idea\n*.iml\n.idea", (".idea", "*.iml"), id="dedupe-keeps-first"
        ),
    ],
)
def test_parse_exception_globs(text: str, expected: tuple[str, ...]) -> None:
    assert wl.parse_exception_globs(text) == expected
