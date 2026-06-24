"""Directory-aware anti-slop metric (WS-6, D3/D4).

The pre-existing hygiene metric only matches ``path.is_file()``; a multi-GB directory
tree (a stray venv, a cache) is invisible to it. ``slop_scan`` closes that gap: it walks
the canonical swept ``.dadaia/`` zones and classifies each **top-level entry** of every
swept zone subtree — a directory tree counts as ONE entry with its **recursive** byte size.

This is the **metric**, not the sweep. It is pure: an injected clock, ``pathlib`` walking
only, and **no** filesystem mutation, no deletion. The canonical root manifest derives from
``hooks/root_whitelist._WHITELIST`` (D4) so the metric reads the same source the gate
enforces; a drift-guard test asserts the two never diverge.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.hygiene import HygieneZone, SlopPolicy
from dadaia_workspace.hooks import root_whitelist

#: Swept ``.dadaia/`` zones whose top-level entries the metric measures. The TTL-bearing
#: zones come from ``SlopPolicy.safe_zones`` (reports/handoff/tmp). ``runs`` is an additional
#: ephemeral zone with no SlopPolicy TTL of its own — it is swept against the tmp TTL.
_RUNS_ZONE = "runs"


class SlopEntryKind(StrEnum):
    """Classification of a swept top-level entry."""

    #: A recognised zone member within its TTL (not yet reclaimable).
    CANONICAL = "canonical"
    #: Past its zone TTL — reclaimable by a future sweep.
    STALE = "stale"
    #: Not a recognised member of any swept zone (defensive; reclaimable).
    NON_CANONICAL = "non_canonical"


@dataclass(frozen=True)
class SlopEntry:
    """One top-level entry of a swept zone, directory-aware.

    For a directory, ``size_bytes`` is the **recursive** sum of contained file sizes —
    the whole point of the directory-aware metric.
    """

    path: str
    kind: SlopEntryKind
    size_bytes: int
    is_dir: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind.value,
            "size_bytes": self.size_bytes,
            "is_dir": self.is_dir,
        }


@dataclass(frozen=True)
class SlopReport:
    """Aggregate of a slop scan.

    ``reclaimable_bytes`` is the total recursive byte size of every entry that is NOT
    canonical-within-TTL — i.e. stale (past-TTL) plus non-canonical entries. It is the
    headline metric the directory-blind sweep could not see.
    """

    entries: tuple[SlopEntry, ...]
    scanned_at: str

    @property
    def total_entries(self) -> int:
        return len(self.entries)

    @property
    def stale_count(self) -> int:
        return sum(1 for entry in self.entries if entry.kind is SlopEntryKind.STALE)

    @property
    def non_canonical_count(self) -> int:
        return sum(1 for entry in self.entries if entry.kind is SlopEntryKind.NON_CANONICAL)

    @property
    def canonical_count(self) -> int:
        return sum(1 for entry in self.entries if entry.kind is SlopEntryKind.CANONICAL)

    @property
    def reclaimable_bytes(self) -> int:
        return sum(
            entry.size_bytes for entry in self.entries if entry.kind is not SlopEntryKind.CANONICAL
        )

    @property
    def total_bytes(self) -> int:
        return sum(entry.size_bytes for entry in self.entries)

    def top_offenders(self, limit: int = 10) -> tuple[SlopEntry, ...]:
        reclaimable = [e for e in self.entries if e.kind is not SlopEntryKind.CANONICAL]
        reclaimable.sort(key=lambda e: e.size_bytes, reverse=True)
        return tuple(reclaimable[:limit])

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned_at": self.scanned_at,
            "total_entries": self.total_entries,
            "canonical_count": self.canonical_count,
            "stale_count": self.stale_count,
            "non_canonical_count": self.non_canonical_count,
            "reclaimable_bytes": self.reclaimable_bytes,
            "total_bytes": self.total_bytes,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def canonical_root_manifest() -> frozenset[str]:
    """Canonical workspace-root entries, derived from the gate's own whitelist (D4).

    The metric MUST read the same manifest the gate enforces; a hand-maintained copy would
    drift. A unit test asserts equality with ``root_whitelist._WHITELIST``.
    """
    return frozenset(root_whitelist._WHITELIST)


def _swept_zones(policy: SlopPolicy) -> tuple[tuple[str, int], ...]:
    """Return ``(zone_dirname, ttl_seconds)`` for every swept ``.dadaia/`` zone."""
    zones: list[tuple[str, int]] = [
        (zone.value, policy.ttl_for(zone)) for zone in policy.safe_zones
    ]
    if _RUNS_ZONE not in {name for name, _ in zones}:
        zones.append((_RUNS_ZONE, policy.ttl_for(HygieneZone.TMP)))
    return tuple(zones)


def _recursive_size(path: Path) -> tuple[int, dt.datetime | None]:
    """Recursive byte size of *path* and the NEWEST contained mtime.

    For a file: its own size and mtime. For a directory: the sum of all contained file
    sizes and the newest mtime among the tree (a fresh file keeps the whole tree fresh).
    """
    if path.is_file():
        stat = path.stat()
        return stat.st_size, dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.UTC)

    total = 0
    newest: dt.datetime | None = None
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        try:
            stat = child.stat()
        except OSError:
            continue
        total += stat.st_size
        mtime = dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.UTC)
        if newest is None or mtime > newest:
            newest = mtime
    return total, newest


def slop_scan(
    workspace_root: Path,
    *,
    now: dt.datetime,
    policy: SlopPolicy,
) -> SlopReport:
    """Directory-aware, read-only slop metric over the canonical swept ``.dadaia/`` zones.

    Each **top-level entry** of every swept zone subtree becomes one ``SlopEntry``. A
    directory tree counts as ONE entry with its recursive byte size and its newest
    contained mtime (a fresh file keeps the tree fresh). Classification:

    - ``STALE`` — past the zone TTL (``policy.ttl_for(zone)``), reclaimable.
    - ``CANONICAL`` — a recognised zone child still within TTL.

    Pure: no filesystem mutation, no deletion. The clock is injected.
    """
    clock = now.astimezone(dt.UTC)
    dadaia_root = workspace_root.resolve() / ".dadaia"
    workspace_resolved = workspace_root.resolve()

    entries: list[SlopEntry] = []
    for zone_name, ttl_seconds in _swept_zones(policy):
        zone_dir = dadaia_root / zone_name
        if not zone_dir.is_dir():
            continue
        cutoff = clock - dt.timedelta(seconds=ttl_seconds)
        for child in sorted(zone_dir.iterdir()):
            _collect_entries(child, cutoff, workspace_resolved, entries)

    return SlopReport(entries=tuple(entries), scanned_at=clock.isoformat())


def _collect_entries(
    node: Path,
    cutoff: dt.datetime,
    workspace_resolved: Path,
    out: list[SlopEntry],
) -> None:
    """Append the reporting unit(s) rooted at *node*.

    Reporting granularity (directory-aware):

    - A **file** is always one entry.
    - A **directory** that directly contains at least one file is the slop unit: it is
      reported as ONE entry with its **recursive** byte size and newest mtime. This is the
      gap the file-only metric missed — a stray venv (files inside) collapses to one entry.
    - A directory of pure scaffolding (only subdirectories, no direct files — e.g. the
      ``tmp/<agent>/`` bucket above the dated leaf) is descended into, never reported
      itself, so the metric lands on the meaningful leaf.
    """
    if node.is_file():
        out.append(_entry_for(node, cutoff, workspace_resolved))
        return
    if not node.is_dir():
        return
    children = sorted(node.iterdir())
    has_direct_file = any(child.is_file() for child in children)
    if has_direct_file or not children:
        out.append(_entry_for(node, cutoff, workspace_resolved))
        return
    for child in children:
        _collect_entries(child, cutoff, workspace_resolved, out)


def _entry_for(node: Path, cutoff: dt.datetime, workspace_resolved: Path) -> SlopEntry:
    size_bytes, newest = _recursive_size(node)
    kind = _classify(newest, cutoff)
    rel = node.resolve().relative_to(workspace_resolved).as_posix()
    return SlopEntry(path=rel, kind=kind, size_bytes=size_bytes, is_dir=node.is_dir())


def _classify(newest: dt.datetime | None, cutoff: dt.datetime) -> SlopEntryKind:
    if newest is None:
        # An empty directory carries no mtime evidence — treat as stale (reclaimable).
        return SlopEntryKind.STALE
    if newest < cutoff:
        return SlopEntryKind.STALE
    return SlopEntryKind.CANONICAL
