"""One table through the gate and the doctor: the gate ALLOWs a write iff the doctor
does not judge the entry it creates SLOP.

Intent: CONTRACT — sa-gate-allows-root-entries-the-reaper-moves#E6 (every row), #E1
(notes/ without a glob), #E2 (with one), sa-gate-allows-root-entries-the-reaper-moves#E3 (wrong type), #E4 (.dadaia non-zone and
non-canon states), #E5 (root specs/), #E8 (law files) — ADR 0058.
Size: MEDIUM (integration: the real ``pre_gate`` subprocess, then ``DoctorService.scan``).

Structural cause pinned: the gate (``root_whitelist``: type-blind names, "an existing
entry is the operator's", no ``.dadaia/`` judgment) and the doctor (type-aware root,
zone and states canon) answered "may this entry exist" with four matchers, so the gate
ALLOWed entries the reaper then moved.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.workspace_layout import DADAIAIGNORE
from dadaia_workspace.features.spec_context.doctor import DoctorService, FindingVerdict
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess
from tests.fixtures.stores import context_store

# (target, pre-existing dir or None, exception glob or None, gate allows)
_TABLE = [
    ("notes/todo.md", "notes", None, False),
    ("notes/todo.md", "notes", "notes", True),
    ("prompt.md/x.md", None, None, False),
    (".env/x.txt", None, None, False),
    (".dadaia/scratch/x.txt", None, None, False),
    (".dadaia/states/mine.json", None, None, False),
    ("prompt.md", None, None, True),
    ("specs/bugs/x.md", None, None, False),
    (".dadaia/newzone/x.txt", None, None, False),
    ("repos/x/f.py", None, None, True),
    (".dadaia/tmp/agent/20260927/x.txt", None, None, True),
]


@pytest.mark.parametrize(("target", "existing", "glob", "allows"), _TABLE)
def test_gate_allows_iff_the_doctor_keeps_the_entry(
    tmp_path: Path, target: str, existing: str | None, glob: str | None, allows: bool
) -> None:
    for zone in ("tmp", "states", "sessions", "reaped"):
        (tmp_path / ".dadaia" / zone).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    if existing is not None:
        (tmp_path / existing).mkdir()
    if glob is not None:
        (tmp_path / DADAIAIGNORE).write_text(f"{glob}\n", encoding="utf-8")
    path = tmp_path / target
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": "x"}}

    gate = run_hook_subprocess("pre_gate", payload, claude_hook_env(tmp_path))

    block = gate.block_envelope()
    assert (block is None) is allows, gate.stdout
    if block is not None:  # #E1, #E4: the one fix names the owning zone, never the globs
        (fix,) = [ln for ln in block["reason"].splitlines() if ln.startswith("fix: ")]
        zone = (tmp_path.resolve() / ".dadaia" / "tmp").as_posix()
        assert shlex.split(fix[len("fix: ") :]) == [
            Path(sys.executable).as_posix(),
            "-c",
            f"import pathlib; pathlib.Path(r'{zone}').mkdir(parents=True, exist_ok=True)",
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    findings = DoctorService(
        context_store(tmp_path / ".dadaia" / "states"), GitSubprocessClient(), tmp_path
    ).scan()
    slop = [f.path for f in findings if f.verdict is FindingVerdict.SLOP]
    assert (slop == []) is allows, slop
    if glob is not None:  # #E2
        verdicts = {f.path: f.verdict for f in findings}
        assert verdicts[glob] is FindingVerdict.OPERATOR
