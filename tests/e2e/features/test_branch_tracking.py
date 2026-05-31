"""E2E: branch tracking through export → import + artifact trim (Fase 8D)."""

import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from dadaia_workspace.core.models.export import ExportOptions
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _init_repo(repo: Path, *, default_branch: str = "main") -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", default_branch)
    _git(repo, "config", "user.email", "test@test")
    _git(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("# r")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "init")


@pytest.fixture
def workspace_with_active_repo(tmp_path: Path) -> tuple[Path, Path, JsonContextStore]:
    workspace = tmp_path / "ws"
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True)

    repo_path = workspace / "repos" / "alpha"
    _init_repo(repo_path)
    _git(repo_path, "checkout", "-q", "-b", "feature/test")

    store = JsonContextStore(states)
    store.save(
        SpecContextProject(
            name="alpha",
            state=ContextState.ALIVE,
            repo_slug="alpha",
            repo_url="https://example.com/alpha.git",
            created_at="2026-01-01T00:00:00Z",
            alive_since="2026-01-02T00:00:00Z",
            dead_since=None,
            current_branch=None,
        )
    )
    return workspace, repo_path, store


def test_export_refreshes_current_branch_before_archive(
    workspace_with_active_repo: tuple[Path, Path, JsonContextStore], tmp_path: Path
) -> None:
    """T80 (part 1): export reads HEAD branch and persists in spec_contexts.json."""
    workspace, repo, store = workspace_with_active_repo
    svc = ExportService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace,
    )

    out = tmp_path / "dist"
    result = svc.run(ExportOptions(output=out, exclude_mnt=True))
    assert result.path is not None

    persisted = store.get("alpha")
    assert persisted is not None
    assert persisted.current_branch == "feature/test"


def test_export_manifest_lists_current_branch_per_context(
    workspace_with_active_repo: tuple[Path, Path, JsonContextStore], tmp_path: Path
) -> None:
    """T80 (part 2): the archive's export-manifest.json records branch."""
    workspace, _, store = workspace_with_active_repo
    svc = ExportService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace,
    )
    out = tmp_path / "dist"
    svc.run(ExportOptions(output=out, exclude_mnt=True))

    archive = next(out.glob("workspace-*.tar.gz"))
    with tarfile.open(archive, "r:gz") as tar:
        member = tar.getmember("export-manifest.json")
        f = tar.extractfile(member)
        assert f is not None
        manifest = json.loads(f.read())

    alpha = next(c for c in manifest["contexts"] if c["name"] == "alpha")
    assert alpha["current_branch"] == "feature/test"


def test_export_artifact_excludes_lib_only_dirs(
    workspace_with_active_repo: tuple[Path, Path, JsonContextStore], tmp_path: Path
) -> None:
    """T81: artifact must not include .dadaia/scripts/, .dadaia/agentic/, .dadaia/src/."""
    workspace, _, store = workspace_with_active_repo
    # Create the lib-only dirs that must be trimmed
    (workspace / ".dadaia" / "scripts").mkdir(parents=True)
    (workspace / ".dadaia" / "scripts" / "ctx-inject.sh").write_text("#!/bin/sh")
    (workspace / ".dadaia" / "agentic").mkdir(parents=True)
    (workspace / ".dadaia" / "agentic" / "manifest.json").write_text("{}")
    (workspace / ".dadaia" / "src").mkdir(parents=True)
    (workspace / ".dadaia" / "src" / "repos.xlsx").write_text("placeholder")

    svc = ExportService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace,
    )
    out = tmp_path / "dist"
    svc.run(ExportOptions(output=out, exclude_mnt=True))

    archive = next(out.glob("workspace-*.tar.gz"))
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()

    for forbidden in (".dadaia/scripts", ".dadaia/agentic", ".dadaia/src"):
        leaks = [n for n in names if n.startswith(forbidden)]
        assert not leaks, f"trim leaked: {forbidden} → {leaks}"
