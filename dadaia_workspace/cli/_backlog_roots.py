"""Backlog root resolution — a ``cli/`` composition helper.

Shared by every verb that builds the backlog subject registry: ``dadaia doctor``'s
`ledgers` section and ``dadaia backlog subjects``. It lived inside
``cli/commands/newartifacts.py`` while ``backlog doctor`` was a command of its own;
0.4.7 FR5 deleted that command and the one doctor needs the same resolution, so the
helper moved here rather than being imported across verb modules or written twice.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["resolve_backlog_roots"]


def resolve_backlog_roots(
    specs_dir: Path, source_root: str | None, alias_map: str | None
) -> tuple[Path, Path, Path]:
    """Resolve the injected roots the registry/doctor need (SPEC §3.8 #6 — never cwd).

    Returns ``(source_root, catalog_path, alias_map_path)``. ``source_root`` defaults to
    the repo root that owns ``specs_dir`` (``specs_dir.parent``) so code anchors are
    derived REPO-ROOT-relative (e.g. ``dadaia_workspace/core/...#Sym``) — matching the way
    committed ``code`` refs are authored. The alias map defaults to the workspace-level
    ``.dadaia/states/backlog_subject_aliases.txt`` resolved up from ``specs_dir``.

    No longer returns an ``archive_root`` (v0.5.0 T-050-13A): the doctor's BL-STALE
    condition (a) reads the relocated ``consumed_backlog_histo.jsonl`` store through a
    ``JsonlRecordStore`` this module builds directly (ADR-0001: single consumer, no
    container seam), wired at the call site below — the pre-relocation directory-glob
    root has no reader left to inject it into.
    """
    src = Path(source_root).resolve() if source_root else specs_dir.parent.resolve()
    catalog_path = specs_dir / "memory" / "product" / "catalog.json"
    alias_map_path = Path(alias_map).resolve() if alias_map else _default_alias_map_path(specs_dir)
    return src, catalog_path, alias_map_path


def _default_alias_map_path(specs_dir: Path) -> Path:
    """Walk up from ``specs_dir`` to the workspace root and target the alias-map file."""
    here = specs_dir.resolve()
    for parent in (here, *here.parents):
        if (parent / ".dadaia").is_dir():
            return parent / ".dadaia" / "states" / "backlog_subject_aliases.txt"
    # No workspace found above specs_dir: fall back to a sibling of specs_dir (still injected).
    return specs_dir.parent / ".dadaia" / "states" / "backlog_subject_aliases.txt"
