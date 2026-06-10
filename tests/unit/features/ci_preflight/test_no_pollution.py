"""Unit tests for the ci-preflight self-pollution fix (T-010-25, AC-R8-02).

The preflight gate's own ruff/mypy checks must not create cache directories at
the repo root that its final pytest check then rejects. These tests pin the
argv-level contract:

  * ruff format --check and ruff check are invoked with --no-cache
  * mypy --strict has its cache redirected OUTSIDE the repo (--cache-dir under
    the workspace .dadaia/tmp/ zone, with a tmpdir fallback when no workspace)

They assert behavior via argv inspection, never by actually polluting the root.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.ci_preflight import checks_for
from dadaia_workspace.features.ci_preflight.service import resolve_mypy_cache_dir


def _check(name: str) -> tuple[str, ...]:
    for c in checks_for(quick=False):
        if c.name == name:
            return c.argv
    raise AssertionError(f"check {name!r} not found")


def test_ruff_format_check_has_no_cache() -> None:
    argv = _check("ruff format --check")
    assert "--no-cache" in argv


def test_ruff_check_has_no_cache() -> None:
    argv = _check("ruff check")
    assert "--no-cache" in argv


def test_mypy_cache_dir_redirected_outside_repo() -> None:
    argv = _check("mypy --strict")
    assert "--cache-dir" in argv
    idx = argv.index("--cache-dir")
    cache_dir = Path(argv[idx + 1])
    # The redirect must point OUTSIDE the dadaia-workspace lib repo working tree.
    repo_root = Path(__file__).resolve().parents[4]
    assert repo_root not in cache_dir.parents and cache_dir != repo_root


def test_mypy_cache_dir_under_workspace_tmp_when_workspace_present(tmp_path: Path) -> None:
    """When a workspace (with .dadaia/) is found, the cache lives under .dadaia/tmp/."""
    ws = tmp_path / "ws"
    (ws / ".dadaia").mkdir(parents=True)
    repo = ws / "repos" / "dadaia-workspace"
    repo.mkdir(parents=True)
    cache = resolve_mypy_cache_dir(start=repo)
    assert (ws / ".dadaia" / "tmp") in cache.parents or cache.parent == (ws / ".dadaia" / "tmp")
    assert ws / ".dadaia" in cache.parents


def test_mypy_cache_dir_falls_back_to_tmpdir_without_workspace(tmp_path: Path) -> None:
    """With no workspace .dadaia/ above start, fall back to a system tmp path."""
    lonely = tmp_path / "no" / "workspace" / "here"
    lonely.mkdir(parents=True)
    cache = resolve_mypy_cache_dir(start=lonely)
    # Falls back outside `lonely` (a system tmpdir), never inside the start tree.
    assert lonely not in cache.parents and cache != lonely


def test_quick_checks_also_carry_the_flags() -> None:
    names_to_argv = {c.name: c.argv for c in checks_for(quick=True)}
    assert "--no-cache" in names_to_argv["ruff format --check"]
    assert "--no-cache" in names_to_argv["ruff check"]
    assert "--cache-dir" in names_to_argv["mypy --strict"]
