"""Shared integration-tier fixtures (T-7, v0.1.75 FR4).

The dominant wall-clock cost in ``tests/integration/`` is repeated
``WorkspaceService.init`` (full public stage+install) calls — historically ~40
per-test invocations across the ``cli/`` tree plus a further 16 in
``features/public/test_doctor_codex_checks.py``. This module builds each
distinct workspace shape ONCE per test session into a template directory and
hands every test a cheap ``shutil.copytree`` of that template into its own
``tmp_path`` — same isolation (no test can see another test's mutations),
~1 stage+install instead of ~1-per-test.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager


def _copy_template(template: Path, dest: Path) -> Path:
    """Copy *template* into *dest* (which must not yet exist) and return *dest*."""
    shutil.copytree(template, dest)
    return dest


@pytest.fixture(scope="session")
def _workspace_init_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A single ``WorkspaceService.init()`` result, built once per session."""
    template_root = tmp_path_factory.mktemp("workspace-init-template")
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(template_root)
    return template_root


@pytest.fixture()
def initialized_workspace(
    _workspace_init_template: Path,
    tmp_path: Path,
) -> Path:
    """Per-test copy of the session-scoped ``WorkspaceService.init()`` template.

    Equivalent in observable state to calling ``WorkspaceService.init(tmp_path)``
    directly, but the expensive full public stage+install underneath ``init()``
    runs once per test session rather than once per test.
    """
    dest = tmp_path / "workspace"
    return _copy_template(_workspace_init_template, dest)


@pytest.fixture(scope="session")
def _codex_installed_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A single full stage + install(target=codex) result, built once per session."""
    template_root = tmp_path_factory.mktemp("codex-installed-template")
    manager = FileSystemPublicAssetManager()
    manager.stage(template_root)
    manager.install(template_root, target="codex", force=True)
    venv_bin = template_root / ".dadaia" / ".venv" / "bin"
    venv_bin.mkdir(parents=True, exist_ok=True)
    (venv_bin / "python").symlink_to(Path(sys.executable))
    return template_root


@pytest.fixture()
def installed_codex_workspace(
    _codex_installed_template: Path,
    tmp_path: Path,
) -> Path:
    """Per-test copy of the session-scoped codex-target stage+install template."""
    dest = tmp_path / "workspace"
    shutil.copytree(_codex_installed_template, dest, symlinks=True)
    return dest
