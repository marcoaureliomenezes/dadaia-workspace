"""``BugService.resolved_commit`` — FR8's one resolver seam (AS-1, v0.5.0 T-050-17).

Intent: CONTRACT — 0.5.0 A8.2. Size: SMALL.

Exercises the seam's two branches purely in-memory (a fake, no-subprocess
``GitHistoryReader``): stored-value short-circuit (never even consulting the reader)
and git-derived fallback (via ``core.bug_provenance.derive_commit_provenance``,
classified through the SAME v5/v6 boundary adapter T-050-09/10 already use,
``features.bugs.migrate_v5.classify_ledger_line``). The real-history, ``stored ==
derived`` proof over the live ledger is a SEPARATE test
(``tests/contract/test_resolved_commit_stored_equals_derived.py``, A8.2's own real-git
sample) — this file never touches a subprocess or the live ``specs/bugs/BUGS.jsonl``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from dadaia_workspace.core.models.bugs import BugRecord
from dadaia_workspace.core.protocols.git_history_reader import HistoryCommit
from dadaia_workspace.features.bugs.service import BugService

from ._bug_record_helpers import bug_record_store

_TS = "2026-08-26T10:00:00Z"


def _record(bug_id: str, *, status: str = "open", resolved_commit: str | None = None) -> BugRecord:
    return BugRecord(
        id=bug_id,
        ts=_TS,
        reported_by="software-engineer",
        title="t",
        severity="HIGH",
        surface="bugs",
        component="c",
        context="dadaia-workspace",
        symptom="s",
        repro="r",
        expected="e",
        status=status,
        resolved_commit=resolved_commit,
    )


class _RaisingHistoryReader:
    """Proves the stored-value branch never consults history at all."""

    def log_added_lines(self, repo: Path, pathspec: str) -> Iterable[HistoryCommit]:
        raise AssertionError(
            "resolved_commit() must not consult history_reader when the record "
            "already carries a stored value (AS-1: stored wins, no derivation)"
        )


class _FakeHistoryReader:
    """A caller-supplied, in-memory ``GitHistoryReader`` (duck-typed to the Protocol),
    recording every call so a test can assert both arguments are threaded through."""

    def __init__(self, commits: tuple[HistoryCommit, ...]) -> None:
        self.commits = commits
        self.calls: list[tuple[Path, str]] = []

    def log_added_lines(self, repo: Path, pathspec: str) -> Iterable[HistoryCommit]:
        self.calls.append((repo, pathspec))
        return self.commits


def test_resolved_commit_returns_stored_value_without_consulting_history(tmp_path: Path) -> None:
    service = BugService(
        bug_record_store(tmp_path),
        history_reader=_RaisingHistoryReader(),
        repo_root=tmp_path,
    )
    record = _record("bug-alpha", status="resolved", resolved_commit="c-stored")

    assert service.resolved_commit(record) == "c-stored"


def test_resolved_commit_returns_none_when_no_history_reader_configured(tmp_path: Path) -> None:
    service = BugService(bug_record_store(tmp_path))
    record = _record("bug-open")

    assert service.resolved_commit(record) is None


def test_resolved_commit_returns_none_when_repo_root_missing_even_with_reader(
    tmp_path: Path,
) -> None:
    service = BugService(bug_record_store(tmp_path), history_reader=_FakeHistoryReader(()))
    record = _record("bug-open")

    assert service.resolved_commit(record) is None


def test_resolved_commit_derives_from_v6_shaped_history_when_stored_is_absent(
    tmp_path: Path,
) -> None:
    commits = (
        HistoryCommit(
            sha="c1",
            parents=(),
            date="2026-01-01T00:00:00+00:00",
            touched_paths=("specs/bugs/BUGS.jsonl", "dadaia_workspace/features/bugs/service.py"),
            added_lines=('{"id": "bug-beta", "status": "open"}',),
        ),
        HistoryCommit(
            sha="c2",
            parents=("c1",),
            date="2026-01-02T00:00:00+00:00",
            touched_paths=("specs/bugs/BUGS.jsonl",),
            added_lines=('{"id": "bug-beta", "status": "resolved"}',),
        ),
    )
    reader = _FakeHistoryReader(commits)
    repo = tmp_path / "repo"
    service = BugService(bug_record_store(tmp_path), history_reader=reader, repo_root=repo)
    forced = _record("bug-beta")  # resolved_commit=None -> forces the derived branch

    derived = service.resolved_commit(forced)

    assert derived == "c2"
    assert reader.calls == [(repo, "specs/bugs/")]


def test_resolved_commit_derives_from_v5_shaped_history_when_stored_is_absent(
    tmp_path: Path,
) -> None:
    """The walked history spans pre-migration commits too — the classifier must decode
    BOTH shapes (A2.5), so this case proves the v5 event shape derives correctly."""
    commits = (
        HistoryCommit(
            sha="c1",
            parents=(),
            date="2026-01-01T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl", "x.py"),
            added_lines=('{"event": "reported", "bug_id": "bug-gamma"}',),
        ),
        HistoryCommit(
            sha="c2",
            parents=("c1",),
            date="2026-01-02T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl",),
            added_lines=('{"event": "resolved", "bug_id": "bug-gamma"}',),
        ),
    )
    reader = _FakeHistoryReader(commits)
    repo = tmp_path / "repo"
    service = BugService(bug_record_store(tmp_path), history_reader=reader, repo_root=repo)
    forced = _record("bug-gamma")

    assert service.resolved_commit(forced) == "c2"


def test_resolved_commit_returns_none_when_history_never_captures_a_terminal_line(
    tmp_path: Path,
) -> None:
    """FR3 step 5: a bug still open in the walked history stays ``None`` — correct, not
    a failure (A8.2)."""
    commits = (
        HistoryCommit(
            sha="c1",
            parents=(),
            date="2026-01-01T00:00:00+00:00",
            touched_paths=("specs/bugs/BUGS.jsonl", "x.py"),
            added_lines=('{"id": "bug-delta", "status": "open"}',),
        ),
    )
    reader = _FakeHistoryReader(commits)
    repo = tmp_path / "repo"
    service = BugService(bug_record_store(tmp_path), history_reader=reader, repo_root=repo)
    forced = _record("bug-delta")

    assert service.resolved_commit(forced) is None


def test_resolved_commit_returns_none_when_bug_id_absent_from_walked_history(
    tmp_path: Path,
) -> None:
    reader = _FakeHistoryReader(())
    repo = tmp_path / "repo"
    service = BugService(bug_record_store(tmp_path), history_reader=reader, repo_root=repo)
    forced = _record("bug-never-seen")

    assert service.resolved_commit(forced) is None


def test_resolved_commit_uses_replace_to_force_derivation_on_an_already_stored_record(
    tmp_path: Path,
) -> None:
    """Documents the exact device the A8.2 real-history contract test relies on:
    ``dataclasses.replace(record, resolved_commit=None)`` forces the SAME seam through
    its derived branch for a record that already carries a stored value."""
    commits = (
        HistoryCommit(
            sha="c1",
            parents=(),
            date="2026-01-01T00:00:00+00:00",
            touched_paths=("specs/bugs/BUGS.jsonl", "x.py"),
            added_lines=('{"id": "bug-epsilon", "status": "open"}',),
        ),
        HistoryCommit(
            sha="c2",
            parents=("c1",),
            date="2026-01-02T00:00:00+00:00",
            touched_paths=("specs/bugs/BUGS.jsonl",),
            added_lines=('{"id": "bug-epsilon", "status": "resolved"}',),
        ),
    )
    reader = _FakeHistoryReader(commits)
    repo = tmp_path / "repo"
    service = BugService(bug_record_store(tmp_path), history_reader=reader, repo_root=repo)
    stored = _record("bug-epsilon", status="resolved", resolved_commit="c2")

    forced = replace(stored, resolved_commit=None)
    derived = service.resolved_commit(forced)

    assert derived == stored.resolved_commit == "c2"
