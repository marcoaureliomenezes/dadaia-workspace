"""Lifecycle hygiene status service driven by the canonical SlopPolicy."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path, PurePosixPath, PureWindowsPath

from dadaia_workspace.core.models.hygiene import HygieneCounters, HygieneZone, SlopPolicy


class LifecycleHygieneService:
    """Compute workspace hygiene counters without mutating the filesystem."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        policy: SlopPolicy | None = None,
        now: dt.datetime | None = None,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._dadaia_root = self._workspace_root / ".dadaia"
        self._policy = policy or SlopPolicy()
        self._now = now

    @property
    def policy(self) -> SlopPolicy:
        return self._policy

    def status(self) -> HygieneCounters:
        """Return metadata-only counters for canonical runtime zones."""
        started = self._clock()
        zone_totals: dict[HygieneZone, int] = {}
        expired_totals: dict[HygieneZone, int] = {}

        for zone in self._policy.safe_zones:
            total, expired = self._zone_counts(zone)
            zone_totals[zone] = total
            expired_totals[zone] = expired

        orphan_handoffs, malformed_handoffs = self._handoff_semantic_counts()
        cleanup_candidates = sum(expired_totals.values())
        elapsed = int((self._clock() - started).total_seconds() * 1000)
        return HygieneCounters(
            zone_totals=zone_totals,
            expired_totals=expired_totals,
            orphan_handoff_count=orphan_handoffs,
            malformed_handoff_count=malformed_handoffs,
            unknown_top_level_dirs=self._unknown_top_level_dirs(),
            cleanup_candidate_count=cleanup_candidates,
            scan_elapsed_ms=elapsed,
        )

    def _zone_counts(self, zone: HygieneZone) -> tuple[int, int]:
        zone_dir = self._dadaia_root / zone.value
        if not zone_dir.is_dir():
            return 0, 0
        cutoff = self._clock() - dt.timedelta(seconds=self._policy.ttl_for(zone))
        total = 0
        expired = 0
        for path in zone_dir.rglob("*"):
            if not path.is_file() or not self._is_under(path, zone_dir):
                continue
            total += 1
            mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.UTC)
            if mtime < cutoff:
                expired += 1
        return total, expired

    def _unknown_top_level_dirs(self) -> tuple[str, ...]:
        if not self._dadaia_root.is_dir():
            return ()
        durable = set(self._policy.durable_top_level_dirs)
        return tuple(
            sorted(
                child.name
                for child in self._dadaia_root.iterdir()
                if child.is_dir() and child.name not in durable
            )
        )

    def _handoff_semantic_counts(self) -> tuple[int, int]:
        handoff_dir = self._dadaia_root / HygieneZone.HANDOFF.value
        if not handoff_dir.is_dir():
            return 0, 0
        orphan = 0
        malformed = 0
        for path in handoff_dir.rglob("*.handoff.json"):
            if not path.is_file() or not self._is_under(path, handoff_dir):
                continue
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                malformed += 1
                continue
            if not isinstance(doc, dict):
                malformed += 1
                continue
            artifact = doc.get("artifact", {})
            if not isinstance(artifact, dict):
                malformed += 1
                continue
            artifact_path = artifact.get("path")
            if artifact_path is None:
                continue
            if not isinstance(artifact_path, str):
                malformed += 1
                continue
            report_path = self._valid_report_artifact_path(artifact_path)
            if report_path is None:
                malformed += 1
                continue
            if not report_path.is_file():
                orphan += 1
        return orphan, malformed

    def _valid_report_artifact_path(self, artifact_path: str) -> Path | None:
        if (
            PurePosixPath(artifact_path).is_absolute()
            or PureWindowsPath(artifact_path).is_absolute()
        ):
            return None
        raw = Path(artifact_path)
        if ".." in raw.parts or raw.parts[:2] != (".dadaia", "reports"):
            return None
        resolved = (self._workspace_root / raw).resolve()
        reports_root = (self._dadaia_root / "reports").resolve()
        try:
            resolved.relative_to(reports_root)
        except ValueError:
            return None
        return resolved

    @staticmethod
    def _is_under(path: Path, root: Path) -> bool:
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            return False
        return True

    def _clock(self) -> dt.datetime:
        return (self._now or dt.datetime.now(tz=dt.UTC)).astimezone(dt.UTC)
