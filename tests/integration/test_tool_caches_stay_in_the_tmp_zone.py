"""Tool caches land in the workspace's tmp zone from any cwd — never in the tree.

sa-tool-caches-land-outside-the-cache-zone#B40-1, #B40-2, #B40-3; AC2.14 (T-050-119). Size: MEDIUM
(real ruff/mypy subprocesses and a real git worktree in tmp_path).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CACHE_DIRS = (".ruff_cache", ".mypy_cache", ".pytest_cache")


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize(
    ("tool", "argv"),
    [
        pytest.param("ruff", ("check", "probe.py"), id="ruff-check"),
        pytest.param("ruff", ("format", "--check", "probe.py"), id="ruff-format-check"),
        pytest.param("mypy", ("--strict", "probe.py"), id="mypy-strict"),
        pytest.param("pytest", ("-q", "probe.py"), id="pytest"),
    ],
)
def test_the_bare_command_writes_no_cache_into_the_tree(
    tmp_path: Path, tool: str, argv: tuple[str, ...]
) -> None:
    """sa-tool-caches-land-outside-the-cache-zone#B40-1, #B40-3: the bare command, run with
    the projected harness env from the repo top, a subdirectory and a harness worktree,
    leaves no cache and no nested .dadaia/ in the tree; the doctor stays clean."""
    from dadaia_workspace.features.spec_context.doctor import DoctorService, FindingVerdict
    from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
    from dadaia_workspace.infrastructure.runtime_config import merge_claude_settings
    from tests.fixtures.stores import context_store

    binary = Path(sys.executable).parent / tool
    if not binary.exists():  # pragma: no cover — environment guard
        pytest.skip(f"{tool} not installed beside this interpreter")
    workspace = tmp_path
    for zone in ("tmp", "states", "sessions", "reaped"):
        (workspace / ".dadaia" / zone).mkdir(parents=True, exist_ok=True)
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"contexts": [{"name": "demo", "repo_slug": "demo", "state": "alive"}]}', encoding="utf-8"
    )
    repo = workspace / "repos" / "demo"
    (repo / "pkg" / "sub").mkdir(parents=True)
    shutil.copyfile(_REPO_ROOT / "pyproject.toml", repo / "pyproject.toml")
    for where in (repo, repo / "pkg" / "sub"):
        (where / "probe.py").write_text("VALUE: int = 1\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "init")
    worktree = repo / ".claude" / "worktrees" / "wt1"
    _git(repo, "worktree", "add", "-q", "-b", "wt/1", str(worktree))
    projected = merge_claude_settings({"env": {"OPERATOR": "kept"}}, workspace)["env"]
    assert projected["OPERATOR"] == "kept"  # type: ignore[index]  # AC2.14: operator keys kept
    assert projected["PLAYWRIGHT_MCP_OUTPUT_DIR"] == f"{workspace}/.dadaia/mcps/playwright"  # type: ignore[index]
    env = {**os.environ, **projected}  # type: ignore[dict-item]

    for cwd in (repo, repo / "pkg" / "sub", worktree):
        subprocess.run([str(binary), *argv], cwd=cwd, env=env, capture_output=True, check=False)

    nested = sorted(p.relative_to(repo).as_posix() for p in repo.rglob(".dadaia"))
    leaked = sorted(
        p.relative_to(repo).as_posix() for name in _CACHE_DIRS for p in repo.rglob(name)
    )
    assert (nested, leaked) == ([], [])
    states = workspace / ".dadaia" / "states"
    findings = DoctorService(context_store(states), GitSubprocessClient(), workspace).scan()
    assert [f.path for f in findings if f.verdict is FindingVerdict.SLOP] == []
