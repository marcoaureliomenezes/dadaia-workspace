"""Integration tests for public asset install projection flows."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

import pytest

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

pytestmark = pytest.mark.slow(reason="public asset install writes projected workspace files")


def _build_minimal_agentic_dir(tmp_path: Path) -> tuple[Path, Path]:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    agentic_dir = workspace_root / ".dadaia" / "agentic"
    agentic_dir.mkdir(parents=True)
    manifest = {
        "schema_version": "1",
        "package_version": "0.0.0-test",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "assets": [],
    }
    (agentic_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return agentic_dir, workspace_root


def test_invalid_target_raises(tmp_path: Path) -> None:
    _, workspace_root = _build_minimal_agentic_dir(tmp_path)
    with pytest.raises(PublicAssetError, match="Unsupported"):
        FileSystemPublicAssetManager().install(workspace_root, harness="invalid-target")


def test_install_leaves_only_ledger_owned_entries_under_claude(tmp_path: Path) -> None:
    """sa-doctor-reaps-harness-owned-entries#H4: the install ledger is
    the one owner of what the library writes under ``.claude/`` — every entry a real
    ``install`` leaves there is a ledger target or a directory holding one; size: MEDIUM
    (drives the real ``public/`` tree, no fake agentic dir).

    A category with no staged source (``commands`` retired at v0.1.1) must not
    materialise as an empty directory the ledger does not own.
    """
    workspace_root = tmp_path / "workspace"
    states_dir = workspace_root / ".dadaia" / "states"
    states_dir.mkdir(parents=True)

    FileSystemPublicAssetManager().install(workspace_root, harness="claude")

    ledger = JsonInstallLedgerStore().read(states_dir)
    assert ledger is not None
    targets = frozenset(ledger.by_relpath())
    owned_dirs = frozenset(
        parent.as_posix() for rel in targets for parent in PurePosixPath(rel).parents
    )
    entries = sorted(
        p.relative_to(workspace_root).as_posix() for p in (workspace_root / ".claude").iterdir()
    )
    assert entries, "install must project into .claude/"
    assert [e for e in entries if e not in targets and e not in owned_dirs] == []
    assert ".claude/commands" not in entries
