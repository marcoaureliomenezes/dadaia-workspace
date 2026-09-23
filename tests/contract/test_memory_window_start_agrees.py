"""Intent: CONTRACT — 0.4.7 c11 review LOW-1: the memory window's start is stated twice
(the writer's `_release_store.window_start`, the doctor's `memory_window_start`); both
read one fixture table and must agree. Size: SMALL.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.specs.release_tree import memory_window_start

pytestmark = pytest.mark.contract

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "dadaia_workspace/public/skills/dd-release-implementation/scripts"
    ),
)
import _release_store as store  # noqa: E402

_MEMORY = {"kind": "memory", "since": "aaa", "until": "bbb"}
_TABLE: list[tuple[str, dict[str, Any], str]] = [
    ("no defined.sha, no entry", {"defined": None, "log": []}, ""),
    ("defined.sha only", {"defined": {"sha": "ddd"}, "log": []}, "ddd"),
    ("non-dict log entries", {"defined": {"sha": "ddd"}, "log": ["prose", 7, None]}, "ddd"),
    ("a previous memory entry", {"defined": {"sha": "ddd"}, "log": [_MEMORY]}, "bbb"),
    (
        "an entry with no until",
        {"defined": {"sha": "ddd"}, "log": [_MEMORY, {"kind": "memory"}]},
        "bbb",
    ),
    (
        "a non-memory entry",
        {"defined": {"sha": "ddd"}, "log": [{"kind": "note", "until": "x"}]},
        "ddd",
    ),
]


@pytest.mark.parametrize(("case", "state", "expected"), _TABLE, ids=[c for c, _, _ in _TABLE])
def test_writer_and_doctor_derive_the_same_window_start(
    case: str, state: dict[str, Any], expected: str
) -> None:
    try:
        written = store.window_start(state)
    except store.Refusal:
        written = ""  # the writer refuses where the doctor derives no start
    assert (written, memory_window_start(state)) == (expected, expected), case
