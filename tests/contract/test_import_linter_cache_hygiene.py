"""Repo-hygiene probe — running ``lint-imports`` leaves no cache in the tree (v0.1.53 FR3).

import-linter's default cache directory is ``.import_linter_cache/`` at the working-dir
root. Inside a dadaia repo that directory is a hard repo-cleanliness violation (see the
workspace root ``AGENTS.md`` "Repo cleanliness" law — no tool cache/state dir may live in
a repo working tree). import-linter reads the cache location only from the CLI
(``--cache-dir`` / ``--no-cache``), never from ``setup.cfg``, so the sanctioned invocation
is ``lint-imports --no-cache``.

This probe does exactly what FR3 mandates: it RUNS ``lint-imports`` with the project config
and ``--no-cache``, then asserts the cache directory is absent from the repo tree. The run
must reach contract evaluation (proving the config is valid and not merely erroring out
before any caching would occur) — the two documented layering contracts are still red
(deferred to backlog ``import-boundary-enforcement``), so a non-zero exit is expected and
NOT asserted; what is asserted is that the run got as far as reporting contract results.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract, pytest.mark.slow]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SETUP_CFG = _REPO_ROOT / "setup.cfg"
_CACHE_DIR = _REPO_ROOT / ".import_linter_cache"


def _lint_imports_bin() -> str | None:
    """Resolve the ``lint-imports`` console script from the active venv.

    ``shutil.which`` scoped to the interpreter's directory handles the Windows
    executable suffix (``Scripts\\lint-imports.exe``) that a bare path join misses.
    """
    return shutil.which("lint-imports", path=str(Path(sys.executable).parent))


def test_lint_imports_runs_with_no_cache_and_leaves_no_cache_dir() -> None:
    bin_path = _lint_imports_bin()
    assert bin_path is not None, f"lint-imports not found next to interpreter {sys.executable}"

    # Guard: the cache must not be present before we start (a stale one would make the
    # post-run assertion pass vacuously and hide a regression).
    assert not _CACHE_DIR.exists(), (
        f"{_CACHE_DIR} already exists before the probe run — a prior lint-imports run left "
        "a cache in the tree (repo-hygiene violation); delete it."
    )

    result = subprocess.run(
        [bin_path, "--config", str(_SETUP_CFG), "--no-cache"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    combined = result.stdout + result.stderr

    # The run must reach contract evaluation — proving the config parsed and the graph
    # built (a config error would abort before this line is ever printed). Exit code is
    # intentionally NOT asserted: the two deferred layering contracts are still red.
    assert "Contracts:" in combined, (
        f"lint-imports did not reach contract evaluation — config or graph-build error:\n{combined}"
    )

    assert not _CACHE_DIR.exists(), (
        f"lint-imports created {_CACHE_DIR} despite --no-cache — repo-hygiene violation"
    )
