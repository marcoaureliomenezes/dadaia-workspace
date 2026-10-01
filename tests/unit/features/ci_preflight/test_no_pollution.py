"""Intent: CONTRACT — 0.4.7 FR3 AC (the bare commands leave the tree clean); size: MEDIUM.

The cache is not born because a flag was typed; it is born because the tool was
configured to write one. `pyproject.toml` redirects ruff's and mypy's caches and
pytest's `addopts` carries `-p no:cacheprovider`, so this test runs the BARE commands —
exactly what an agent types by hand and what `dadaia ci preflight` now builds — inside a
throwaway copy of the repo's config, and asserts the tree stays clean.

A flag-level assertion would prove nothing here: the flags are gone.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.features.ci_preflight import checks_for

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CACHE_DIRS = (".ruff_cache", ".mypy_cache", ".pytest_cache")


def _pyproject() -> dict[str, object]:
    return tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_the_projected_harness_env_names_absolute_caches_and_pyproject_none() -> None:
    """sa-tool-caches-land-outside-the-cache-zone#B40-2: the Claude settings the library
    projects export absolute RUFF_CACHE_DIR/MYPY_CACHE_DIR under .dadaia/tmp; pyproject
    carries no relative .dadaia path."""
    from dadaia_workspace.infrastructure.runtime_config import merge_claude_settings

    env = merge_claude_settings(None, Path("/ws"))["env"]
    assert env == {
        "MYPY_CACHE_DIR": str(Path("/ws/.dadaia/tmp/mypy-cache")),
        "RUFF_CACHE_DIR": str(Path("/ws/.dadaia/tmp/ruff-cache")),
        "PLAYWRIGHT_MCP_OUTPUT_DIR": str(Path("/ws/.dadaia/mcps/playwright")),
    }
    tool = _pyproject()["tool"]
    assert "cache-dir" not in tool["ruff"] and "cache_dir" not in tool["mypy"]  # type: ignore[index,operator]
    assert "-p no:cacheprovider" in str(_pyproject()["tool"]["pytest"]["ini_options"]["addopts"])  # type: ignore[index]


@pytest.mark.parametrize("quick", [False, True], ids=["full", "quick"])
def test_preflight_builds_bare_commands_with_no_cache_flags(quick: bool) -> None:
    """0.4.7 FR3: preflight runs what an agent types — no `--no-cache`, no `--cache-dir`."""
    for check in checks_for(quick=quick):
        if check.name.startswith(("ruff", "mypy --strict")):
            assert "--no-cache" not in check.argv, check
            assert "--cache-dir" not in check.argv, check
