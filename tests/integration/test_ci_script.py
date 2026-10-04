"""``scripts/ci.py`` names the failing step and exits 1, run over a tmp tree (never the
checkout): the script and ``pyproject.toml`` copied in, beside the one planted file."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow(reason="each case spawns scripts/ci.py and its tools")
_REPO = Path(__file__).resolve().parents[2]


def _run(tmp_path: Path, job: str, rel: str, text: str) -> subprocess.CompletedProcess[str]:
    for d in ("scripts", "tests"):
        (tmp_path / d).mkdir()
    for kept in ("scripts/ci.py", "pyproject.toml"):
        shutil.copyfile(_REPO / kept, tmp_path / kept)
    (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / rel).write_text(text, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(tmp_path / "scripts" / "ci.py"), job],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("source", "verdict"),
    [("import os\n", "FAIL ruff check"), ("x = 1\n", "PASS ruff check")],
)
def test_lint_names_ruff_check_by_its_verdict(tmp_path: Path, source: str, verdict: str) -> None:
    done = _run(tmp_path, "lint", "dadaia_workspace/m.py", source)
    assert verdict in done.stdout


@pytest.mark.parametrize(
    ("check", "verdict", "code"),
    [("1 == 2", "FAIL unit-fast", 1), ("1 == 1", "PASS unit-fast", 0)],
)
def test_unit_fast_exits_by_its_unit_tests(
    tmp_path: Path, check: str, verdict: str, code: int
) -> None:
    test = f"import pytest\n\n\n@pytest.mark.unit\ndef test_one() -> None:\n    assert {check}\n"
    done = _run(tmp_path, "unit-fast", "tests/unit/test_one.py", test)
    assert verdict in done.stdout
    assert done.returncode == code
