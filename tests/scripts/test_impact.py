"""``scripts/ci.py --changed`` over a temporary git repo (never the checkout).

Design choices the implementation must satisfy:

- Root: no new rule. ``ci.py`` takes ``ROOT`` from its own file (``parents[1]``), so the test
  copies ``scripts/ci.py`` and ``scripts/impact.py`` into ``<repo>/scripts/`` and runs
  ``python scripts/ci.py --changed`` with cwd ``<repo>``. There is no root argument.
  ``impact.py`` is run as a script of that same ``scripts/`` dir, never imported.
- Base: the working tree against ``HEAD`` -- tracked edits (``git diff --name-only HEAD``)
  plus untracked, non-ignored files (``git ls-files --others --exclude-standard``). The repo
  has one commit and no work branch, so no merge-base is involved.
- Graph: ``ast`` imports over ``dadaia_workspace/`` and ``tests/``; a test file is selected
  when it imports a changed module, directly or through other modules.
- Skill rule: a changed ``dadaia_workspace/public/skills/dd-<x>/...`` file selects every test
  under ``tests/public/skills/dd_<x>/``.
- Output, one per line on stdout: ``test: <path>`` for each selected test file (sorted) and
  ``unmapped: <path>`` for each changed file that selects nothing; then ``ci.py`` runs
  pytest on the selected files. Unmapped files do not fail the run: exit 0 when the
  selected tests pass.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.harness_env import suite_env

pytestmark = pytest.mark.slow(reason="each case spawns git, scripts/ci.py and pytest")
_REPO = Path(__file__).resolve().parents[2]
_SKILL = "dadaia_workspace/public/skills/dd-demo/scripts/run.py"


def _test(imports: str) -> str:
    """A passing test that records its file name in ``ran.log`` (cwd) so the run is observable."""
    return (
        f"{imports}from pathlib import Path\n\n\n"
        "def test_ran() -> None:\n"
        "    with Path('ran.log').open('a') as log:\n"
        "        log.write(Path(__file__).name + '\\n')\n"
    )


_FILES = {
    "dadaia_workspace/__init__.py": "",
    "dadaia_workspace/base.py": "VALUE = 1\n",
    "dadaia_workspace/mid.py": "from dadaia_workspace import base\n\nVALUE = base.VALUE\n",
    "dadaia_workspace/top.py": "VALUE = 2\n",
    "dadaia_workspace/orphan.py": "VALUE = 3\n",
    _SKILL: "VALUE = 4\n",
    "README.md": "readme\n",
    "tests/test_mid.py": _test("from dadaia_workspace import mid\n"),
    "tests/test_top.py": _test("from dadaia_workspace import top\n"),
    "tests/public/skills/dd_demo/test_run.py": _test(""),
    "tests/public/skills/dd_other/test_other.py": _test(""),
}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(root: Path) -> Path:
    for name in ("ci.py", "impact.py"):
        if (_REPO / "scripts" / name).exists():
            (root / "scripts").mkdir(exist_ok=True)
            shutil.copyfile(_REPO / "scripts" / name, root / "scripts" / name)
    for rel, text in _FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    (root / ".gitignore").write_text("ran.log\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base")
    return root


def _changed(root: Path, edits: dict[str, str]) -> subprocess.CompletedProcess[str]:
    for rel, text in edits.items():
        (root / rel).write_text(text, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "scripts/ci.py", "--changed"],
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
        check=False,
    )


def _lines(done: subprocess.CompletedProcess[str], prefix: str) -> list[str]:
    return sorted(ln for ln in done.stdout.splitlines() if ln.startswith(prefix))


def _ran(root: Path) -> list[str]:
    return sorted((root / "ran.log").read_text("utf-8").split())


def test_a_changed_module_selects_the_tests_importing_it_transitively_and_runs_them(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    done = _changed(root, {"dadaia_workspace/base.py": "VALUE = 10\n"})
    assert _lines(done, "test: ") == ["test: tests/test_mid.py"]
    assert _lines(done, "unmapped: ") == []
    assert _ran(root) == ["test_mid.py"]
    assert done.returncode == 0
    assert list(tmp_path.rglob("__pycache__")) == []


def test_a_direct_import_selects_only_the_importing_test(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    done = _changed(root, {"dadaia_workspace/top.py": "VALUE = 20\n"})
    assert _lines(done, "test: ") == ["test: tests/test_top.py"]
    assert _ran(root) == ["test_top.py"]


def test_changed_files_the_graph_cannot_map_are_named_not_hidden(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    done = _changed(
        root,
        {"README.md": "changed\n", "dadaia_workspace/orphan.py": "VALUE = 30\n"},
    )
    assert _lines(done, "unmapped: ") == [
        "unmapped: README.md",
        "unmapped: dadaia_workspace/orphan.py",
    ]
    assert _lines(done, "test: ") == []
    assert done.returncode == 0


def test_a_skill_script_maps_to_its_tests_directory(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    done = _changed(root, {_SKILL: "VALUE = 40\n"})
    assert _lines(done, "test: ") == ["test: tests/public/skills/dd_demo/test_run.py"]
    assert _lines(done, "unmapped: ") == []
    assert _ran(root) == ["test_run.py"]


def test_explicit_paths_select_their_tests_without_reading_the_working_tree(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    (root / "pkg").mkdir()
    (root / "pkg/__init__.py").write_text("", encoding="utf-8")
    (root / "pkg/m.py").write_text("LIMIT = 10\n", encoding="utf-8")
    (root / "tests/test_m.py").write_text(_test("from pkg import m\n"), encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "pkg")
    (root / "README.md").write_text("changed\n", encoding="utf-8")
    done = subprocess.run(
        [sys.executable, "scripts/impact.py", "pkg/m.py"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert done.stdout.splitlines() == ["test: tests/test_m.py"]
