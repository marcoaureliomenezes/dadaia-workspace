"""FR8's one resolver seam (AS-1) proven against real git history — A8.2's own
acceptance: "the value ... equals what the resolver derives from git" on >= 20
historical records.

Intent: CONTRACT — 0.5.0 A8.2. Size: SMALL (directory-tiered ``contract``).

Every case below is a real, live record from ``specs/bugs/BUGS.jsonl`` that already
carries a stored ``resolved_commit`` (T-050-10's migration wrote it). Each is forced
through ``BugService.resolved_commit``'s DERIVED branch — the exact same seam
``dadaia_workspace/features/bugs/service.py`` exposes, on a copy with
``resolved_commit`` cleared (``dataclasses.replace``) — and the result is asserted
equal to the value already on disk. A mismatch here is exactly the drift FR14's
pillar-1 audit exists to catch (SPEC FR8: "Pillar 1 reports a stored value that
disagrees with the derivation as a finding") — this test catches it earlier, on a real
sample, at implementation time.

**Cost note, and why the walk is shared.** ``GitHistoryReader.log_added_lines`` walks
every commit that ever touched ``specs/bugs/`` (~300 at this fold) with ~2 extra git
subprocess calls each — a few seconds, genuinely NOT free, and NOT something to pay
per parametrized case. The module-scoped ``_cached_history_reader`` fixture below runs
the REAL adapter (``container.build_git_history_reader()``) exactly ONCE per test
session and caches its result; every parametrized case reuses that cached commit list,
so the marginal cost per case is one in-memory ``derive_commit_provenance`` pass, not a
new git invocation.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.models.bugs import BugRecord
from dadaia_workspace.core.protocols.git_history_reader import GitHistoryReader, HistoryCommit
from dadaia_workspace.features.bugs.service import BugService

pytestmark = [pytest.mark.slow]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPECS_DIR = _REPO_ROOT / "specs"
_LEDGER_PATH = _SPECS_DIR / "bugs" / "BUGS.jsonl"

#: The acceptance floor (A8.2: ">= 20 historical records").
_MINIMUM_SAMPLE = 20


def _resolved_sample(minimum: int) -> list[BugRecord]:
    """A deterministic sample of >= *minimum* live records already carrying a stored
    ``resolved_commit``, spread across every resolution-granularity bucket present
    (``exact``/``release-squash``/``ledger-only``) so the sample exercises more than
    one commit shape — never just hardcoded ids, so the sample tracks the live ledger."""
    by_granularity: dict[str, list[BugRecord]] = {}
    with _LEDGER_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            record = BugRecord.from_dict(json.loads(stripped))
            if record.resolved_commit is None:
                continue
            bucket = record.resolution_granularity or "unknown"
            by_granularity.setdefault(bucket, []).append(record)

    if not by_granularity:
        return []

    per_bucket = max(1, minimum // len(by_granularity))
    sample: list[BugRecord] = []
    seen_ids: set[str] = set()
    for bucket_records in by_granularity.values():
        for record in sorted(bucket_records, key=lambda r: r.id)[:per_bucket]:
            sample.append(record)
            seen_ids.add(record.id)

    if len(sample) < minimum:
        largest = max(by_granularity.values(), key=len)
        for record in sorted(largest, key=lambda r: r.id):
            if record.id in seen_ids:
                continue
            sample.append(record)
            seen_ids.add(record.id)
            if len(sample) >= minimum:
                break

    return sample


_SAMPLE: list[BugRecord] = _resolved_sample(_MINIMUM_SAMPLE) if _LEDGER_PATH.is_file() else []


class _CachedHistoryReader:
    """Wraps the REAL ``GitHistoryReader`` adapter but performs the git walk exactly
    once and replays the cached result for every subsequent call — the module
    fixture's cost-sharing device this file's docstring promises."""

    def __init__(self, real_reader: GitHistoryReader) -> None:
        self._real_reader = real_reader
        self._cache: dict[tuple[Path, str], list[HistoryCommit]] = {}

    def log_added_lines(self, repo: Path, pathspec: str) -> Iterable[HistoryCommit]:
        key = (repo, pathspec)
        if key not in self._cache:
            self._cache[key] = list(self._real_reader.log_added_lines(repo, pathspec))
        return self._cache[key]


@pytest.fixture(scope="module")
def _service_with_cached_history() -> BugService:
    cached_reader = _CachedHistoryReader(container.build_git_history_reader())
    store = container.build_bug_record_store(_SPECS_DIR)
    return BugService(store, history_reader=cached_reader, repo_root=_REPO_ROOT)


@pytest.mark.skipif(not _LEDGER_PATH.is_file(), reason="specs/bugs/BUGS.jsonl not present")
@pytest.mark.skipif(
    len(_SAMPLE) < _MINIMUM_SAMPLE,
    reason=f"live ledger yields only {len(_SAMPLE)} resolved records, need >= {_MINIMUM_SAMPLE}",
)
@pytest.mark.parametrize("record", _SAMPLE, ids=[record.id for record in _SAMPLE])
def test_stored_equals_derived_resolved_commit(
    record: BugRecord, _service_with_cached_history: BugService
) -> None:
    forced = replace(record, resolved_commit=None)

    derived = _service_with_cached_history.resolved_commit(forced)

    assert derived == record.resolved_commit, (
        f"{record.id}: stored {record.resolved_commit!r} != derived {derived!r} "
        f"(resolution_granularity={record.resolution_granularity!r})"
    )


def test_sample_meets_the_a8_2_floor() -> None:
    """Guards the fixture itself: a shrinking sample (e.g. a future ledger rewrite)
    fails loud here instead of silently skipping every parametrized case above."""
    assert len(_SAMPLE) >= _MINIMUM_SAMPLE, (
        f"A8.2 requires >= {_MINIMUM_SAMPLE} historical resolved records to sample; "
        f"found {len(_SAMPLE)}"
    )
