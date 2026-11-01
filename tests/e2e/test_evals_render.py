"""`evals/scripts/render.py SRC DST HARNESS LABEL`, run as a subprocess: it copies the task tree
SRC to DST and swaps the two harness tokens (T1 instruction "Claude Code" -> LABEL, T2 project.sh
`--harness claude` -> `--harness HARNESS`); every `tests/` folder stays a byte copy and a token
absent from SRC exits non-zero.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from tests.helpers.oslib import run

pytestmark = pytest.mark.e2e

_ROOT = Path(__file__).resolve().parents[2]
_TASKS = _ROOT / "evals" / "tasks"
_T1 = "t1-cold-onboarding/instruction.md"
_T2 = "t2-block-list-bug/environment/project.sh"


def _files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _render(src: Path, dst: Path) -> int:
    cmd = [sys.executable, str(_ROOT / "evals" / "scripts" / "render.py"), str(src), str(dst)]
    return run([*cmd, "codex", "Codex"], timeout=60).returncode


def test_render_changes_exactly_the_two_tokens(tmp_path: Path) -> None:
    before = _files(_TASKS)
    assert _render(_TASKS, tmp_path / "out") == 0
    out = _files(tmp_path / "out")
    assert out.keys() == before.keys()
    assert {k for k in out if out[k] != before[k]} == {_T1, _T2}
    assert out[_T1] == before[_T1].replace(b"the Claude Code harness", b"the Codex harness")
    assert out[_T2] == before[_T2].replace(b"--harness claude", b"--harness codex")
    assert _files(_TASKS) == before


def test_render_keeps_every_tests_folder_byte_equal(tmp_path: Path) -> None:
    assert _render(_TASKS, tmp_path / "out") == 0
    out = _files(tmp_path / "out")
    kept = {k: v for k, v in _files(_TASKS).items() if "/tests/" in k}
    assert kept
    assert {k: out[k] for k in kept} == kept


@pytest.mark.parametrize("name", [_T1, _T2], ids=["t1-words", "t2-flag"])
def test_render_exits_nonzero_on_an_absent_token(tmp_path: Path, name: str) -> None:
    src = tmp_path / "src"
    shutil.copytree(_TASKS, src)
    assert _render(src, tmp_path / "control") == 0
    (src / name).write_text("reworded line\n")
    assert _render(src, tmp_path / "out") != 0
