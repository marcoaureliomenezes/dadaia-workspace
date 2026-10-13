"""``dadaia context create <name> --main-repo <url>`` where the NAME differs from the repo SLUG
(the directory under ``repos/``) succeeds, and ``create`` refuses a name the rest of the CLI
cannot use.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.fixtures.harness_env import claude_hook_env

_NAME = "meu-projeto"
_SLUG = "repo-diferente"
_TIMEOUT = 180


def _dadaia(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", *args],
        cwd=workspace,
        env=claude_hook_env(workspace, extra={"DADAIA_CONTEXT": _NAME}),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(root, harnesses=L1_ENTRY_HARNESSES)
    remote = tmp_path / f"{_SLUG}.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, timeout=_TIMEOUT)
    created = _dadaia(root, "context", "create", _NAME, "--main-repo", str(remote))
    assert created.returncode == 0, created.stdout + created.stderr
    return root


def test_create_refuses_a_name_no_other_verb_can_use(workspace: Path) -> None:
    """`create` must refuse exactly what the rest of the CLI refuses.

    A name with spaces or non-ASCII characters would otherwise be created and then rejected by
    `bind` and every workflow against the `[A-Za-z0-9_-]+` allowlist, leaving the operator a
    context they can create and never use.

    The check reuses the resolver's own allowlist rather than inventing a second, stricter
    opinion, so "created" and "usable" cannot drift apart.
    """
    for bad in ("meu projeto", "projeto-café", "../escape"):
        proc = _dadaia(workspace, "context", "create", bad, "--main-repo", "x")
        combined = proc.stdout + proc.stderr
        assert proc.returncode != 0, f"create accepted the unusable name {bad!r}"
        assert "Traceback" not in combined
        assert "letters, digits" in combined, combined
