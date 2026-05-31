"""Integration tests for ``dadaia migrate`` (state-file migration) CLI command.

AC-T10c-1..4 coverage; uses Typer's CliRunner on real tmp_path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _v1_data() -> dict:  # type: ignore[type-arg]
    return {
        "schema_version": "1",
        "contexts": [
            {
                "name": "my-ctx",
                "state": "ativo",
                "repo_slug": "my-ctx",
                "repo_url": "https://github.com/org/my-ctx",
                "is_primary": True,
                "created_at": "2026-01-01T00:00:00Z",
                "activated_at": "2026-05-01T00:00:00Z",
            }
        ],
    }


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture()
def v1_workspace(workspace: Path) -> Path:
    """Overwrite spec_contexts.json with v1 data."""
    states = workspace / ".dadaia" / "states"
    (states / "spec_contexts.json").write_text(json.dumps(_v1_data()))
    # Write a primary_context.json too
    (states / "primary_context.json").write_text(
        json.dumps({"name": "my-ctx", "repo_slug": "my-ctx", "specs_dir": "/x"})
    )
    return workspace


# ---------------------------------------------------------------------------
# AC-T10c-1: --dry-run prints planned changes, exits 0, writes nothing
# ---------------------------------------------------------------------------


def test_migrate_dry_run_exits_0_and_writes_nothing(v1_workspace: Path) -> None:
    states = v1_workspace / ".dadaia" / "states"
    before = (states / "spec_contexts.json").read_text()
    result = _runner.invoke(app, ["migrate", "--dry-run"])
    assert result.exit_code == 0, result.output
    # File unchanged
    after = (states / "spec_contexts.json").read_text()
    assert before == after
    # Output contains migration info
    assert "ativo" in result.output or "alive" in result.output or "1" in result.output


# ---------------------------------------------------------------------------
# AC-T10c-2: --yes performs all 12 actions, exits 0
# ---------------------------------------------------------------------------


def test_migrate_yes_migrates_v1_to_v2(v1_workspace: Path) -> None:
    states = v1_workspace / ".dadaia" / "states"
    result = _runner.invoke(app, ["migrate", "--yes"])
    assert result.exit_code == 0, result.output

    data = json.loads((states / "spec_contexts.json").read_text())
    assert data["schema_version"] == "2"
    row = data["contexts"][0]
    assert row["state"] == "alive"
    assert "is_primary" not in row
    assert "activated_at" not in row


def test_migrate_yes_creates_required_dirs(v1_workspace: Path) -> None:
    """AC-T10c-6: sessions/, locks/implementation/, states/ctx_locks/ created."""
    _runner.invoke(app, ["migrate", "--yes"])
    assert (v1_workspace / ".dadaia" / "sessions").is_dir()
    assert (v1_workspace / ".dadaia" / "locks" / "implementation").is_dir()
    assert (v1_workspace / ".dadaia" / "states" / "ctx_locks").is_dir()


def test_migrate_yes_deletes_primary_context_json(v1_workspace: Path) -> None:
    """AC-T10c-5: primary_context.json must not exist after migration."""
    primary = v1_workspace / ".dadaia" / "states" / "primary_context.json"
    assert primary.exists()
    _runner.invoke(app, ["migrate", "--yes"])
    assert not primary.exists()


# ---------------------------------------------------------------------------
# AC-T10c-3: idempotent on v2 workspace
# ---------------------------------------------------------------------------


def test_migrate_on_v2_workspace_is_noop(workspace: Path) -> None:
    """Migrating a v2 workspace must report nothing to do and exit 0."""
    result = _runner.invoke(app, ["migrate", "--yes"])
    assert result.exit_code == 0, result.output
    assert (
        "schema_version 2" in result.output
        or "nothing to do" in result.output.lower()
        or "already" in result.output.lower()
    )


# ---------------------------------------------------------------------------
# tree-v2 subcommand still works after adding bare migrate
# ---------------------------------------------------------------------------


def test_tree_v2_subcommand_still_works(tmp_path: Path) -> None:
    """migrate tree-v2 must still function as a subcommand."""
    specs = tmp_path / "specs"
    specs.mkdir()
    foundation = specs / "foundation"
    foundation.mkdir()
    (foundation / "SPEC.md").write_text("# Foundation\n")

    result = _runner.invoke(app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "MOVE" in result.output
    # Filesystem unchanged
    assert foundation.is_dir()
