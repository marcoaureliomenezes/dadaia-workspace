"""One ``HarnessRecord`` row per harness; every legacy constant derives from the record table."""

from __future__ import annotations

from dadaia_workspace.core.harness_registry import (
    HARNESS_PROJECTION_DIRS,
    HARNESS_RECORDS,
    L1_ENTRY_HARNESSES,
    PROJECTION_TARGETS,
    parse_harness_name,
)


def test_every_record_carries_a_directory_an_agent_transcode_and_a_hook_derivation() -> None:
    assert tuple(HARNESS_RECORDS) == L1_ENTRY_HARNESSES
    for name, record in HARNESS_RECORDS.items():
        assert record.name == name
        assert record.agent_transcode is not None
        assert record.hooks is not None


def test_the_legacy_constants_derive_from_the_record_table() -> None:
    assert tuple(HARNESS_RECORDS) == L1_ENTRY_HARNESSES
    assert {
        name: ((record.directory,) if record.directory else ())
        for name, record in HARNESS_RECORDS.items()
    } == HARNESS_PROJECTION_DIRS
    assert ("agents", *HARNESS_RECORDS) == PROJECTION_TARGETS
    last = next(reversed(HARNESS_RECORDS))
    assert parse_harness_name(last) == last
