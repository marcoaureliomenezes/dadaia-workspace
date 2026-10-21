"""One ``HarnessRecord`` row per harness; the projection table carries no harness-named
literal, so the per-harness-branch bug family (public-install / init --harness /
harness-profile disagreements) cannot reappear by construction.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

from dadaia_workspace.cli.commands import init as init_module
from dadaia_workspace.core.harness_registry import (
    HARNESS_PROJECTION_DIRS,
    HARNESS_RECORDS,
    L1_ENTRY_HARNESSES,
    PROJECTION_TARGETS,
    parse_harness_name,
)
from dadaia_workspace.features.workspace import service as workspace_service_module
from dadaia_workspace.infrastructure import agent_transcodes as agent_transcodes_module
from dadaia_workspace.infrastructure import projection_rules as projection_rules_module
from tests.helpers.oslib import read_text


def test_every_record_carries_a_directory_an_agent_transcode_and_a_hook_derivation() -> None:
    assert tuple(HARNESS_RECORDS) == L1_ENTRY_HARNESSES
    for name, record in HARNESS_RECORDS.items():
        assert record.name == name
        assert record.agent_transcode is not None
        assert record.hooks is not None


def test_only_claude_names_the_payload_key_of_a_subagent() -> None:
    assert {name: record.subagent_key for name, record in HARNESS_RECORDS.items()} == {
        "claude": "agent_type",
        "codex": None,
        "kimi-code": None,
        "cursor": None,
        "devin": None,
        "copilot": None,
    }


def test_the_legacy_constants_derive_from_the_record_table() -> None:
    assert tuple(HARNESS_RECORDS) == L1_ENTRY_HARNESSES
    assert {
        name: ((record.directory,) if record.directory else ())
        for name, record in HARNESS_RECORDS.items()
    } == HARNESS_PROJECTION_DIRS
    assert ("agents", *HARNESS_RECORDS) == PROJECTION_TARGETS
    last = next(reversed(HARNESS_RECORDS))
    assert parse_harness_name(last) == last


@pytest.mark.parametrize(
    "module",
    [
        projection_rules_module,
        agent_transcodes_module,
        workspace_service_module,
        init_module,
    ],
    ids=lambda m: m.__name__,
)
def test_the_projection_table_carries_no_harness_named_literal(module: ModuleType) -> None:
    """A harness name in the projection table — or in `init`, which owns no projection —
    IS the per-harness branch coming back."""
    source = read_text(Path(module.__file__ or ""))
    offenders = [
        f'"{name}"' for name in L1_ENTRY_HARNESSES if f'"{name}"' in source or f"'{name}'" in source
    ]
    assert not offenders, (
        f"{Path(module.__file__ or '').name} names harnesses {offenders}; "
        "every harness fact belongs to core/harness_registry.py's record table"
    )
