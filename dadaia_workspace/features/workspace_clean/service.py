"""WorkspaceCleanService — reclaim stale files from ephemeral .dadaia/ zones.

Implements ``dadaia clean`` (T-016-Z03):

  - Dry-run by default: lists candidates without deleting.
  - Declarative per-zone TTL for .dadaia/tmp/, .dadaia/reports/, .dadaia/dev-report/.
  - Safe-delete: never touches files protected by root_exceptions.txt; never
    deletes anything outside .dadaia/.
  - Logs every reclaim in the returned CleanResult.

Zones and default TTLs
----------------------
  tmp/          2 days — highly ephemeral agent scratch files
  reports/      7 days — human-readable HTML reports persist longer
  dev-report/   3 days — dev/debug reports kept briefly

The TTLs are applied per-file using the file's mtime.  Empty directories
created during scanning are left in place (only files are reclaimed here; the
caller may invoke a directory-pruning pass separately if needed).
"""

from __future__ import annotations

import datetime as dt
import fnmatch
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default per-zone TTLs
# ---------------------------------------------------------------------------

_ZONE_TTLS: dict[str, dt.timedelta] = {
    "tmp": dt.timedelta(days=2),
    "reports": dt.timedelta(days=7),
    "dev-report": dt.timedelta(days=3),
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CleanCandidate:
    """A file eligible for deletion."""

    path: Path
    zone: str
    reason: str


@dataclass
class CleanResult:
    """Outcome of a clean run."""

    dry_run: bool
    candidates: list[CleanCandidate] = field(default_factory=list)
    deleted: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class WorkspaceCleanService:
    """Scan ephemeral .dadaia/ zones and reclaim stale files.

    Parameters
    ----------
    workspace_root:
        Absolute path to the workspace root (parent of ``.dadaia/``).
    now:
        Injectable clock seam for tests.  Defaults to ``datetime.now(UTC)``.
    zone_ttls:
        Override per-zone TTLs (zone name → timedelta).  Defaults to
        :data:`_ZONE_TTLS` when ``None``.
    """

    def __init__(
        self,
        workspace_root: Path,
        *,
        now: dt.datetime | None = None,
        zone_ttls: dict[str, dt.timedelta] | None = None,
    ) -> None:
        self._root = workspace_root.resolve()
        self._dadaia = self._root / ".dadaia"
        self._now = now
        self._ttls = zone_ttls if zone_ttls is not None else dict(_ZONE_TTLS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clean(self, *, dry_run: bool = True) -> CleanResult:
        """Scan zones and optionally delete stale files.

        Parameters
        ----------
        dry_run:
            When ``True`` (the default) return candidates without touching
            the filesystem.  When ``False``, delete every non-protected
            stale file and log the reclaim.

        Returns
        -------
        CleanResult
            Candidates found (always populated) and deleted paths (populated
            only when *dry_run* is ``False``).
        """
        exc_globs = self._operator_exception_globs()
        now = self._clock()
        result = CleanResult(dry_run=dry_run)

        for zone, ttl in self._ttls.items():
            zone_dir = self._dadaia / zone
            if not zone_dir.is_dir():
                continue
            cutoff = now - ttl
            for file in sorted(zone_dir.rglob("*")):
                if not file.is_file():
                    continue
                # Boundary guard — must be under .dadaia/
                if not self._is_under_dadaia(file):
                    continue
                # Operator protection
                if self._is_protected(file, exc_globs):
                    continue
                # TTL check (use mtime)
                mtime = dt.datetime.fromtimestamp(file.stat().st_mtime, tz=dt.UTC)
                if mtime >= cutoff:
                    continue
                candidate = CleanCandidate(
                    path=file,
                    zone=zone,
                    reason=f"older than {int(ttl.total_seconds() // 86400)} day(s) TTL",
                )
                result.candidates.append(candidate)
                if not dry_run:
                    self._delete(file, result)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _delete(self, path: Path, result: CleanResult) -> None:
        """Delete *path* and record the reclaim in *result*."""
        try:
            path.unlink(missing_ok=True)
            result.deleted.append(path)
            logger.info("dadaia clean: reclaimed %s", path)
        except OSError as exc:
            logger.warning("dadaia clean: failed to delete %s: %s", path, exc)

    def _is_under_dadaia(self, path: Path) -> bool:
        """Return True iff *path* is strictly under self._dadaia."""
        try:
            path.resolve().relative_to(self._dadaia)
        except ValueError:
            return False
        return True

    def _is_protected(self, path: Path, exc_globs: list[str]) -> bool:
        """Return True iff *path*'s name matches an operator exception glob."""
        return any(fnmatch.fnmatch(path.name, g) for g in exc_globs)

    def _operator_exception_globs(self) -> list[str]:
        """Read operator exception globs from .dadaia/states/root_exceptions.txt."""
        exc_file = self._dadaia / "states" / "root_exceptions.txt"
        if not exc_file.exists():
            return []
        globs: list[str] = []
        for line in exc_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                globs.append(stripped)
        return globs

    def _clock(self) -> dt.datetime:
        return (self._now or dt.datetime.now(tz=dt.UTC)).astimezone(dt.UTC)
