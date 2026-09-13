"""``BugService.heal_closed_at`` — the migration 0.4.7 candidate 1's invariant shipped without.

Intent: CONTRACT — bugs-update-cannot-heal-terminal-record-missing-closed-at
Size: SMALL — in-memory ledger files under tmp_path and a fake, no-subprocess
``GitHistoryReader``; never a real git repository, never the live ledger.

Structural frame: making ``closed_at`` non-null-iff-terminal (``BugRecord.__post_init__``)
landed with a ONE-TIME back-fill run as a throwaway script over this repo only (T-047-08,
18ee932c). Every other ledger kept terminal records with ``closed_at: null``, which the
model now refuses to construct — so the healing write path could not load the very
records it had to heal. The back-fill is a FIXER here, shipped with the invariant, and it
operates on raw ledger lines precisely because the records are unconstructible.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from dadaia_workspace.core.models.bugs import BugRecord
from dadaia_workspace.core.models.git_history import HistoryCommit
from dadaia_workspace.features.bugs.service import BugService

from ._bug_record_helpers import bug_record_store

_TS = "2026-08-26T10:00:00Z"


def _raw(bug_id: str, *, status: str, closed_at: str | None = None) -> dict[str, object]:
    return {
        "id": bug_id,
        "ts": _TS,
        "reported_by": "software-engineer",
        "title": "t",
        "severity": "HIGH",
        "surface": "bugs",
        "component": "c",
        "context": "dadaia-workspace",
        "symptom": "s",
        "repro": "r",
        "expected": "e",
        "status": status,
        "closed_at": closed_at,
        "cause": "c" if status != "open" else None,
        "caused_by": None,
        "lineage_source": None,
        "registration_commit": None,
        "registration_granularity": None,
        "resolved_commit": None,
        "resolution_granularity": None,
        "resolved_release": None,
        "audited": None,
    }


def _write_ledger(root: Path, records: list[dict[str, object]]) -> Path:
    path = root / "bugs" / "BUGS.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8"
    )
    return path


def _read_ledger(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()
    ]


class _FakeHistoryReader:
    def __init__(self, commits: tuple[HistoryCommit, ...]) -> None:
        self.commits = commits
        self.calls: list[tuple[Path, str]] = []

    def log_added_lines(self, repo: Path, pathspec: str) -> Iterable[HistoryCommit]:
        self.calls.append((repo, pathspec))
        return self.commits


def test_heal_stamps_closed_at_from_the_commit_that_added_the_terminal_line(
    tmp_path: Path,
) -> None:
    """The back-fill's real source is the ledger's own history — the date of the FIRST
    commit whose BUGS.jsonl carried this record terminal, exactly what T-047-08's script
    computed by hand."""
    terminal = _raw("bug-alpha", status="resolved")
    path = _write_ledger(tmp_path, [terminal])
    reader = _FakeHistoryReader(
        (
            HistoryCommit(
                sha="c1",
                parents=(),
                date="2026-08-26T10:00:00+00:00",
                touched_paths=("specs/bugs/BUGS.jsonl",),
                added_lines=(json.dumps({**terminal, "status": "open"}),),
            ),
            HistoryCommit(
                sha="c2",
                parents=("c1",),
                date="2026-09-02T08:30:00+00:00",
                touched_paths=("specs/bugs/BUGS.jsonl",),
                added_lines=(json.dumps(terminal),),
            ),
        )
    )
    service = BugService(bug_record_store(tmp_path), history_reader=reader, repo_root=tmp_path)

    assert service.heal_closed_at() == 1
    assert _read_ledger(path)[0]["closed_at"] == "2026-09-02T08:30:00Z"
    assert reader.calls == [(tmp_path, "specs/bugs/")]


def test_heal_falls_back_to_ts_when_history_is_unavailable_and_the_record_then_loads(
    tmp_path: Path,
) -> None:
    """No history reader wired (or a bug id the walk never saw): the record's own filing
    date is the honest floor — never invented, never earlier than ``ts``, which is the
    one bound ``__post_init__`` also enforces. After healing, the record LOADS."""
    path = _write_ledger(tmp_path, [_raw("bug-beta", status="resolved")])
    service = BugService(bug_record_store(tmp_path))

    assert service.heal_closed_at() == 1
    assert _read_ledger(path)[0]["closed_at"] == _TS

    healed = BugRecord.from_dict(_read_ledger(path)[0])
    assert healed.closed_at == _TS
    assert [r.id for r in service.status(include_closed=True)] == ["bug-beta"]


def test_heal_is_idempotent_and_never_walks_history_with_nothing_to_back_fill(
    tmp_path: Path,
) -> None:
    """The fixer runs once per reported issue, so a second pass must cost nothing: with
    every terminal record already stamped there is no walk and no write."""
    _write_ledger(
        tmp_path,
        [
            _raw("bug-open", status="open"),
            _raw("bug-done", status="resolved", closed_at="2026-09-01T00:00:00Z"),
        ],
    )
    reader = _FakeHistoryReader(())
    service = BugService(bug_record_store(tmp_path), history_reader=reader, repo_root=tmp_path)

    assert service.heal_closed_at() == 0
    assert reader.calls == []


def test_heal_leaves_an_open_record_and_a_malformed_line_untouched(tmp_path: Path) -> None:
    """The back-fill writes ONE field on the records that need it. An open record keeps
    ``closed_at: null`` (the same invariant, other direction) and a line this migration
    cannot read is preserved verbatim rather than dropped."""
    path = _write_ledger(tmp_path, [_raw("bug-open", status="open")])
    path.write_text(path.read_text(encoding="utf-8") + "not json at all\n", encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    service = BugService(bug_record_store(tmp_path))

    assert service.heal_closed_at() == 0
    assert path.read_text(encoding="utf-8") == before
