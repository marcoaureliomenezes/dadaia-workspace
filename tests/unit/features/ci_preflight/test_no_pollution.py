"""Intent: CONTRACT — 0.4.7 FR3 AC (the bare commands leave the tree clean); size: MEDIUM.

The cache is not born because a flag was typed; it is born because the tool was
configured to write one. `pyproject.toml` redirects ruff's and mypy's caches and
pytest's `addopts` carries `-p no:cacheprovider`, so this test runs the BARE commands —
exactly what an agent types by hand and what `dadaia ci preflight` now builds — inside a
throwaway copy of the repo's config, and asserts the tree stays clean.

A flag-level assertion would prove nothing here: the flags are gone.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.features.ci_preflight import checks_for

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CACHE_DIRS = (".ruff_cache", ".mypy_cache", ".pytest_cache")


def _pyproject() -> dict[str, object]:
    return tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_configuration_redirects_every_tool_cache_out_of_the_repo_tree() -> None:
    """One rule, both tools: a relative path that resolves outside the checkout."""
    config = _pyproject()["tool"]
    assert isinstance(config, dict)
    for section, key in (("ruff", "cache-dir"), ("mypy", "cache_dir")):
        value = str(config[section][key])  # type: ignore[index]
        assert value.startswith("../"), f"[tool.{section}] {key} must escape the repo tree"
    assert "-p no:cacheprovider" in str(config["pytest"]["ini_options"]["addopts"])  # type: ignore[index]


@pytest.mark.parametrize("quick", [False, True], ids=["full", "quick"])
def test_preflight_builds_bare_commands_with_no_cache_flags(quick: bool) -> None:
    """0.4.7 FR3: preflight runs what an agent types — no `--no-cache`, no `--cache-dir`."""
    for check in checks_for(quick=quick):
        if check.name.startswith(("ruff", "mypy --strict")):
            assert "--no-cache" not in check.argv, check
            assert "--cache-dir" not in check.argv, check


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize(
    ("tool", "argv"),
    [
        pytest.param("ruff", ("check", "probe.py"), id="ruff-check"),
        pytest.param("ruff", ("format", "--check", "probe.py"), id="ruff-format-check"),
        pytest.param("mypy", ("--strict", "probe.py"), id="mypy-strict"),
    ],
)
def test_the_bare_command_writes_no_cache_into_the_tree(
    tmp_path: Path, tool: str, argv: tuple[str, ...]
) -> None:
    """The real commands, unflagged, in a real tree carrying the real configuration."""
    binary = Path(sys.executable).parent / tool
    if not binary.exists():  # pragma: no cover — environment guard
        pytest.skip(f"{tool} not installed beside this interpreter")

    # The real topology: the checkout sits at workspace/repos/<slug>, so the relative
    # `../../.dadaia/tmp` redirect lands in THIS test's workspace — never two levels above
    # tmp_path, where it would seed a phantom `.dadaia/` for every later test.
    workspace = tmp_path
    tree = workspace / "repos" / "checkout"
    tree.mkdir(parents=True)
    shutil.copyfile(_REPO_ROOT / "pyproject.toml", tree / "pyproject.toml")
    (tree / "probe.py").write_text("VALUE: int = 1\n", encoding="utf-8")

    subprocess.run([str(binary), *argv], cwd=tree, capture_output=True, check=False)

    leaked = [name for name in _CACHE_DIRS if (tree / name).exists()]
    assert not leaked, f"bare `{tool} {' '.join(argv)}` wrote {leaked} into the tree"
    assert (workspace / ".dadaia" / "tmp").is_dir(), "the cache must land in the workspace"
    assert not (workspace.parent / ".dadaia").exists()
