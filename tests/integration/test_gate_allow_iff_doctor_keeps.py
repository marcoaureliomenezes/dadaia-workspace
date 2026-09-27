"""One table through the gate and the doctor: the gate ALLOWs a write iff the doctor
does not judge the entry it creates SLOP.

Intent: CONTRACT — sa-gate-allows-root-entries-the-reaper-moves#E1..#E9 (ADR 0058).
Size: MEDIUM (integration: the real ``pre_gate`` subprocess, then ``DoctorService.scan``).

Structural cause pinned: the gate (``root_whitelist``: type-blind names, "an existing
entry is the operator's", no ``.dadaia/`` judgment) and the doctor (type-aware root,
zone and states canon) answered "may this entry exist" with four matchers, so the gate
ALLOWed entries the reaper then moved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.workspace_layout import INSTANCE_EXCEPTIONS
from dadaia_workspace.features.spec_context.doctor import DoctorService, FindingVerdict
from tests.fakes import FakeContextStore, FakeGitClient
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

# (target, pre-existing dir or None, exception glob or None, gate allows)
_TABLE = [
    ("notes/todo.md", "notes", None, False),
    ("notes/todo.md", "notes", "notes", True),
    ("prompt.md/x.md", None, None, False),
    (".env/x.txt", None, None, False),
    (".dadaia/scratch/x.txt", None, None, False),
    (".dadaia/states/mine.json", None, None, False),
    ("prompt.md", None, None, True),
    ("repos/x/f.py", None, None, True),
    (".dadaia/tmp/agent/20260927/x.txt", None, None, True),
]


@pytest.mark.parametrize(("target", "existing", "glob", "allows"), _TABLE)
def test_gate_allows_iff_the_doctor_keeps_the_entry(
    tmp_path: Path, target: str, existing: str | None, glob: str | None, allows: bool
) -> None:
    for zone in ("tmp", "states", "sessions", "reaped"):
        (tmp_path / ".dadaia" / zone).mkdir(parents=True, exist_ok=True)
    if existing is not None:
        (tmp_path / existing).mkdir()
    if glob is not None:
        (tmp_path / INSTANCE_EXCEPTIONS).write_text(f"{glob}\n", encoding="utf-8")
    path = tmp_path / target
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": "x"}}

    gate = run_hook_subprocess("pre_gate", payload, claude_hook_env(tmp_path))

    assert (gate.block_envelope() is None) is allows, gate.stdout
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    slop = [
        f.path
        for f in DoctorService(FakeContextStore(), FakeGitClient(), tmp_path).scan()
        if f.verdict is FindingVerdict.SLOP
    ]
    assert (slop == []) is allows, slop
