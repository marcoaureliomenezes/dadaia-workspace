"""Intent: CONTRACT — 0.4.6 AC5 (FR4/D13: the SessionStart lane is the one reaper);
sa-hook-files-written-by-table-and-by-hand (HOOK_DIALECTS is the one authority for every
harness's hook wiring); projected-hooks-carry-no-timeout; size: SMALL.

Every harness renders, from its ``HOOK_DIALECTS`` row, exactly one session-start command
that deletes — ``dadaia doctor --fix --expired-only --quiet`` as a CLI process (P-12), never
a ``dadaia_workspace.hooks.*`` module; the settings merge replaces it instead of stacking.
Every rendered row is bounded: 10 s on the tool-call events, 30 s on the others.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path, PurePath
from typing import Any

import pytest

from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.infrastructure.runtime_config import kimi_hooks_block, merge_claude_settings
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    HOOK_DIALECTS,
    hook_documents,
    hook_wrapper_contents,
    wrapper_name,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("harness", sorted(HARNESS_RECORDS))
def test_session_start_runs_the_reaper_once(harness: str) -> None:
    record = HARNESS_RECORDS[harness]
    dialect = HOOK_DIALECTS[record.hooks]
    kimi = record.name == "kimi-code"  # its rows live in a user-level TOML block
    rows: list[dict[str, Any]] = (
        tomllib.loads(kimi_hooks_block(Path("/k")))["hooks"] if kimi else []
    )
    for document in json.loads(json.dumps({} if kimi else hook_documents(record))).values():
        for event, groups in (document if dialect.bare else document["hooks"]).items():
            for group in groups:
                rows += [
                    {"event": event, **e} for e in (group["hooks"] if dialect.nested else [group])
                ]
    assert rows, f"{harness}: no hook file rendered from HOOK_DIALECTS"
    tool = {"pretooluse", "posttooluse"}
    assert [r["timeout"] for r in rows] == [10 if r["event"].lower() in tool else 30 for r in rows]
    bodies = hook_wrapper_contents(record)
    reapers = [r["event"] for r in rows if "--fix" in bodies[PurePath(r[dialect.entry_key]).name]]
    assert [e.lower() for e in reapers] == ["sessionstart"], rows
    reaper = bodies[wrapper_name(record, "doctor-expired")]
    assert " -m dadaia_workspace doctor --fix --expired-only --quiet" in reaper
    assert "dadaia_workspace.hooks." not in reaper


def test_reaper_entry_is_dadaia_owned_so_merge_is_idempotent() -> None:
    canonical = merge_claude_settings(None, Path("/ws"))
    assert merge_claude_settings(canonical, Path("/ws")) == canonical
