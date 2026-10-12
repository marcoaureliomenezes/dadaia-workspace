"""``scripts/mutate.py --base`` over a temporary git repo (never the checkout).

The planted repo has a base commit and a head commit; ``mutate.py`` is copied into
``<repo>/scripts/`` with ``impact.py`` and ``covdata.py`` and run with cwd ``<repo>``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.harness_env import suite_env

pytestmark = pytest.mark.slow(reason="each case spawns git, scripts/mutate.py and pytest")
_REPO = Path(__file__).resolve().parents[2]

_BASE_M = 'LIMIT = 10\n\n\ndef under(n):\n    return "no"\n'
_HEAD_M = (
    'LIMIT = 10\n\n\ndef under(n):\n    if n < LIMIT:\n        return "yes"\n    return "no"\n'
)
_BASE_T = 'from pkg.m import under\n\n\ndef test_above_the_limit():\n    assert under(20) == "no"\n'
_BELOW = 'def test_below_the_limit():\n    assert under(3) == "yes"\n'
_AGAIN = 'def test_below_again():\n    assert under(3) == "yes"\n'


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
    )


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def _planted(root: Path, *, extra_test: str = "") -> Path:
    for name in ("mutate.py", "impact.py", "covdata.py"):
        if (_REPO / "scripts" / name).exists():
            (root / "scripts").mkdir(exist_ok=True)
            shutil.copyfile(_REPO / "scripts" / name, root / "scripts" / name)
    _write(root, ".gitignore", "__pycache__/\n.coverage*\n.pytest_cache/\n")
    _write(root, "pkg/__init__.py", "")
    _write(root, "pkg/m.py", _BASE_M)
    _write(root, "tests/test_m.py", _BASE_T)
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    _write(root, "pkg/m.py", _HEAD_M)
    _write(root, "tests/test_m.py", _BASE_T + "\n\n" + _BELOW + extra_test)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "head")
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/mutate.py", *args],
        cwd=root,
        env=suite_env(
            os.environ,
            Path.home(),
            unset=tuple(
                k
                for k in os.environ
                if k == "PYTHONDONTWRITEBYTECODE" or k.startswith(("COV_CORE_", "COVERAGE"))
            ),
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_a_diff_is_mutated_line_by_line_and_reports_survivors_kills_and_coverage(
    tmp_path: Path,
) -> None:
    root = _planted(tmp_path)
    done = _run(root, "--base", "HEAD~1")
    assert done.stdout.splitlines() == [
        "SURVIVED pkg/m.py:5 compare: < -> <=",
        'KILLED pkg/m.py:6 return: "yes" -> None [tests/test_m.py::test_below_the_limit]',
        "mutation score 1/2",
        "diff line coverage 2/2",
        "diff branch coverage 2/2",
    ]
    assert done.returncode == 0
    assert (root / "pkg/m.py").read_text("utf-8") == _HEAD_M
