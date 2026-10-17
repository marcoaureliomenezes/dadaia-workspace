"""A picked backlog item stays ``picked`` in ``active[]`` and exits once, at closure.

No source or test file names the ``CONSUMED`` token, its ledger module, its record class
or its consumed histo file.

Size: MEDIUM (reads the shipped source tree and runs `git ls-files`; no fixture, no network).
"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

import dadaia_workspace
from tests.helpers.oslib import read_text, run, write_text

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

#: Law and skill text under ``public/`` is outside this contract; it covers code and tests.
_SCOPES = (_PKG / "core", _PKG / "features", _PKG / "cli", _PKG / "hooks")


def _files() -> list[Path]:
    tests = run(
        ["git", "-C", str(_TESTS.parent), "ls-files", "-z", "--", "tests/*.py"], check=True
    ).stdout
    return [
        *(p for scope in _SCOPES for p in scope.rglob("*.py")),
        *(_TESTS.parent / t for t in tests.split("\0") if t),
    ]


def _offenders() -> list[str]:
    hits: list[str] = []
    for path in _files():
        if "__pycache__" in path.parts or path.name == Path(__file__).name:
            continue
        for lineno, line in enumerate(read_text(path).splitlines(), 1):
            if _DEAD_RE.search(line):
                hits.append(f"{path.relative_to(_PKG.parent).as_posix()}:{lineno}: {line.strip()}")
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


def test_an_untracked_scratch_file_under_tests_is_not_judged() -> None:
    scratch = _TESTS / "tmp" / f"exit-probe-{uuid.uuid4().hex[:8]}"
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        write_text(scratch / "test_gone.py", "X = 'CONSUMED'\n")
        hits = _offenders()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    assert [h for h in hits if scratch.name in h] == []
