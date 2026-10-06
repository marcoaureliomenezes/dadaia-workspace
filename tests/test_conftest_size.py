"""AC7.3: the size marker comes from what a test reaches, never from its folder. Each case
is judged by a real inner collection (pytester) over a throwaway module placed under the
checkout's gitignored ``tests/tmp/``, where the root conftest applies."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

_CHECKOUT = Path(__file__).resolve().parents[1]

_REAL_GIT = """
from tests.fixtures.real_git import git

def test_inner(tmp_path):
    git(tmp_path, "--version")
"""
_PURE = """
def test_inner():
    assert 1 + 1 == 2
"""
_EXPLICIT = """
import pytest

@pytest.mark.medium
def test_inner():
    pass
"""

_RED = pytest.mark.xfail(strict=True, reason="size derives from the folder until J7.S2.T1")


@pytest.fixture()
def inner() -> Iterator[Path]:
    where = _CHECKOUT / "tests" / "tmp" / f"size-{uuid.uuid4().hex[:8]}"
    where.mkdir(parents=True)
    yield where
    shutil.rmtree(where, ignore_errors=True)


@_RED
@pytest.mark.parametrize(
    ("source", "size", "other"),
    [
        pytest.param(_REAL_GIT, "medium", "small", id="real-git-is-medium"),
        pytest.param(_PURE, "small", "medium", id="pure-is-small"),
        pytest.param(_EXPLICIT, "medium", "small", id="explicit-medium-wins"),
    ],
)
def test_size_follows_what_the_test_reaches(
    pytester: pytest.Pytester, inner: Path, source: str, size: str, other: str
) -> None:
    (inner / "test_inner_case.py").write_text(source, encoding="utf-8")
    nodeid = f"tests/tmp/{inner.name}/test_inner_case.py::test_inner"

    def collected(marker: str) -> list[str]:
        run = pytester.runpytest_subprocess(
            "--collect-only", "-q", "-p", "no:randomly", "-m", marker, str(inner)
        )
        return [line for line in run.outlines if "::" in line]

    assert collected(size) == [nodeid]
    assert collected(other) == []
