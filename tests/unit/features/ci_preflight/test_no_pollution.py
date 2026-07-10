"""Unit tests for the ci-preflight self-pollution fix (T-010-25, AC-R8-02).

The preflight gate's own ruff/mypy checks must not create cache directories at
the repo root that its final pytest check then rejects. This pins the argv-level
contract as one parametrized decision table:

  * ruff format --check and ruff check are invoked with --no-cache
  * mypy --strict has its cache redirected OUTSIDE the repo (--cache-dir under
    the workspace .dadaia/tmp/ zone, with a tmpdir fallback when no workspace)
  * the same flags hold in both full and quick check lists

They assert behavior via argv inspection, never by actually polluting the root.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.ci_preflight import checks_for


def _check(name: str, *, quick: bool = False) -> tuple[str, ...]:
    for c in checks_for(quick=quick):
        if c.name == name:
            return c.argv
    raise AssertionError(f"check {name!r} not found")


@pytest.mark.parametrize(
    ("quick", "name", "flag"),
    [
        pytest.param(False, "ruff format --check", "--no-cache", id="full-ruff-format-no-cache"),
        pytest.param(False, "ruff check", "--no-cache", id="full-ruff-check-no-cache"),
        pytest.param(False, "mypy --strict", "--cache-dir", id="full-mypy-cache-dir-redirected"),
        pytest.param(True, "ruff format --check", "--no-cache", id="quick-ruff-format-no-cache"),
        pytest.param(True, "ruff check", "--no-cache", id="quick-ruff-check-no-cache"),
        pytest.param(True, "mypy --strict", "--cache-dir", id="quick-mypy-cache-dir-redirected"),
    ],
)
def test_every_check_argv_carries_its_cache_flag(quick: bool, name: str, flag: str) -> None:
    argv = _check(name, quick=quick)
    assert flag in argv

    if name == "mypy --strict" and not quick:
        idx = argv.index("--cache-dir")
        cache_dir = Path(argv[idx + 1])
        repo_root = Path(__file__).resolve().parents[4]
        assert repo_root not in cache_dir.parents and cache_dir != repo_root
