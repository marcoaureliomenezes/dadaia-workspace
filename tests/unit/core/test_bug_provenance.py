"""``core.bug_provenance.derive_commit_provenance`` — FR3's pure, one-pass derivation.

Intent: CONTRACT — 0.5.0 A3.10. Size: SMALL.

Every case here runs the pure function over an **in-memory** :class:`HistoryCommit`
fixture with a minimal, test-local classifier (``_classify`` below) — deliberately NOT
:func:`~dadaia_workspace.features.bugs.migrate_v5.classify_ledger_line`, so this suite
proves the ALGORITHM (first-add-wins, granularity-by-count-and-touched-paths) is
decoupled from the v5/v6 JSON shape that module decodes (A2.5). These tests are
CONTRACT, not SCAFFOLD: ``core/bug_provenance.py`` outlives ``migrate_v5.py`` (it is the
permanent derivation FR8's resolver and FR14's pillar 1 both import), so tagging them
SCAFFOLD would schedule the deletion of a permanent contract (SPEC FR3 "Marking, split
correctly", qa-engineer amendment 10).

No synthetic git repository is required for any test in this file — that lives in
``tests/contract/test_git_history_reader_log_added_lines.py`` instead (per the SPEC's
own placement rule: subprocess/I/O cost belongs in ``tests/contract/``, never
``tests/unit/``).
"""

from __future__ import annotations

from dadaia_workspace.core.bug_provenance import (
    ClassifiedLedgerLine,
    LedgerLineKind,
    derive_commit_provenance,
)
from dadaia_workspace.core.protocols.git_history_reader import HistoryCommit


def _classify(line: str) -> ClassifiedLedgerLine | None:
    """Minimal test-local line classifier — ``"REG <id>"`` / ``"TERM <id>"`` prefixes,
    anything else unclassifiable (returns ``None``, mirroring a malformed/irrelevant
    added ledger line the real adapter would also drop)."""
    if line.startswith("REG "):
        return ClassifiedLedgerLine(
            bug_id=line.removeprefix("REG "), kind=LedgerLineKind.REGISTRATION
        )
    if line.startswith("TERM "):
        return ClassifiedLedgerLine(bug_id=line.removeprefix("TERM "), kind=LedgerLineKind.TERMINAL)
    return None


def test_single_bug_registration_is_exact_when_the_commit_touches_a_non_specs_file() -> None:
    commits = [
        HistoryCommit(
            sha="c1",
            parents=(),
            date="2026-01-01T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl", "dadaia_workspace/features/bugs/service.py"),
            # An unclassifiable line is present too — proves it is silently dropped,
            # never mistaken for a bug line.
            added_lines=("REG bug-alpha", "not-json-or-anything-recognisable"),
        ),
    ]

    result = derive_commit_provenance(commits, _classify)

    assert set(result) == {"bug-alpha"}
    provenance = result["bug-alpha"]
    assert provenance.registration_commit == "c1"
    assert provenance.registration_granularity == "exact"
    assert provenance.resolved_commit is None
    assert provenance.resolution_granularity is None
    assert provenance.migration_note is None


def test_three_bug_squash_marks_release_squash_for_all_three() -> None:
    commits = [
        HistoryCommit(
            sha="c1",
            parents=(),
            date="2026-01-01T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl",),
            added_lines=("REG bug-a", "REG bug-b", "REG bug-c"),
        ),
    ]

    result = derive_commit_provenance(commits, _classify)

    for bug_id in ("bug-a", "bug-b", "bug-c"):
        assert result[bug_id].registration_commit == "c1"
        assert result[bug_id].registration_granularity == "release-squash"


def test_ledger_only_resolution_when_the_resolving_commit_touches_nothing_outside_specs() -> None:
    commits = [
        HistoryCommit(
            sha="c1",
            parents=(),
            date="2026-01-01T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl", "code.py"),
            added_lines=("REG bug-x",),
        ),
        HistoryCommit(
            sha="c2",
            parents=("c1",),
            date="2026-01-02T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl",),
            added_lines=("TERM bug-x",),
        ),
    ]

    result = derive_commit_provenance(commits, _classify)

    provenance = result["bug-x"]
    assert provenance.registration_commit == "c1"
    assert provenance.registration_granularity == "exact"
    assert provenance.resolved_commit == "c2"
    assert provenance.resolution_granularity == "ledger-only"


def test_a_line_re_added_by_a_later_squash_never_overrides_the_first_add() -> None:
    commits = [
        HistoryCommit(
            sha="c1",
            parents=(),
            date="2026-01-01T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl", "code.py"),
            added_lines=("REG bug-alpha",),
        ),
        # A later "squash" re-adds bug-alpha's registration line (e.g. a rebase/cherry
        # -pick artifact) alongside a genuinely NEW bug's first registration.
        HistoryCommit(
            sha="c2",
            parents=("c1",),
            date="2026-01-02T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl",),
            added_lines=("REG bug-alpha", "REG bug-beta"),
        ),
    ]

    result = derive_commit_provenance(commits, _classify)

    # First-add wins: bug-alpha's provenance is entirely c1's, untouched by c2.
    assert result["bug-alpha"].registration_commit == "c1"
    assert result["bug-alpha"].registration_granularity == "exact"
    # bug-beta genuinely first appears in c2, whose squash size (2 bug ids added,
    # including the re-add) still marks it release-squash.
    assert result["bug-beta"].registration_commit == "c2"
    assert result["bug-beta"].registration_granularity == "release-squash"


def test_a_bug_whose_registration_line_is_never_added_carries_a_migration_note() -> None:
    """A bug id known only via a TERMINAL line (never a registration line anywhere in
    the walked history) is FR3 step 5's "null only when nothing adds the line" case:
    ``registration_commit`` stays ``None`` WITH a ``migration_note`` — distinct from the
    ordinary "still open" case (a bug with a registration but no terminal line), which
    carries no note at all (see the first test above)."""
    commits = [
        HistoryCommit(
            sha="c1",
            parents=(),
            date="2026-01-01T00:00:00+00:00",
            touched_paths=("specs/bugs/bugs.jsonl", "code.py"),
            added_lines=("TERM bug-ghost",),
        ),
    ]

    result = derive_commit_provenance(commits, _classify)

    provenance = result["bug-ghost"]
    assert provenance.registration_commit is None
    assert provenance.registration_granularity is None
    assert provenance.migration_note is not None
    assert provenance.resolved_commit == "c1"
    assert provenance.resolution_granularity == "exact"
