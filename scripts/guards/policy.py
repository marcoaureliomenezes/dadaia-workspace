"""Policy checks: pytest tests behaviour only, so no test reads a tracked repo file.

A test, its helpers and its tables must not read a path rooted at ``__file__`` outside
``tests/fixtures/`` and ``tmp_path``, nor run ``git ls-files`` or ``git grep`` on the checkout.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from run import Check, Session, Tree


def policy_in_pytest(tree: Tree) -> list[str]:
    return []


# --- plants: each writes one violation; ``run.py --planted`` requires red ----------------


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


_ROOT = "from pathlib import Path\n\nROOT = Path(__file__).resolve().parents[2]\n\n\n"

_CONTROL_TESTS = {
    "fixture": _ROOT
    + 'FIX = ROOT / "tests" / "fixtures"\n\n\n'
    + 'def test_fixture():\n    assert (FIX / "data.md").read_text()\n',
    "tmp_path": 'def test_tmp(tmp_path):\n    (tmp_path / "a.md").write_text("a")\n'
    + '    assert (tmp_path / "a.md").read_text()\n',
    "copy_and_run": "import shutil\nimport subprocess\nimport sys\n\n"
    + _ROOT
    + 'def test_copy(tmp_path):\n    shutil.copy(ROOT / "scripts" / "x.py", tmp_path / "x.py")\n'
    + '    subprocess.run([sys.executable, str(tmp_path / "x.py")], check=True)\n',
    "run_by_path": "import subprocess\nimport sys\n\n"
    + _ROOT
    + 'def test_run():\n    subprocess.run([sys.executable, str(ROOT / "scripts" / "x.py")], check=True)\n',
    "argument": _ROOT
    + "def test_argument():\n    from x import check\n\n"
    + '    assert check(ROOT / "scripts" / "x.py") == []\n',
    "git_in_tmp": "import subprocess\n\n\n"
    + 'def test_git(tmp_path):\n    subprocess.run(["git", "ls-files"], cwd=tmp_path, check=True)\n',
}


def CONTROL(root: Path) -> Session:
    """Every check green: tests that read only fixtures and ``tmp_path``, run scripts or
    pass a repo path as an argument, with violations only in an untracked, gitignored file."""
    _write(root, ".gitignore", "scratch/\n")
    _write(
        root, "scratch/tests/unit/test_x.py", _CONTROL_TESTS["fixture"].replace("FIX /", "ROOT /")
    )
    _write(root, "tests/fixtures/data.md", "data\n")
    for name, body in _CONTROL_TESTS.items():
        _write(root, f"tests/unit/test_{name}.py", body)
    return {}


def _plant(body: str) -> Callable[[Path], Session | None]:
    def plant(root: Path) -> None:
        CONTROL(root)
        _write(root, "tests/unit/test_planted.py", body)

    return plant


_PLANTS = {
    "repo-file-read": _ROOT
    + 'def test_law():\n    assert "x" in (ROOT / "AGENTS.md").read_text()\n',
    "repo-file-read-helper": _ROOT
    + "def _read(p):\n    return p.read_text()\n\n\n"
    + 'def test_law():\n    assert _read(ROOT / "AGENTS.md")\n',
    "repo-file-read-table": "import pytest\n\n"
    + _ROOT
    + 'DOCS = [ROOT / "AGENTS.md"]\n\n\n'
    + '@pytest.mark.parametrize("p", DOCS)\ndef test_law(p):\n    assert p.read_text()\n',
    "repo-file-read-git": "import subprocess\n\n\n"
    + "def test_files():\n"
    + '    out = subprocess.run(["git", "ls-files"], capture_output=True, check=True).stdout\n'
    + "    assert out\n",
    "repo-file-read-tree": "import ast\n\n"
    + _ROOT
    + 'def test_parse():\n    for p in ROOT.rglob("*.py"):\n        ast.parse(p.read_text())\n',
    "repo-file-read-module-file": "from pathlib import Path\n\nimport pkg\n\n\n"
    + 'def test_pkg():\n    assert (Path(pkg.__file__).parent / "AGENTS.md").read_text()\n',
    "repo-file-read-return": _ROOT
    + 'def _doc():\n    return ROOT / "AGENTS.md"\n\n\n'
    + "def test_law():\n    assert _doc().read_text()\n",
    "repo-file-read-constant": _ROOT
    + 'LAW = (ROOT / "AGENTS.md").read_text()\n\n\ndef test_law():\n    assert "x" in LAW\n',
}

CHECKS: dict[str, Check] = {
    "policy-in-pytest": (policy_in_pytest, {row: _plant(body) for row, body in _PLANTS.items()}),
}
