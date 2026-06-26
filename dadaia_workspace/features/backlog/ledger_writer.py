"""``consumed_backlog`` ledger WRITER — the R2 producer of the R1 reader shape (SPEC §3.6).

R1 shipped ``ledger.read_consumed`` (BL-STALE feed) + ``LEDGER_FILENAME`` but nothing wrote
the ledger. This module is the writer: it emits
``specs/_archive/<release-id>/consumed_backlog.json`` in the **exact** R1 reader shape,
keyed on the **verified shipped subject-anchor set** actually consumed by the release — not
the slug string alone. The ledger this writer produces is what BL-STALE keys on to reject a
consumed slug that survives in ``specs/backlog/`` (closing the R1 loop).

Constraints (SPEC §3.8):

* ``archive_root`` is **injected**, never ``os.getcwd()``.
* Reuse ``LEDGER_FILENAME`` from R1 ``ledger.py`` — no second schema.
* Anchors are **module-relative** ``path#symbol`` or a non-path id (``INV-*``, a slug); an
  operator-local absolute / home / traversal / drive-prefixed path anchor is rejected at
  write time so no operator-local path can land in a committed safety record (privacy).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.features.backlog.ledger import LEDGER_FILENAME

__all__ = ["ConsumedEntry", "write_consumed"]

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True)
class ConsumedEntry:
    """One consumed backlog item: its slug + the verified shipped anchor set.

    ``shipped_anchors`` is the set of canonical anchor ids the release actually shipped for
    this item — the basis for residual-aware removal and BL-STALE, never the slug alone.
    """

    slug: str
    shipped_anchors: frozenset[str]


def _validate_anchor(anchor: str) -> None:
    """Reject an operator-local path anchor (privacy, SPEC §3.8); allow non-path ids.

    A path-like anchor (one containing ``#`` with a path segment, or any ``/``-bearing token)
    must be module-relative. A bare id (``INV-foo``, a catalog slug, a CLI id like
    ``backlog define``) carries no path and is allowed verbatim.
    """
    path_part = anchor.split("#", 1)[0]
    if "/" not in path_part and not _WINDOWS_DRIVE_RE.match(path_part):
        return  # bare id (invariant / slug / cli surface) — no path to leak.
    if path_part.startswith("/"):
        raise ValueError(f"shipped anchor must be module-relative, not absolute: {anchor!r}")
    if path_part.startswith("~"):
        raise ValueError(f"shipped anchor must be module-relative, not a home path: {anchor!r}")
    if ".." in path_part.split("/"):
        raise ValueError(
            f"shipped anchor must be module-relative, parent traversal forbidden: {anchor!r}"
        )
    if _WINDOWS_DRIVE_RE.match(path_part):
        raise ValueError(f"shipped anchor must be module-relative, not a drive path: {anchor!r}")


def write_consumed(
    *,
    archive_root: Path,
    release_id: str,
    consumed: Sequence[ConsumedEntry],
) -> Path:
    """Write ``<archive_root>/<release_id>/consumed_backlog.json`` (R1 reader shape).

    Returns the written ledger path. The archive release directory is created if absent.
    Entries are serialized in input order; each entry's anchors are sorted for deterministic
    output. Every anchor is validated module-relative before any byte is written (fail-loud
    on an operator-local path — privacy, SPEC §3.8).
    """
    for entry in consumed:
        for anchor in entry.shipped_anchors:
            _validate_anchor(anchor)

    payload = {
        "release": release_id,
        "consumed": [
            {"slug": entry.slug, "shipped_anchors": sorted(entry.shipped_anchors)}
            for entry in consumed
        ],
    }
    release_dir = archive_root / release_id
    release_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = release_dir / LEDGER_FILENAME
    ledger_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return ledger_path
