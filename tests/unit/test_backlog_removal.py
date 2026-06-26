"""T-26-04 — the residual-aware closure removal hook (SPEC §3.6 removal, ADR-C).

apply_removal computes, per consumed item, the residual = intents whose bound anchors are
NOT in the shipped set:

* residual > 0  -> rewrite-down-to-residual (strip only shipped intents) and KEEP the file.
* residual == 0 -> copy to specs/_archive/<release>/consumed-backlog/<slug>.md THEN unlink;
  the archive copy MUST exist before the removal (the only surviving copy — backlog is
  gitignored).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.backlog.removal import RemovalAction, apply_removal
from dadaia_workspace.features.backlog.subject_registry import build_registry

# Two planted code anchors so the registry binds both refs directly.
_REF_KEEP = "pkg/keep.py#kept"
_REF_SHIP = "pkg/ship.py#shipped"

_PARTIAL_ITEM = f"""\
---
name: partial-item
status: candidate
intents:
  - subject: {{ kind: code, ref: "{_REF_SHIP}" }}
    change: "this part shipped"
  - subject: {{ kind: code, ref: "{_REF_KEEP}" }}
    change: "this part survives"
---

# partial
Residual body that must survive a rewrite.
"""

_FULLY_SHIPPED_ITEM = f"""\
---
name: done-item
status: candidate
intents:
  - subject: {{ kind: code, ref: "{_REF_SHIP}" }}
    change: "all of it shipped"
---

# done
Body that goes to the archive copy.
"""


def _build(tmp_path: Path) -> tuple[Path, Path, object]:
    """Plant a specs tree + injected source root; return (backlog_dir, archive_root, registry)."""
    specs = tmp_path / "specs"
    backlog = specs / "backlog"
    backlog.mkdir(parents=True)
    (backlog / "partial-item.md").write_text(_PARTIAL_ITEM, encoding="utf-8")
    (backlog / "done-item.md").write_text(_FULLY_SHIPPED_ITEM, encoding="utf-8")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "keep.py").write_text("def kept() -> None:\n    pass\n", encoding="utf-8")
    (pkg / "ship.py").write_text("def shipped() -> None:\n    pass\n", encoding="utf-8")
    registry = build_registry(
        source_root=tmp_path,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=tmp_path / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs,
    )
    return backlog, specs / "_archive", registry


def test_residual_item_rewritten_and_kept(tmp_path: Path) -> None:
    backlog, archive_root, registry = _build(tmp_path)

    result = apply_removal(
        backlog_dir=backlog,
        archive_root=archive_root,
        release_id="v0.1.26",
        shipped_anchors={_REF_SHIP},
        registry=registry,
    )

    partial = backlog / "partial-item.md"
    assert partial.is_file(), "an item with surviving intents is KEPT"
    text = partial.read_text(encoding="utf-8")
    assert _REF_KEEP in text
    assert _REF_SHIP not in text, "the shipped intent is stripped down to residual"
    assert "this part survives" in text
    action = next(a for a in result.actions if a.slug == "partial-item")
    assert action.action is RemovalAction.REWRITTEN


def test_fully_shipped_item_archived_then_removed(tmp_path: Path) -> None:
    backlog, archive_root, registry = _build(tmp_path)

    result = apply_removal(
        backlog_dir=backlog,
        archive_root=archive_root,
        release_id="v0.1.26",
        shipped_anchors={_REF_SHIP},
        registry=registry,
    )

    done = backlog / "done-item.md"
    archive_copy = archive_root / "v0.1.26" / "consumed-backlog" / "done-item.md"
    assert not done.exists(), "a zero-residual item is removed from the live SET"
    assert archive_copy.is_file(), "a durable archive copy survives"
    assert "all of it shipped" in archive_copy.read_text(encoding="utf-8")
    action = next(a for a in result.actions if a.slug == "done-item")
    assert action.action is RemovalAction.ARCHIVED_AND_REMOVED


def test_archive_copy_exists_before_removal(tmp_path: Path) -> None:
    """ADR-C safety: the copy must precede the unlink — never delete the only copy."""
    backlog, archive_root, registry = _build(tmp_path)
    archive_copy = archive_root / "v0.1.26" / "consumed-backlog" / "done-item.md"
    live = backlog / "done-item.md"

    original_unlink = Path.unlink
    seen: dict[str, bool] = {}

    def spy_unlink(self: Path, *args: object, **kwargs: object) -> None:
        if self == live:
            # At the moment the live file is unlinked, the archive copy must already exist.
            seen["copy_present_at_unlink"] = archive_copy.is_file()
        original_unlink(self, *args, **kwargs)

    import dadaia_workspace.features.backlog.removal as removal_mod

    orig = removal_mod.Path.unlink
    removal_mod.Path.unlink = spy_unlink  # type: ignore[method-assign,assignment]
    try:
        apply_removal(
            backlog_dir=backlog,
            archive_root=archive_root,
            release_id="v0.1.26",
            shipped_anchors={_REF_SHIP},
            registry=registry,
        )
    finally:
        removal_mod.Path.unlink = orig  # type: ignore[method-assign]

    assert seen.get("copy_present_at_unlink") is True


def test_unrelated_item_untouched(tmp_path: Path) -> None:
    backlog, archive_root, registry = _build(tmp_path)
    # Nothing shipped that matches partial's residual-only anchor → partial fully survives,
    # done-item shares no shipped anchor → untouched too.
    result = apply_removal(
        backlog_dir=backlog,
        archive_root=archive_root,
        release_id="v0.1.26",
        shipped_anchors={"pkg/other.py#nope"},
        registry=registry,
    )
    assert (backlog / "partial-item.md").is_file()
    assert (backlog / "done-item.md").is_file()
    assert all(a.action is RemovalAction.UNCHANGED for a in result.actions)
