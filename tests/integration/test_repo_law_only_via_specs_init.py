"""Repo law has one writer: ``specs init`` (canon.REPO_LAW), once; ``public install``
never writes under ``repos/``.

Intent: CONTRACT — sa-public-install-writes-the-root-map-into-product-repos (WP-07);
size: MEDIUM (real public tree, real install).

K1: install before specs init leaves repos/<slug>/ untouched; specs init then writes the
    repo template, not the root map.
K2: an operator line appended to the repo AGENTS.md survives the next install.
K4: a repos/ path a former release ledgered is forgotten on upgrade, never pruned.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dadaia_workspace.core.models.install_ledger import InstallLedger, LedgerEntry
from dadaia_workspace.features.specs.canon import scaffold_repo_law
from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"


def _workspace(tmp_path: Path) -> tuple[Path, Path]:
    ws = tmp_path / "ws"
    repo = ws / "repos" / "zz-product"
    (repo / "tests").mkdir(parents=True)
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True)
    row = {
        "name": "zz-product",
        "state": "alive",
        "repo_slug": "zz-product",
        "repo_url": "https://example.com/zz-product.git",
        "created_at": "2026-01-01T00:00:00Z",
        "alive_since": "2026-01-01T00:00:00Z",
        "dead_since": None,
        "current_branch": "main",
    }
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": [row]}), encoding="utf-8"
    )
    return ws, repo


def test_install_first_then_specs_init_leaves_the_repo_template(tmp_path: Path) -> None:
    """K1."""
    ws, repo = _workspace(tmp_path)
    FileSystemPublicAssetManager().install(ws)
    assert not (repo / "AGENTS.md").exists()

    scaffold_repo_law(repo, project_name="zz-product")

    template = (_PUBLIC / "templates" / "repo-AGENTS.md").read_text(encoding="utf-8")
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == template.replace(
        "<repo-name>", "zz-product"
    )
    assert (repo / "tests" / "AGENTS.md").is_file()


def test_an_operator_edit_to_repo_law_survives_install(tmp_path: Path) -> None:
    """K2."""
    ws, repo = _workspace(tmp_path)
    scaffold_repo_law(repo, project_name="zz-product")
    law = repo / "AGENTS.md"
    law.write_text(law.read_text(encoding="utf-8") + "- zz operator rule\n", encoding="utf-8")
    edited = law.read_bytes()

    FileSystemPublicAssetManager().install(ws)
    FileSystemPublicAssetManager().install(ws, force=True)

    assert law.read_bytes() == edited


def test_a_formerly_ledgered_repo_copy_is_forgotten_never_pruned(tmp_path: Path) -> None:
    """K4."""
    ws, repo = _workspace(tmp_path)
    old = repo / "AGENTS.md"
    old.write_text("# former root-map copy\n", encoding="utf-8")
    entry = LedgerEntry(
        relpath="repos/zz-product/AGENTS.md",
        sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
        family="repos",
        kind="file",
    )
    states = ws / ".dadaia" / "states"
    JsonInstallLedgerStore().write(states, InstallLedger.of([entry]))

    FileSystemPublicAssetManager().install(ws)

    assert old.read_text(encoding="utf-8") == "# former root-map copy\n"
    ledger = JsonInstallLedgerStore().read(states)
    assert ledger is not None
    assert "repos/zz-product/AGENTS.md" not in ledger.by_relpath()
