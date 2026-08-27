"""FR3's commit-provenance derivation — one chronological pass, first-add wins.

**Placement is the point (v0.5.0 SPEC A3.10, `software-architect` change 4 / SA-Q4,
`specs/releases/0.5.0/reviews/S1-AR1-ruling.md` §3).** The first Draft called this "a
pure core function" and then put it in ``features/bugs/migrate_v5.py`` — the module FR3
itself declares **deletable** — while FR8's resolver and FR14's pillar 1 both need to
import it permanently. A permanent consumer importing a disposable module is the
fidelity defect this split closes: this module is **pure and stdlib-only, with no
``features/**`` import**, so it outlives the migration that first exercises it. A
contract test (``tests/contract/test_migrate_v5_not_imported_by_permanent_consumer.py``)
asserts the inverse holds too — no permanent module imports the deletable
``migrate_v5``.

**Why this module never parses JSON itself (A2.5).** FR3 step 2 says "parse each added
line as JSON through the FR2 boundary adapter" — that boundary adapter is
``features/bugs/migrate_v5.py``'s ``classify_ledger_line`` (A2.5: "the v5 event shape is
decoded by ONE boundary adapter that lives in the migration module"), a features-layer
concern. This module never imports it (that would be the exact ``core -> features``
edge A3.10 forbids); instead :func:`derive_commit_provenance` takes the classifier as an
injected callable (:data:`LineClassifier`), decoupling the permanent algorithm from the
disposable v5/v6 shape-decoding — the algorithm below has zero opinion on what a
"registration" or "terminal" line looks like on disk, only on what to do once a line has
already been classified as one.

**Ordering is the caller's contract, not this module's.** FR3 step 2 calls the walk "one
chronological pass"; :func:`derive_commit_provenance` performs exactly that — a single
pass over *commits* in the order given, taking the FIRST commit that adds a
classifiable line for each ``(bug_id, kind)`` pair (step 3, "first-add wins"). It trusts
the caller (``GitHistoryReader.log_added_lines``, ``git log --all --no-merges --reverse
--date-order``) to have already resolved topological + date ordering; a genuine
same-instant, no-ancestry-relation tie between two commits is exceedingly rare and, when
it occurs, is resolved by the reader's own log order — re-sorting inside this pure
function would turn "one chronological pass" into two and duplicate ordering logic
better owned once, at the git-facing seam.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from dadaia_workspace.core.protocols.git_history_reader import HistoryCommit

__all__ = [
    "ClassifiedLedgerLine",
    "DerivedBugProvenance",
    "Granularity",
    "LedgerLineKind",
    "LineClassifier",
    "derive_commit_provenance",
]

#: The closed granularity vocabulary (FR3 step 4, D-A — one marker name everywhere).
#: ``exact`` — the commit adds exactly one bug's line of this kind AND touches at least
#: one file outside ``specs/``. ``release-squash`` — the commit adds more than one bug's
#: line of this kind (a release-level squash). ``ledger-only`` — the commit adds exactly
#: one bug's line of this kind AND touches no file outside ``specs/`` (the code change,
#: if any, is elsewhere or unknown). These are STRUCTURAL definitions computed from the
#: diff alone — never a narrative/measured category.
Granularity = Literal["exact", "release-squash", "ledger-only"]


class LedgerLineKind(StrEnum):
    """What one classified ledger line contributes to its bug id's provenance.

    ``REGISTRATION`` — a v5 ``reported`` event, or a v6 record newly present with
    ``status == "open"`` (FR3 step 3). ``TERMINAL`` — a v5 event whose ``event`` is one
    of the four terminal kinds, or a v6 record whose ``status`` is terminal. A v5
    ``picked``/``archived`` line, or any line the classifier cannot place in either
    bucket, is not represented here at all — the classifier returns ``None`` for it
    (FR2: "the value, its transition and picked_by all disappear").
    """

    REGISTRATION = "registration"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class ClassifiedLedgerLine:
    """One added ledger line, already decoded to (which bug, what kind of line)."""

    bug_id: str
    kind: LedgerLineKind


#: Injected by the caller (``features/bugs/migrate_v5.py``'s ``classify_ledger_line`` in
#: production; a minimal test-local callable in this module's own unit tests) — see the
#: module docstring's A2.5 note. Returns ``None`` for a line that is neither a
#: registration nor a terminal shape (malformed JSON, a non-object line, a
#: ``picked``/``archived`` event, an unparseable record).
LineClassifier = Callable[[str], "ClassifiedLedgerLine | None"]


@dataclass(frozen=True)
class DerivedBugProvenance:
    """One bug id's derived commit provenance — the FR3 output row.

    ``migration_note`` is populated **only** when this module found OTHER evidence the
    bug id exists (a terminal line was classified for it somewhere in the walked
    history) but never found a commit adding a REGISTRATION line for it — the "null only
    when nothing adds the line" edge case (FR3 step 5), measured at zero cases on the
    corpus as of 2026-08-26. A bug that is simply still open (no terminal line anywhere)
    is the ordinary, expected case: ``resolved_commit`` stays ``None`` with **no**
    ``migration_note`` — that is not an anomaly.
    """

    bug_id: str
    registration_commit: str | None
    registration_granularity: Granularity | None
    resolved_commit: str | None
    resolution_granularity: Granularity | None
    migration_note: str | None = None


def _granularity(bug_line_count: int, *, touches_outside_specs: bool) -> Granularity:
    """FR3 step 4's structural marker for one commit, one line kind. Never called with
    ``bug_line_count == 0`` (the caller only computes a marker when at least one bug id
    of that kind was classified in the commit)."""
    if bug_line_count > 1:
        return "release-squash"
    return "exact" if touches_outside_specs else "ledger-only"


def derive_commit_provenance(
    commits: Iterable[HistoryCommit],
    classify_line: LineClassifier,
) -> dict[str, DerivedBugProvenance]:
    """FR3's whole derivation: one chronological pass over *commits*, first-add wins.

    For each commit, in the order given: classify every added line via
    *classify_line*, then — separately for the registration-kind lines and the
    terminal-kind lines this SAME commit added — compute this commit's granularity
    marker (step 4) from how many distinct bug ids got a line of that kind added here,
    and whether the commit's ``touched_paths`` includes anything outside ``specs/``.
    A bug id that already has a ``registration_commit``/``resolved_commit`` from an
    earlier commit in the pass is left untouched by a later commit re-adding the same
    kind of line for it (step 3: first-add wins) — the later commit's marker is still
    computed from everything it added (a re-add still counts toward that commit's OWN
    squash size), it simply never overwrites an earlier winner.

    Pure: makes no I/O call, raises nothing on its own (a malformed *commits* entry is
    the caller's contract to avoid), and is trivially idempotent — the same *commits*
    and *classify_line* always fold to the same result (A3.4's idempotence acceptance,
    at the algorithm level; the full migration's byte-identical-output acceptance is
    proven at the runner/CLI seam, not here).
    """
    registration_commit_of: dict[str, str] = {}
    registration_granularity_of: dict[str, Granularity] = {}
    resolved_commit_of: dict[str, str] = {}
    resolution_granularity_of: dict[str, Granularity] = {}
    known_bug_ids: set[str] = set()

    for commit in commits:
        registration_bug_ids: set[str] = set()
        terminal_bug_ids: set[str] = set()
        for raw_line in commit.added_lines:
            classified = classify_line(raw_line)
            if classified is None:
                continue
            known_bug_ids.add(classified.bug_id)
            if classified.kind is LedgerLineKind.REGISTRATION:
                registration_bug_ids.add(classified.bug_id)
            else:
                terminal_bug_ids.add(classified.bug_id)

        touches_outside_specs = any(not path.startswith("specs/") for path in commit.touched_paths)

        if registration_bug_ids:
            marker = _granularity(
                len(registration_bug_ids), touches_outside_specs=touches_outside_specs
            )
            for bug_id in registration_bug_ids:
                if bug_id in registration_commit_of:
                    continue  # first-add wins — a later re-add never overrides.
                registration_commit_of[bug_id] = commit.sha
                registration_granularity_of[bug_id] = marker

        if terminal_bug_ids:
            marker = _granularity(
                len(terminal_bug_ids), touches_outside_specs=touches_outside_specs
            )
            for bug_id in terminal_bug_ids:
                if bug_id in resolved_commit_of:
                    continue
                resolved_commit_of[bug_id] = commit.sha
                resolution_granularity_of[bug_id] = marker

    return {
        bug_id: DerivedBugProvenance(
            bug_id=bug_id,
            registration_commit=registration_commit_of.get(bug_id),
            registration_granularity=registration_granularity_of.get(bug_id),
            resolved_commit=resolved_commit_of.get(bug_id),
            resolution_granularity=resolution_granularity_of.get(bug_id),
            migration_note=(
                None
                if bug_id in registration_commit_of
                else (
                    "no commit in the walked history adds a registration line for "
                    "this bug id (FR3 step 5)"
                )
            ),
        )
        for bug_id in sorted(known_bug_ids)
    }
