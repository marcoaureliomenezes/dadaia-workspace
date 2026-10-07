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

pytestmark = pytest.mark.slow

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

_CREATES_A_RUFF_CACHE = """
import pytest

def test_inner(request: pytest.FixtureRequest):
    (request.config.rootpath / ".ruff_cache").mkdir(exist_ok=True)
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


def test_inner_runs_see_the_temp_home_and_fail_on_a_pycache_or_a_created_root_cache(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch, inner: Path, tmp_path: Path
) -> None:
    """One test, inner runs in order: each one's watched write would fail any inner session
    running beside it (the tripwires watch the ``tests/`` tree and the checkout).
    The last two pin T-010-25 / AC-R8-02 against the inner session's own rootdir (the
    pytester dir): a root cache dir the session creates fails it; one present before is
    ignored."""
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    monkeypatch.setenv("DADAIA_CONTEXT", "ghost")
    monkeypatch.setenv("HOME", str(foreign))
    monkeypatch.setenv("OUTER_FOREIGN_HOME", str(foreign))
    (inner / "test_home.py").write_text(_SEES_THE_TEMP_HOME, encoding="utf-8")
    (inner / "test_pycache.py").write_text(_WRITES_A_PYCACHE, encoding="utf-8")

    home = pytester.runpytest_subprocess(str(inner / "test_home.py"), "-p", "no:randomly")
    pycache = pytester.runpytest_subprocess(str(inner / "test_pycache.py"), "-p", "no:randomly")
    (inner / "test_ruff.py").write_text(_CREATES_A_RUFF_CACHE, encoding="utf-8")
    ruff = (str(inner / "test_ruff.py"), "-p", "no:randomly", f"--rootdir={pytester.path}")
    created = pytester.runpytest_subprocess(*ruff)
    preexisting = pytester.runpytest_subprocess(*ruff)

    assert home.ret == 0, home.stdout.str()
    assert pycache.ret == 1
    pycache.stdout.fnmatch_lines(["*[[]OUTSIDE TMP[]] gained: *__pycache__*"])
    assert created.ret == 1
    created.stdout.fnmatch_lines(["*[[]SESSION POLLUTION[]]*", "  .ruff_cache"])
    assert preexisting.ret == 0, preexisting.stdout.str()
    preexisting.stdout.no_fnmatch_line("*[[]SESSION POLLUTION[]]*")
