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


def _planted(root: Path, *, extra_test: str = "", files: dict[str, str] | None = None) -> Path:
    for name in ("mutate.py", "impact.py", "covdata.py"):
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
    for rel, text in (files or {}).items():
        _write(root, rel, text)
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


_HOME = ["--module", "pkg/m.py", "--home", "tests/test_m.py::test_below_the_limit"]
_MATRIX = [
    "SURVIVED pkg/m.py:1 const: 10 -> 11",
    "SURVIVED pkg/m.py:5 compare: < -> <=",
    'KILLED pkg/m.py:6 return: "yes" -> None'
    " [tests/test_m.py::test_below_again, tests/test_m.py::test_below_the_limit]",
    'KILLED pkg/m.py:7 return: "no" -> None [tests/test_m.py::test_above_the_limit]',
    "mutation score 2/4",
    "DELETABLE tests/test_m.py::test_below_again",
    "KEPT tests/test_m.py::test_above_the_limit",
]


def test_a_test_whose_kills_the_home_also_makes_is_deletable_and_the_rest_are_kept(
    tmp_path: Path,
) -> None:
    root = _planted(tmp_path, extra_test="\n\n" + _AGAIN)
    done = _run(root, *_HOME)
    assert done.stdout.splitlines() == _MATRIX
    assert done.returncode == 0


def test_a_selected_test_that_kills_no_mutant_is_no_kill_and_never_deletable(
    tmp_path: Path,
) -> None:
    root = _planted(
        tmp_path,
        extra_test="\n\n" + _AGAIN,
        files={
            "pkg/other.py": "def noop():\n    return 1\n",
            "tests/test_other.py": (
                "from pkg.other import noop\n\n\ndef test_noop():\n    assert noop() == 1\n"
            ),
        },
    )
    done = _run(root, *_HOME, "--tests", "tests/test_m.py", "tests/test_other.py")
    assert done.stdout.splitlines() == [*_MATRIX, "NO-KILL tests/test_other.py::test_noop"]
    assert done.returncode == 0


_TWO = 'def a():\n    return "a"\n\n\ndef b():\n    return "b"\n\n\ndef unused():\n    return "u"\n'
_TEST_TWO = (
    "from pathlib import Path\n\nfrom pkg import two\n\n\n"
    'def test_a():\n    assert two.a() == "a"\n\n\n'
    "def test_b():\n"
    '    assert two.b() == "b"\n'
    "    assert 'return \"a\"' in Path(two.__file__).read_text()\n"
)


def test_a_mutant_runs_every_selected_test_and_an_unexecuted_line_is_uncovered(
    tmp_path: Path,
) -> None:
    root = _planted(tmp_path, files={"pkg/two.py": _TWO, "tests/test_two.py": _TEST_TWO})
    done = _run(root, "--module", "pkg/two.py", "--tests", "tests/test_two.py")
    assert done.stdout.splitlines() == [
        'KILLED pkg/two.py:2 return: "a" -> None [tests/test_two.py::test_a, tests/test_two.py::test_b]',
        'KILLED pkg/two.py:6 return: "b" -> None [tests/test_two.py::test_b]',
        'UNCOVERED pkg/two.py:10 return: "u" -> None',
        "mutation score 2/3",
    ]
    assert done.returncode == 0


_FG = 'def f():\n    return "x"\n\n\ndef g():\n    return "y"\n'
_NO_RANDOM = {"pytest.ini": "[pytest]\naddopts = -p no:randomly\n"}
_HOME_F = {
    "tests/test_home.py": 'from pkg import fg\n\n\ndef test_f():\n    assert fg.f() == "x"\n'
}
_FG_ARGS = ["--module", "pkg/fg.py", "--home", "tests/test_home.py::test_f", "--tests"]


def test_a_test_depending_on_work_an_earlier_test_triggered_is_still_run_and_kept(
    tmp_path: Path,
) -> None:
    shared = (
        "import pytest\n\nfrom pkg import fg\n\n\n"
        '@pytest.fixture(scope="module")\ndef gv():\n    return fg.g()\n\n\n'
        "def test_first(gv):\n    assert True\n\n\n"
        'def test_second(gv):\n    assert fg.f() == "x"\n    assert gv == "y"\n'
    )
    root = _planted(
        tmp_path,
        files={**_NO_RANDOM, **_HOME_F, "pkg/fg.py": _FG, "tests/test_shared.py": shared},
    )
    done = _run(root, *_FG_ARGS, "tests/test_home.py", "tests/test_shared.py")
    assert done.stdout.splitlines() == [
        'KILLED pkg/fg.py:2 return: "x" -> None'
        " [tests/test_home.py::test_f, tests/test_shared.py::test_second]",
        'KILLED pkg/fg.py:6 return: "y" -> None [tests/test_shared.py::test_second]',
        "mutation score 2/2",
        "KEPT tests/test_shared.py::test_second",
        "NO-KILL tests/test_shared.py::test_first",
    ]
    assert done.returncode == 0


def test_a_mutant_that_breaks_one_files_import_still_credits_every_other_failing_test(
    tmp_path: Path,
) -> None:
    root = _planted(
        tmp_path,
        files={
            **_NO_RANDOM,
            **_HOME_F,
            "pkg/fg.py": _FG,
            "tests/test_x.py": (
                'from pkg import fg\n\nV = fg.g().upper()\n\n\ndef test_v():\n    assert V == "Y"\n'
            ),
            "tests/test_z.py": (
                'from pkg import fg\n\n\ndef test_y():\n    assert fg.f() == "x"\n'
                '    assert fg.g() == "y"\n'
            ),
        },
    )
    done = _run(root, *_FG_ARGS, "tests/test_home.py", "tests/test_z.py", "tests/test_x.py")
    assert done.stdout.splitlines() == [
        'KILLED pkg/fg.py:2 return: "x" -> None [tests/test_home.py::test_f, tests/test_z.py::test_y]',
        'KILLED pkg/fg.py:6 return: "y" -> None [tests/test_x.py::test_v, tests/test_z.py::test_y]',
        "mutation score 2/2",
        "KEPT tests/test_x.py::test_v",
        "KEPT tests/test_z.py::test_y",
    ]
    assert done.returncode == 0


def test_a_red_baseline_exits_1_before_any_mutation(tmp_path: Path) -> None:
    root = _planted(tmp_path, files={"tests/test_red.py": "def test_fails():\n    assert False\n"})
    done = _run(root, "--module", "pkg/m.py", "--tests", "tests/test_red.py")
    assert done.stdout.splitlines() == ["BASELINE RED pkg/m.py: tests/test_red.py::test_fails"]
    assert done.returncode == 1
    assert (root / "pkg/m.py").read_text("utf-8") == _HEAD_M


_CHILD_TEST = (
    "import os\nimport subprocess\nimport sys\n\n\n"
    "def test_spawns():\n"
    '    env = {k: v for k, v in os.environ.items() if not k.startswith(("COV", "COVERAGE"))}\n'
    "    code = \"from pkg.child import f; assert f() == 'c'\"\n"
    '    done = subprocess.run([sys.executable, "-c", code], env=env, check=False)\n'
    "    assert done.returncode == 0\n"
)


def test_a_mutant_on_a_line_only_an_unmeasured_child_executes_is_killed_by_the_spawning_test(
    tmp_path: Path,
) -> None:
    root = _planted(
        tmp_path,
        files={"pkg/child.py": 'def f():\n    return "c"\n', "tests/test_child.py": _CHILD_TEST},
    )
    done = _run(root, "--module", "pkg/child.py", "--tests", "tests/test_child.py")
    assert done.stdout.splitlines() == [
        'KILLED pkg/child.py:2 return: "c" -> None [tests/test_child.py::test_spawns]',
        "mutation score 1/1",
    ]
    assert done.returncode == 0
