"""Intent: CONTRACT — AC3.2 / T-047-56: a link rule falls back to a verified copy.

Windows without Developer Mode raises ``OSError`` from ``os.symlink``. The projection
must still deliver the content — and the ledger must still be able to tell that entry
apart from a real link, which ``read_bytes()`` never can: it follows the link.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from dadaia_workspace.core.models.install_ledger import InstallLedger, LedgerEntry
from dadaia_workspace.infrastructure.projection import ProjectionRule, install_rules, link_render
from dadaia_workspace.infrastructure.public_assets_common import _entry_digest

pytestmark = pytest.mark.unit


def _authored(root: Path) -> Path:
    skill = root / ".agents" / "skills" / "dd-example"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: dd-example\n---\nbody\n", encoding="utf-8")
    (skill / "NOTES.md").write_text("deeper\n", encoding="utf-8")
    return skill


def _rule(root: Path, authored: Path) -> ProjectionRule:
    return ProjectionRule(
        label="claude:skills/dd-example",
        harness="claude",
        dst=root / ".claude" / "skills" / "dd-example",
        render=link_render,
        link_to=authored,
    )


def test_symlink_path_writes_one_relative_link_recorded_as_symlink(tmp_path: Path) -> None:
    authored = _authored(tmp_path)
    rule = _rule(tmp_path, authored)

    transcript = install_rules([rule], force=False)

    assert [(line.path, line.kind) for line in transcript.lines] == [(rule.dst, "symlink")]
    assert os.readlink(rule.dst) == "../../.agents/skills/dd-example"
    assert (rule.dst / "SKILL.md").read_text(encoding="utf-8").startswith("---")


def test_copy_fallback_when_symlink_raises_is_hash_equal_and_kinded_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authored = _authored(tmp_path)
    rule = _rule(tmp_path, authored)

    def _refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError(1314, "A required privilege is not held by the client")

    monkeypatch.setattr(os, "symlink", _refuse)

    transcript = install_rules([rule], force=False)

    assert {line.kind for line in transcript.lines} == {"copy"}
    assert sorted(p.name for p in transcript.paths()) == ["NOTES.md", "SKILL.md"]
    assert not rule.dst.is_symlink()
    for source in sorted(authored.rglob("*")):
        copied = rule.dst / source.relative_to(authored)
        assert copied.read_bytes() == source.read_bytes()

    entry = LedgerEntry(
        relpath=".claude/skills/dd-example/SKILL.md",
        sha256=_entry_digest(rule.dst / "SKILL.md") or "",
        family="claude",
        kind="copy",
    )
    assert entry.sha256 == hashlib.sha256((authored / "SKILL.md").read_bytes()).hexdigest()
    assert InstallLedger.of([entry]).to_dict()["entries"] == [
        {
            "relpath": ".claude/skills/dd-example/SKILL.md",
            "sha256": entry.sha256,
            "family": "claude",
            "kind": "copy",
        }
    ]


def test_a_symlink_entry_digests_its_target_string_not_the_bytes_behind_it(
    tmp_path: Path,
) -> None:
    authored = _authored(tmp_path)
    rule = _rule(tmp_path, authored)
    install_rules([rule], force=False)

    assert _entry_digest(rule.dst) == hashlib.sha256(b"../../.agents/skills/dd-example").hexdigest()


def test_a_pre_kind_ledger_entry_migrates_as_file() -> None:
    parsed = InstallLedger.from_dict(
        {
            "schema_version": "1",
            "entries": [{"relpath": ".codex/config.toml", "sha256": "ab", "family": "codex"}],
        }
    )
    assert parsed.entries[0].kind == "file"


def test_prune_never_follows_a_link_into_the_authored_tree(tmp_path: Path) -> None:
    """Intent: CONTRACT — T-047-56: the ledger's prune stops at a symlinked parent.

    An instance upgrading to the link projection carries ledger entries like
    ``.claude/skills/dd-x/SKILL.md`` whose parent is now a symlink onto
    ``.agents/skills/dd-x``. Resolving that relpath reaches the AUTHORED file with the
    ledgered digest — pruning it deletes the source of every harness view at once.
    """
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

    authored = _authored(tmp_path)
    install_rules([_rule(tmp_path, authored)], force=False)
    stale = tmp_path / ".claude" / "skills" / "dd-example" / "SKILL.md"

    assert stale.is_file(), "the link resolves onto the authored file"
    assert not FileSystemPublicAssetManager._reachable_without_link(stale, tmp_path)
    assert FileSystemPublicAssetManager._reachable_without_link(authored / "SKILL.md", tmp_path)
