"""RED tests — projection reconciliation has MEMORY (Class 2).

Bug ``retired-lib-asset-leaves-orphan-projection``: ``copy_tree`` returned before its
orphan-prune loop when the source dir no longer existed, so retiring an entire asset
family from the library never removed its projections — the instance kept ghost assets
forever. The ledger inverts the derivation: the desired state is diffed against the
RECORD of what was installed, not against whatever the current source happens to carry.

Safety invariant pinned here: prune only (in previous ledger) ∧ (not in current
projection) ∧ (on-disk sha == ledgered sha). Operator-modified orphans are retained and
surfaced; a missing/corrupt ledger bootstraps (record everything, prune nothing).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def _install_all(ws: Path) -> FileSystemPublicAssetManager:
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    return mgr


def test_retired_family_is_pruned_on_next_install(tmp_path: Path) -> None:
    """Retire an ENTIRE staged family ⇒ the next install removes its projections."""
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_all(ws)

    # Pick one universal skill as the retired family member.
    skills_src = ws / ".dadaia" / "agentic" / "skills"
    one = sorted(p for p in skills_src.iterdir() if p.is_dir())[0]
    projected = ws / ".agents" / "skills" / one.name / "SKILL.md"
    assert projected.is_file(), "fixture: the skill must project before retirement"

    # Retire the WHOLE family from staging (the copy_tree early-return hole).
    shutil.rmtree(skills_src)
    installed = mgr.install(ws, target="all")

    assert not projected.exists(), (
        "a retired asset family must disappear from the instance on the next install "
        "(ghost law bug: copy_tree returned before pruning when src was gone)"
    )
    assert any("[prune]" in line and one.name in line for line in installed)


def test_operator_modified_orphan_is_retained_and_surfaced(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_all(ws)

    skills_src = ws / ".dadaia" / "agentic" / "skills"
    one = sorted(p for p in skills_src.iterdir() if p.is_dir())[0]
    projected = ws / ".agents" / "skills" / one.name / "SKILL.md"
    projected.write_text(projected.read_text(encoding="utf-8") + "\nOPERATOR EDIT\n")

    shutil.rmtree(skills_src)
    installed = mgr.install(ws, target="all")

    assert projected.exists(), "an operator-modified orphan must NEVER be deleted"
    assert any(
        "operator-modified orphan retained" in line and one.name in line for line in installed
    )


def test_no_ledger_bootstrap_prunes_nothing(tmp_path: Path) -> None:
    """First ledgered install over a pre-ledger workspace: adopt, never delete."""
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_all(ws)

    ledger = ws / ".dadaia" / "states" / "install_ledger.json"
    assert ledger.is_file(), "install must persist the ledger"
    # Simulate a pre-ledger workspace: drop the ledger, plant a stray file in a
    # managed surface, reinstall — bootstrap must not touch it.
    ledger.unlink()
    stray = ws / ".agents" / "skills" / "operator-own-skill" / "SKILL.md"
    stray.parent.mkdir(parents=True)
    stray.write_text("mine\n", encoding="utf-8")

    installed = mgr.install(ws, target="all")

    assert stray.exists(), "bootstrap (no ledger) must prune nothing"
    assert not any("[prune]" in line and "operator-own-skill" in line for line in installed)


def test_scoped_install_never_prunes_other_scopes(tmp_path: Path) -> None:
    """A per-harness install must not treat other harnesses' entries as stale."""
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_all(ws)
    codex_agents = ws / ".codex" / "agents"
    assert any(codex_agents.glob("*.toml"))

    mgr.install(ws, target="claude")

    assert any(codex_agents.glob("*.toml")), (
        "a claude-scoped install must never prune codex projections via the ledger"
    )
