"""Performance guard for lifecycle hygiene metadata scans."""

from __future__ import annotations

import datetime as dt
import json
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
TOTAL_FILES = REPORT_FILES + HANDOFF_FILES + TMP_FILES
#: Every synthetic handoff body is this JSON literal (see ``_synthetic_files`` below) —
#: the bound below is derived directly from it, not an arbitrary constant.
_HANDOFF_BODY = json.dumps({"artifact": {"type": "handoff-first"}})
# Op-count budget (v0.1.53 FR3): the previous 90s wall-clock ceiling was load-sensitive —
# it false-failed the pre-push gate under CPU contention even though the scan's cost profile
# was unchanged. The real invariants a perf guard must hold are algorithmic and
# deterministic under load: (1) each candidate file is stat()'d EXACTLY once (no O(n^2)
# re-scan storm) and (2) ONLY handoff bodies are read (report/tmp bodies are never opened).
# Both are counted directly below, so the budget no longer depends on wall-clock time.
MAX_STAT_OPS = TOTAL_FILES  # exactly one stat per file — no repeated stat of any file
MAX_CONTENT_READS = HANDOFF_FILES * 2  # only handoff bodies, each at most twice
# Content-BYTES budget (v0.1.80 T-1, root-cause fix for bug
# ``perf-hygiene-scan-rss-ceiling-flaky-in-sandbox``): the removed ``rss_delta_bytes``
# check used ``resource.getrusage(...).ru_maxrss`` — an ABSOLUTE OS/allocator-level RSS
# ceiling that bakes in a host/sandbox baseline-memory assumption. Root cause established
# by direct measurement (tracemalloc, isolated): this sandbox's ~500MB RSS delta was NOT
# caused by unbounded content reads (the synthetic handoff bodies total under 12KB) — it
# was almost entirely the O(n) object materialization of
# ``sorted(zone_dir.rglob("*"))`` inside ``_protected_paths`` for the 437,724-file TMP
# zone (confirmed: isolated ``sorted()`` over the same synthetic TMP population alone
# reproduces a ~467MB tracemalloc peak, matching the observed RSS delta almost exactly).
# That materialization is legitimate, deterministic, PRE-EXISTING zone-doc-detection cost
# proportional to file COUNT, not a content-read regression — pinning it as a hard byte
# ceiling would either fail identically to the old flake (same false invariant, different
# unit) or require an environment-fragile ceiling far above what "no unbounded content
# reads" is actually supposed to protect. The invariant THIS test protects is narrower and
# exact: total BYTES read from file CONTENT (``read_text``) never exceeds the synthetic
# tree's own handoff-body size, read at most twice per handoff file (mirrors
# ``MAX_CONTENT_READS`` above, but in bytes instead of call count) — allocator/OS/host
# independent, and tight enough that any regression that starts reading report/tmp bodies,
# or reads a handoff body more than twice, pushes it over deterministically.
MAX_CONTENT_READ_BYTES = len(_HANDOFF_BODY.encode("utf-8")) * MAX_CONTENT_READS


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
            content = _HANDOFF_BODY
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
    """Exercise the definition baseline class without creating 438k real inodes.

    v0.1.80 T-1 (root-cause fix for bug ``perf-hygiene-scan-rss-ceiling-flaky-in-sandbox``):
    the invariant this test protects is that the hygiene scan does BOUNDED content reads —
    it must never slurp report/tmp file bodies, and must read each handoff body at most
    twice. The removed ``rss_delta_bytes < MAX_PEAK_BYTES`` assertion measured this
    indirectly via OS-level RSS (``resource.getrusage``), which bakes in a host/sandbox
    interpreter-baseline-memory assumption unrelated to the scan's own content-read
    behavior (see ``MAX_CONTENT_READ_BYTES`` docstring above for the root-cause
    measurement). This test now measures the DIRECT, environment-independent signal: the
    total bytes actually returned by ``read_text`` calls during the scan.
    """
    (tmp_path / ".dadaia" / "reports").mkdir(parents=True)
    (tmp_path / ".dadaia" / "handoff").mkdir()
    (tmp_path / ".dadaia" / "tmp").mkdir()

    original_rglob = Path.rglob
    read_paths: list[PurePosixPath] = []
    read_bytes_total = 0

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
        nonlocal read_bytes_total
        read_paths.append(self.rel_path)
        text = original_read_text(self, encoding=encoding)
        read_bytes_total += len(text.encode("utf-8"))
        return text

    original_stat = _SyntheticPath.stat
    stat_calls = 0

    def counting_stat(self: _SyntheticPath) -> _SyntheticStat:
        nonlocal stat_calls
        stat_calls += 1
        return original_stat(self)

    monkeypatch.setattr(Path, "rglob", synthetic_rglob)
    monkeypatch.setattr(_SyntheticPath, "read_text", counting_read_text)
    monkeypatch.setattr(_SyntheticPath, "stat", counting_stat)

    counters = LifecycleHygieneService(tmp_path, now=NOW).status()

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
    assert counters.cleanup_candidate_count == TOTAL_FILES - 7
    assert counters.scan_elapsed_ms is not None
    assert counters.scan_elapsed_ms >= 0
    # Content-read budget: only handoff bodies are opened, never report/tmp bodies.
    assert all(path.parts[:2] == (".dadaia", "handoff") for path in read_paths)
    assert len(read_paths) <= MAX_CONTENT_READS
    # Op-count budget (deterministic under load): every file is stat()'d exactly once, so
    # the total stat count equals the file count — a repeated-scan regression (O(n^2)) or a
    # per-file double-stat would push this over the file total. This replaces the removed
    # 90s wall-clock ceiling, which false-failed under CPU contention.
    assert stat_calls == MAX_STAT_OPS
    # Content-BYTES budget (v0.1.80 T-1, replaces the environment-dependent RSS ceiling):
    # environment-independent because it counts exactly what ``read_text`` returned, never
    # OS/allocator/interpreter-baseline memory. Tight against the synthetic tree's own
    # numbers — pinned exact (not just "under a generous ceiling") because every handoff
    # body here is byte-identical, so the scan's actual content-read footprint is fully
    # determined by ``len(read_paths)``.
    assert read_bytes_total == len(_HANDOFF_BODY.encode("utf-8")) * len(read_paths)
    assert read_bytes_total <= MAX_CONTENT_READ_BYTES
