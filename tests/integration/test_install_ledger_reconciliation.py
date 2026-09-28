"""Projection reconciliation diffs against the install ledger: prune only a pristine orphan.

Intent: CONTRACT — retired-lib-asset-leaves-orphan-projection.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.harness_profile import register_all


def _install_all(ws: Path) -> FileSystemPublicAssetManager:
    mgr = FileSystemPublicAssetManager()
    register_all(ws)
    mgr.install(ws)
    return mgr


def test_retired_family_is_pruned_on_next_install(tmp_path: Path) -> None:
    """A retired family's pristine projection is pruned; an operator-modified one is retained.

    sa-public-install-unlinks-operator-files-outside-its-ledger#D3;
    sa-public-install-unlinks-operator-files-outside-its-ledger#D4;
    sa-doctor-reaps-harness-owned-entries#H4.
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_all(ws)
    skills_src = ws / ".dadaia" / "agentic" / "skills"
    pristine, edited = sorted(p.name for p in skills_src.iterdir() if p.is_dir())[:2]
    gone = ws / ".agents" / "skills" / pristine / "SKILL.md"
    kept = ws / ".agents" / "skills" / edited / "SKILL.md"
    assert gone.is_file()
    kept.write_text(kept.read_text(encoding="utf-8") + "\nOPERATOR EDIT\n")

    shutil.rmtree(skills_src)
    installed = mgr.install(ws)

    assert not gone.exists()
    assert any("[prune]" in line and pristine in line for line in installed)
    assert kept.exists()
    assert any("operator-modified orphan retained" in ln and edited in ln for ln in installed)


def test_no_ledger_bootstrap_prunes_nothing(tmp_path: Path) -> None:
    """sa-public-install-unlinks-operator-files-outside-its-ledger#D5 — no ledger: prune nothing."""
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_all(ws)

    ledger = ws / ".dadaia" / "states" / "install_ledger.json"
    assert ledger.is_file()
    ledger.unlink()
    stray = ws / ".agents" / "skills" / "operator-own-skill" / "SKILL.md"
    stray.parent.mkdir(parents=True)
    stray.write_text("mine\n", encoding="utf-8")

    installed = mgr.install(ws)

    assert stray.exists()
    assert not any("[prune]" in line and "operator-own-skill" in line for line in installed)


def test_every_install_keeps_every_ledgered_path_the_library_still_ships(tmp_path: Path) -> None:
    """sa-scoped-public-install-prunes-the-gate-wiring#L2,
    sa-public-install-unlinks-operator-files-outside-its-ledger#D3 — a whole, forced or
    claude-scoped install keeps every previously ledgered path on disk."""
    from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore

    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_all(ws)
    states = ws / ".dadaia" / "states"
    before = JsonInstallLedgerStore().read(states)
    assert before is not None
    for variant in ({}, {"force": True}, {"harness": "claude"}):
        mgr.install(ws, **variant)  # type: ignore[arg-type]
        missing = [
            rel
            for rel in before.by_relpath()
            if not (ws / rel).is_symlink() and not (ws / rel).exists()
        ]
        assert missing == [], variant
