"""Performance guard for lifecycle hygiene metadata scans."""

from __future__ import annotations

import datetime as dt
import json
import resource
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import pytest

from dadaia_workspace.core.models.hygiene import HygieneZone
from dadaia_workspace.features.lifecycle.hygiene import LifecycleHygieneService

NOW = dt.datetime(2026, 6, 18, 12, 0, tzinfo=dt.UTC)
REPORT_FILES = 122
HANDOFF_FILES = 295
TMP_FILES = 437_724
MAX_SCAN_SECONDS = 90.0
MAX_PEAK_BYTES = 96 * 1024 * 1024


@dataclass(frozen=True)
class _SyntheticStat:
    st_mtime: float


@dataclass(frozen=True)
class _SyntheticPath:
    workspace_root: Path
    rel_path: PurePosixPath
    mtime: float
    content: str = ""

    @property
    def name(self) -> str:
        return self.rel_path.name

    def __lt__(self, other: _SyntheticPath) -> bool:
        return self.rel_path < other.rel_path

    def is_file(self) -> bool:
        return True

    def exists(self) -> bool:
        return True

    def stat(self) -> _SyntheticStat:
        return _SyntheticStat(st_mtime=self.mtime)

    def resolve(self) -> _SyntheticPath:
        return self

    def relative_to(self, root: Path) -> PurePosixPath:
        try:
            root_rel = PurePosixPath(root.relative_to(self.workspace_root).as_posix())
        except ValueError as exc:
            raise ValueError from exc
        if root_rel == PurePosixPath("."):
            return self.rel_path
        if self.rel_path.parts[: len(root_rel.parts)] != root_rel.parts:
            raise ValueError
        return PurePosixPath(*self.rel_path.parts[len(root_rel.parts) :])

    def as_posix(self) -> str:
        return self.rel_path.as_posix()

    def read_text(self, encoding: str | None = None) -> str:
        _ = encoding
        return self.content


def _mtime(age: dt.timedelta) -> float:
    return (NOW - age).timestamp()


def _synthetic_files(
    workspace_root: Path,
    zone: HygieneZone,
    *,
    count: int,
    fresh: int,
) -> Iterator[_SyntheticPath]:
    for index in range(count):
        age = dt.timedelta(hours=1 if index >= count - fresh else 72)
        if zone is HygieneZone.REPORTS:
            rel = PurePosixPath(f".dadaia/reports/ctx/agent/report-{index}.html")
            content = ""
        elif zone is HygieneZone.HANDOFF:
            rel = PurePosixPath(f".dadaia/handoff/ctx/handoff-{index}.handoff.json")
            content = json.dumps({"artifact": {"type": "handoff-first"}})
        else:
            rel = PurePosixPath(f".dadaia/tmp/agent/{index // 1000:04d}/tmp-{index}.txt")
            content = ""
        yield _SyntheticPath(
            workspace_root=workspace_root,
            rel_path=rel,
            mtime=_mtime(age),
            content=content,
        )


@pytest.mark.slow
def test_hygiene_status_scans_synthetic_baseline_tree_with_bounded_content_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the definition baseline class without creating 438k real inodes."""
    (tmp_path / ".dadaia" / "reports").mkdir(parents=True)
    (tmp_path / ".dadaia" / "handoff").mkdir()
    (tmp_path / ".dadaia" / "tmp").mkdir()

    original_rglob = Path.rglob
    read_paths: list[PurePosixPath] = []

    def synthetic_rglob(self: Path, pattern: str) -> Iterator[_SyntheticPath]:
        _ = pattern
        if self == tmp_path / ".dadaia" / "reports":
            return _synthetic_files(
                tmp_path,
                HygieneZone.REPORTS,
                count=REPORT_FILES,
                fresh=1,
            )
        if self == tmp_path / ".dadaia" / "handoff":
            return _synthetic_files(
                tmp_path,
                HygieneZone.HANDOFF,
                count=HANDOFF_FILES,
                fresh=1,
            )
        if self == tmp_path / ".dadaia" / "tmp":
            return _synthetic_files(
                tmp_path,
                HygieneZone.TMP,
                count=TMP_FILES,
                fresh=5,
            )
        return original_rglob(self, pattern)  # type: ignore[return-value]

    original_read_text = _SyntheticPath.read_text

    def counting_read_text(self: _SyntheticPath, encoding: str | None = None) -> str:
        read_paths.append(self.rel_path)
        return original_read_text(self, encoding=encoding)

    monkeypatch.setattr(Path, "rglob", synthetic_rglob)
    monkeypatch.setattr(_SyntheticPath, "read_text", counting_read_text)

    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    start = time.perf_counter()
    counters = LifecycleHygieneService(tmp_path, now=NOW).status()
    elapsed = time.perf_counter() - start
    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_delta_bytes = max(rss_after - rss_before, 0) * 1024

    assert counters.zone_totals == {
        HygieneZone.REPORTS: REPORT_FILES,
        HygieneZone.HANDOFF: HANDOFF_FILES,
        HygieneZone.TMP: TMP_FILES,
    }
    assert counters.expired_totals == {
        HygieneZone.REPORTS: REPORT_FILES - 1,
        HygieneZone.HANDOFF: HANDOFF_FILES - 1,
        HygieneZone.TMP: TMP_FILES - 5,
    }
    assert counters.cleanup_candidate_count == REPORT_FILES + HANDOFF_FILES + TMP_FILES - 7
    assert counters.scan_elapsed_ms is not None
    assert counters.scan_elapsed_ms >= 0
    assert all(path.parts[:2] == (".dadaia", "handoff") for path in read_paths)
    assert len(read_paths) <= HANDOFF_FILES * 2
    assert elapsed < MAX_SCAN_SECONDS
    assert rss_delta_bytes < MAX_PEAK_BYTES
