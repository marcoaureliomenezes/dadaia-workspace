"""RED tests — the doctor sees unmanaged files inside lib-managed projection dirs.

Bug ``claude-doctor-blind-to-unmanaged-projection-files``: an extra ``.md`` dropped into
``.claude/rules/`` produced zero doctor lines. The fix adds NO second scanner and NO
allowlist: the doctor runs the install-ledger reconciliation READ-ONLY — a managed dir
is exactly a directory the ledger owns a file in; a file there that the ledger does not
own reads ``[foreign]``. Ruling 16: operator authorship is legitimate, so ``foreign``
is visible-but-non-blocking; the check is ATTESTING (it always speaks).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def _installed_ws(tmp_path: Path) -> tuple[Path, FileSystemPublicAssetManager]:
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    return ws, mgr


def _foreign(lines: list[DoctorLine]) -> list[str]:
    return [line.text for line in lines if line.status is DoctorStatus.FOREIGN]


def test_extra_rule_in_managed_dir_reads_foreign_and_never_blocks(tmp_path: Path) -> None:
    ws, mgr = _installed_ws(tmp_path)
    (ws / ".claude" / "rules" / "my-own-rule.md").write_text("# operator rule\n", "utf-8")

    lines = list(mgr.doctor(ws))
    hits = [t for t in _foreign(lines) if ".claude/rules/my-own-rule.md" in t]
    assert hits, "an unmanaged file in a lib-managed dir must surface as [foreign]"
    # Ruling 16 — operator authorship is legitimate: foreign never blocks.
    assert DoctorStatus.FOREIGN.blocking is False


def test_operator_skill_dir_and_root_files_are_not_flagged(tmp_path: Path) -> None:
    """A whole operator-created skill dir is NOT inside any ledger-managed dir (its
    parent dir belongs to the operator), and the workspace root is governed by the
    root whitelist, not the ledger — neither may read [foreign]."""
    ws, mgr = _installed_ws(tmp_path)
    own_skill = ws / ".claude" / "skills" / "my-private-skill"
    own_skill.mkdir(parents=True)
    (own_skill / "SKILL.md").write_text("---\nname: my-private-skill\n---\n", "utf-8")
    (ws / "prompt.md").write_text("operator root file\n", "utf-8")

    hits = _foreign(list(mgr.doctor(ws)))
    assert not any("my-private-skill" in t for t in hits)
    assert not any("prompt.md" in t for t in hits)


def test_foreign_scan_attests_clean_and_not_applicable(tmp_path: Path) -> None:
    ws, mgr = _installed_ws(tmp_path)
    rendered = [line.render() for line in mgr.doctor(ws)]
    assert any(
        line.startswith("[ok] ledger:foreign-scan") for line in rendered
    ), "a clean scan must still speak — silence is indistinguishable from a vanished check"

    # No ledger (pre-ledger workspace) ⇒ no authority to scan against ⇒ explicit stamp.
    (ws / ".dadaia" / "states" / "install_ledger.json").unlink()
    rendered_no_ledger = [line.render() for line in mgr.doctor(ws)]
    assert "[not-applicable] check:foreign-projections — no applicable objects" in (
        rendered_no_ledger
    )
