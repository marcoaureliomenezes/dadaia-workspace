"""``features.bugs.migrate_v5``'s v5/v6 boundary classifier and one-shot runner.

Intent: SCAFFOLD — T-050-09 — expires: 0.6.0. Size: SMALL.

Unlike ``tests/unit/core/test_bug_provenance.py`` (CONTRACT — the pure derivation
outlives this module), this file's subject — ``classify_ledger_line``,
``run_migration`` — is DELETABLE with ``migrate_v5.py`` itself (SPEC FR3, AR-1 ruling
answer (a)): T-050-10's physical migration is the last consumer, and 0.6.0 deletes the
whole module. A slipped expiry is renewed by an explicit ``qa-engineer`` verdict at that
release's closure, never by silence (V28 turns an unrenewed expiry RED).

This single test exercises BOTH halves the "adapter and runner" marking names: it
decodes a real v5 event-shaped line AND a real v6 record-shaped line through
``classify_ledger_line`` (proving the boundary adapter, A2.5), and it runs
``run_migration`` — the composition of an injected fake
``GitHistoryReader`` with that classifier and ``core.bug_provenance``'s pure fold —
TWICE against the identical fixture, proving the runner-level idempotence FR3/A3.4
requires ("running the migration twice produces identical output").
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core.protocols.git_history_reader import HistoryCommit
from dadaia_workspace.features.bugs.migrate_v5 import run_migration


@dataclass
class _FakeGitHistoryReader:
    """A caller-supplied ``GitHistoryReader`` (duck-typed to the Protocol) that
    returns a fixed, in-memory commit history regardless of *repo*/*pathspec* — while
    recording every call, so the test can assert ``run_migration`` actually threads
    both arguments through rather than hard-coding them."""

    commits: tuple[HistoryCommit, ...]
    calls: list[tuple[Path, str]] = field(default_factory=list)

    def log_added_lines(self, repo: Path, pathspec: str) -> Iterable[HistoryCommit]:
        self.calls.append((repo, pathspec))
        return self.commits


def test_run_migration_decodes_both_shapes_and_is_idempotent(tmp_path: Path) -> None:
    commits = (
        HistoryCommit(
            sha="c1",
            parents=(),
            date="2026-01-01T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl", "dadaia_workspace/features/bugs/service.py"),
            added_lines=('{"event": "reported", "bug_id": "bug-alpha"}',),
        ),
        HistoryCommit(
            sha="c2",
            parents=("c1",),
            date="2026-01-02T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl",),
            added_lines=('{"event": "resolved", "bug_id": "bug-alpha"}',),
        ),
        HistoryCommit(
            sha="c3",
            parents=("c2",),
            date="2026-01-03T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl", "x.py"),
            # v6 record shape (no "event" key) — proves classify_ledger_line's
            # SECOND branch, not just the v5 one c1/c2 exercise.
            added_lines=('{"id": "bug-beta", "status": "open"}',),
        ),
    )
    reader = _FakeGitHistoryReader(commits=commits)
    repo = tmp_path / "repo"

    first = run_migration(repo, "specs/bugs/", reader)
    second = run_migration(repo, "specs/bugs/", reader)

    assert first == second

    assert first["bug-alpha"].registration_commit == "c1"
    assert first["bug-alpha"].registration_granularity == "exact"
    assert first["bug-alpha"].resolved_commit == "c2"
    assert first["bug-alpha"].resolution_granularity == "ledger-only"

    assert first["bug-beta"].registration_commit == "c3"
    assert first["bug-beta"].registration_granularity == "exact"
    assert first["bug-beta"].resolved_commit is None

    assert reader.calls == [(repo, "specs/bugs/"), (repo, "specs/bugs/")]
