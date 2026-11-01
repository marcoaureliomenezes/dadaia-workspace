"""The size marker comes from what a test reaches, never from its folder. Each case
is a real collected item (pytester, under ``tmp_path``) that the root conftest's
collection hook marks."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests import conftest

_CHECKOUT = Path(__file__).resolve().parents[2]

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


_SUBPROCESS = """
import subprocess

def test_inner():
    assert subprocess.sys is not None
"""
_PYTESTER = """
def test_inner(pytester):
    pass
"""
_EXPLICIT_SMALL = """
import subprocess
import pytest

@pytest.mark.small
def test_inner():
    assert subprocess.sys is not None
"""


def _marked(pytester: pytest.Pytester, source: str, under: str) -> pytest.Item:
    """The first item of *source*, run through the conftest hook as a test at ``<checkout>/<under>``."""
    item = pytester.getitems(source)[0]
    item.path = _CHECKOUT / under / "test_inner_case.py"
    conftest.pytest_collection_modifyitems(item.config, [item])
    return item


@pytest.mark.parametrize(
    ("source", "size", "other"),
    [
        pytest.param(_REAL_GIT, "medium", "small", id="real-git-is-medium"),
        pytest.param(_PURE, "small", "medium", id="pure-is-small"),
        pytest.param(_EXPLICIT, "medium", "small", id="explicit-medium-wins"),
        pytest.param(_SUBPROCESS, "medium", "small", id="subprocess-is-medium"),
        pytest.param(
            "from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient\n"
            "def test_inner():\n    pass\n",
            "medium",
            "small",
            id="git-client-is-medium",
        ),
        pytest.param(
            "from dadaia_workspace.infrastructure.subprocess_runner import (\n"
            "    SubprocessProcessRunner,\n)\n"
            "def test_inner():\n    pass\n",
            "medium",
            "small",
            id="process-runner-is-medium",
        ),
        pytest.param(
            "from tests.helpers.worktree_ws import run\ndef test_inner():\n    pass\n",
            "medium",
            "small",
            id="worktree-ws-is-medium",
        ),
        pytest.param(_PYTESTER, "medium", "small", id="pytester-is-medium"),
        pytest.param(_EXPLICIT_SMALL, "small", "medium", id="explicit-small-wins"),
    ],
)
def test_size_follows_what_the_test_reaches(
    pytester: pytest.Pytester, source: str, size: str, other: str
) -> None:
    item = _marked(pytester, source, "tests/tmp")
    assert item.get_closest_marker(size) is not None
    assert item.get_closest_marker(other) is None


def test_a_journey_under_e2e_is_e2e_whatever_it_reaches(pytester: pytest.Pytester) -> None:
    item = _marked(pytester, _SUBPROCESS, "tests/e2e")
    assert item.get_closest_marker("e2e") is not None
    assert item.get_closest_marker("medium") is None
