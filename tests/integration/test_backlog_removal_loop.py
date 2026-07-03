"""T-26-08 — the BL-STALE loop closes (SPEC §3.6 + acceptance §3.7.10).

End-to-end over the pure ops + the R1 doctor: writer (release-definition) → removal
(closure) → ``run_backlog_doctor``:

- after the writer + removal run, ``backlog doctor`` reports **zero** BL-STALE;
- a consumed slug **artificially left behind** in ``specs/backlog/`` → BL-STALE ERROR.

All roots are injected under ``tmp_path`` — no real filesystem outside it, no cwd.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.backlog.doctor import BacklogDoctorCode, run_backlog_doctor
from dadaia_workspace.features.backlog.removal import RemovalAction
from dadaia_workspace.features.backlog.removal_lifecycle import (
    consume_at_release_definition,
    remove_at_closure,
)
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry

_REF_SHIP = "pkg/ship.py#shipped"
_REF_KEEP = "pkg/keep.py#kept"

_FULLY_SHIPPED = f"""\
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

_PARTIAL = f"""\
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
Residual body that must survive.
"""


def _plant(tmp_path: Path) -> tuple[Path, Path, Registry]:
    """Plant a specs tree + injected source root; return (backlog_dir, archive_root, registry)."""
    specs = tmp_path / "specs"
    backlog = specs / "backlog"
    backlog.mkdir(parents=True)
    (backlog / "done-item.md").write_text(_FULLY_SHIPPED, encoding="utf-8")
    (backlog / "partial-item.md").write_text(_PARTIAL, encoding="utf-8")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "ship.py").write_text("def shipped() -> None:\n    pass\n", encoding="utf-8")
    (pkg / "keep.py").write_text("def kept() -> None:\n    pass\n", encoding="utf-8")
    registry = build_registry(
        source_root=tmp_path,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=tmp_path / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs,
        cli_anchors=frozenset(),
    )
    return backlog, specs / "_archive", registry


def _doctor(tmp_path: Path) -> list:
    specs = tmp_path / "specs"
    return run_backlog_doctor(
        specs_dir=specs,
        source_root=tmp_path,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=tmp_path / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        archive_root=specs / "_archive",
        cli_anchors=frozenset(),
    )


def test_loop_closes_zero_bl_stale_after_writer_and_removal(tmp_path: Path) -> None:
    backlog, archive_root, registry = _plant(tmp_path)

    # release-definition: write the ledger keyed on the VERIFIED shipped anchor set.
    # The release shipped only the `ship` anchor: done-item is FULLY consumed (recorded);
    # partial-item ships only one of its two intents → NOT recorded (it survives, residual).
    ledger = consume_at_release_definition(
        backlog_dir=backlog,
        archive_root=archive_root,
        release_id="v0.1.26",
        shipped_anchors={_REF_SHIP},
        registry=registry,
    )
    assert ledger.exists()

    # closure: apply residual-aware removal.
    result = remove_at_closure(
        backlog_dir=backlog,
        archive_root=archive_root,
        release_id="v0.1.26",
        registry=registry,
    )
    by_slug = {a.slug: a.action for a in result.actions}
    assert by_slug["done-item"] is RemovalAction.ARCHIVED_AND_REMOVED
    assert by_slug["partial-item"] is RemovalAction.REWRITTEN

    # The fully-shipped item is gone from the live SET; the archive copy is the survivor.
    assert not (backlog / "done-item.md").exists()
    assert (archive_root / "v0.1.26" / "consumed-backlog" / "done-item.md").exists()
    # The partial item survives, rewritten to its residual (the unshipped intent).
    assert (backlog / "partial-item.md").exists()

    # The loop closes: doctor reports ZERO BL-STALE over the post-removal tree.
    findings = _doctor(tmp_path)
    stale = [f for f in findings if f.code is BacklogDoctorCode.BL_STALE]
    assert stale == [], [f.to_dict() for f in stale]


def test_retained_consumed_slug_flags_bl_stale(tmp_path: Path) -> None:
    backlog, archive_root, registry = _plant(tmp_path)

    consume_at_release_definition(
        backlog_dir=backlog,
        archive_root=archive_root,
        release_id="v0.1.26",
        shipped_anchors={_REF_SHIP},
        registry=registry,
    )
    # Deliberately DO NOT run removal — the consumed slug is artificially left behind.
    assert (backlog / "done-item.md").exists()

    findings = _doctor(tmp_path)
    stale = [f for f in findings if f.code is BacklogDoctorCode.BL_STALE]
    assert any(f.slug == "done-item" for f in stale), [f.to_dict() for f in findings]
