"""rc-9 AC3.1: the root conftest applies the suite env once per process and its tripwire
fails a session that writes outside tmp — each judged by a real inner session (pytester),
never by re-executing the conftest. Bugs outside-tmp-home-pin-coupled-to-session-hooks,
heartbeat-test-drives-hook-in-process, operator-env-scrub-row-leaves-stale-pinned-home."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_CHECKOUT = Path(__file__).resolve().parents[2]

_SEES_THE_TEMP_HOME = """
import os, subprocess, sys
from pathlib import Path
from tests.fixtures.harness_env import suite_env

def test_inner():
    assert "DADAIA_CONTEXT" not in os.environ
    assert Path.home() != Path(os.environ["OUTER_FOREIGN_HOME"])
    child = subprocess.run(
        [sys.executable, "-c", "import os; print(os.environ['HOME'])"],
        env=suite_env(os.environ, Path.home()), capture_output=True, text=True, check=True,
    )
    assert child.stdout == f"{Path.home()}\\n"
"""

_WRITES_A_PYCACHE = """
from pathlib import Path

def test_inner():
    (Path(__file__).parent / "__pycache__").mkdir()
"""


@pytest.fixture()
def inner(request: pytest.FixtureRequest) -> Iterator[Path]:
    """A gitignored dir under the checkout's ``tests/tmp/`` (the root conftest only judges
    items inside the checkout); removed after the run."""
    where = _CHECKOUT / "tests" / "tmp" / f"inner-{uuid.uuid4().hex[:8]}"
    where.mkdir(parents=True)
    yield where
    shutil.rmtree(where, ignore_errors=True)


@pytest.mark.xfail(strict=True, reason="RED until J3.S2.T1")
def test_an_inner_run_under_an_operator_context_sees_the_temp_home(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch, inner: Path, tmp_path: Path
) -> None:
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    monkeypatch.setenv("DADAIA_CONTEXT", "ghost")
    monkeypatch.setenv("HOME", str(foreign))
    monkeypatch.setenv("OUTER_FOREIGN_HOME", str(foreign))
    (inner / "test_home.py").write_text(_SEES_THE_TEMP_HOME, encoding="utf-8")

    result = pytester.runpytest_subprocess(str(inner / "test_home.py"), "-p", "no:randomly")

    assert result.ret == 0, result.stdout.str()


def test_an_inner_run_writing_a_watched_pycache_exits_1(
    pytester: pytest.Pytester, inner: Path
) -> None:
    (inner / "test_pycache.py").write_text(_WRITES_A_PYCACHE, encoding="utf-8")

    result = pytester.runpytest_subprocess(str(inner / "test_pycache.py"), "-p", "no:randomly")

    assert result.ret == 1
    result.stdout.fnmatch_lines(["*[[]OUTSIDE TMP[]] gained: *__pycache__*"])
