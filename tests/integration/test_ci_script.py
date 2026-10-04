"""``scripts/ci.py`` names the failing step and exits 1, run over a tmp tree (never the
checkout): the script, ``pyproject.toml`` and a one-contract ``setup.cfg`` copied in, beside
the planted files."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow(reason="each case spawns scripts/ci.py and its tools")
_REPO = Path(__file__).resolve().parents[2]
_CONTRACT = """[importlinter]
root_package = dadaia_workspace
[importlinter:contract:one]
name = one
type = independence
modules =
    dadaia_workspace.a
    dadaia_workspace.m
"""


def _checkout(root: Path, files: dict[str, str]) -> Path:
    for d in ("scripts", "tests"):
        (root / d).mkdir(parents=True)
    for kept in ("scripts/ci.py", "pyproject.toml"):
        shutil.copyfile(_REPO / kept, root / kept)
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def _ci(checkout: Path, job: str, python: str = sys.executable) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [python, str(checkout / "scripts" / "ci.py"), job],
        cwd=checkout,
        env={k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"},
        capture_output=True,
        text=True,
        check=False,
    )


def _instance(root: Path) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": []}\n')
    return root


def _venv_owned_by(instance: Path) -> str:
    """A python whose ``sys.prefix`` is ``<instance>/.dadaia/.venv``: a symlink to this
    interpreter, this venv's ``pyvenv.cfg``, and a ``.pth`` onto its packages — no install."""
    venv = instance / ".dadaia" / ".venv"
    site = venv / Path(sysconfig.get_path("purelib")).relative_to(sys.prefix)
    site.mkdir(parents=True)
    (site / "deps.pth").write_text(sysconfig.get_path("purelib") + "\n")
    shutil.copyfile(Path(sys.prefix) / "pyvenv.cfg", venv / "pyvenv.cfg")
    (venv / "bin").mkdir()
    (venv / "bin" / "python").symlink_to(sys.executable)
    return str(venv / "bin" / "python")


@pytest.mark.parametrize(
    ("source", "last", "code"),
    [("import os\n", "FAILED: ruff check", 1), ("x = 1\n", "ALL PASS", 0)],
)
def test_lint_exits_by_the_step_that_failed(
    tmp_path: Path, source: str, last: str, code: int
) -> None:
    files = {
        "setup.cfg": _CONTRACT,
        "dadaia_workspace/__init__.py": "",
        "dadaia_workspace/a.py": "",
    }
    done = _ci(_checkout(tmp_path, {**files, "dadaia_workspace/m.py": source}), "lint")
    assert done.stdout.splitlines()[-1] == last
    assert done.returncode == code


@pytest.mark.parametrize(
    ("check", "verdict", "code"),
    [("1 == 2", "FAIL unit-fast", 1), ("1 == 1", "PASS unit-fast", 0)],
)
def test_unit_fast_exits_by_its_unit_tests(
    tmp_path: Path, check: str, verdict: str, code: int
) -> None:
    test = f"import pytest\n\n\n@pytest.mark.unit\ndef test_one() -> None:\n    assert {check}\n"
    done = _ci(_checkout(tmp_path, {"tests/unit/test_one.py": test}), "unit-fast")
    assert verdict in done.stdout
    assert done.returncode == code
    assert list(tmp_path.rglob("__pycache__")) == []  # no step writes bytecode into the tree


@pytest.mark.parametrize("owner", ["encloses the checkout", "owns the venv"])
def test_doctor_judges_no_instance(tmp_path: Path, owner: str) -> None:
    instance = _instance(tmp_path / "inst")
    nested = owner == "encloses the checkout"
    checkout = _checkout(instance / "repos" / "co" if nested else tmp_path / "co", {})
    (checkout / "dadaia_workspace").symlink_to(_REPO / "dadaia_workspace")
    done = _ci(checkout, "doctor", sys.executable if nested else _venv_owned_by(instance))
    assert "doctor --specs-dir specs" in done.stdout
    # The workspace section (WS-*) judges a resolved instance; the fenced run resolves none.
    assert [ln for ln in done.stdout.splitlines() if ln.startswith("WS-")] == []
