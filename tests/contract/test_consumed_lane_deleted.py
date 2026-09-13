"""0.4.7 FR7 contract (T-047-05), bug
``provisional-consumed-histo-records-never-finalized-no-writer-no-check``.

Intent: CONTRACT — 0.4.7 FR7 / T-047-05. A picked backlog item stays ``picked`` in
``active[]`` and exits ONCE, at closure. The provisional ``CONSUMED`` token invented a
second, pick-time exit whose finalizer was never written: 27 records stalled in
``consumed_backlog_histo.jsonl`` forever, and two independent staleness checks
(BL-STALE condition (a), SPEC-DOC-031) were built to police the stall instead of
removing it. This test pins the deletion: no source or test file names the token, the
ledger module, the record class or the consumed histo file ever again.

Size: SMALL (reads the shipped source tree; no subprocess, no fixture, no network).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import dadaia_workspace

pytestmark = pytest.mark.contract

_PKG = Path(dadaia_workspace.__file__).resolve().parent
_TESTS = _PKG.parent / "tests"

#: Every name the deleted pick-time exit lane went by.
_DEAD_NAMES = (
    "CONSUMED",
    "ConsumedBacklogHistoRecord",
    "consumed_backlog_histo",
    "read_consumed",
    "SPEC-DOC-031",
)
_DEAD_RE = re.compile("|".join(re.escape(name) for name in _DEAD_NAMES))

#: Law/skill text under ``public/`` is T-047-12's write set — this contract covers the
#: code and its tests, which T-047-05 owns.
_SCOPES = (_PKG / "core", _PKG / "features", _PKG / "cli", _PKG / "hooks", _TESTS)


def _offenders() -> list[str]:
    hits: list[str] = []
    for scope in _SCOPES:
        for path in scope.rglob("*.py"):
            if "__pycache__" in path.parts or path.name == Path(__file__).name:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _DEAD_RE.search(line):
                    hits.append(
                        f"{path.relative_to(_PKG.parent).as_posix()}:{lineno}: {line.strip()}"
                    )
    return hits


def test_no_source_or_test_names_the_consumed_lane() -> None:
    offenders = _offenders()
    assert not offenders, (
        "the pick-time CONSUMED exit lane is deleted (0.4.7 FR7, T-047-05): a picked "
        "item stays 'picked' in active[] and exits once, at closure. Still named:\n"
        + "\n".join(offenders)
    )


def test_the_consumed_histo_file_and_ledger_module_are_gone() -> None:
    assert not (_PKG / "features" / "backlog" / "ledger.py").exists(), (
        "features/backlog/ledger.py read the consumed lane and had no producer — deleted"
    )
    specs_dir = _PKG.parent / "specs"
    stale = specs_dir / "backlog" / "_archive" / "consumed_backlog_histo.jsonl"
    assert not stale.exists(), f"{stale} holds stalled provisional records — deleted"
