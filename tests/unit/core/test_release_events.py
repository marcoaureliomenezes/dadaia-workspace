"""``core.release_events`` — the read-only RELEASE.jsonl fold (v0.5.0 FR4, D3, T-050-11).

Intent: CONTRACT — SPEC v0.5.0 A4.2 (milestone immutability: the fold takes the FIRST
``defined``/``implemented``/``shipped`` record and reports every later one as a
duplicate finding, never silently overwriting it) plus the phase LAST-wins resolution
D3 assigns the SDD gate. Size: SMALL — pure functions over in-memory text, no I/O.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.release_events import fold_release_events, parse_release_events

pytestmark = pytest.mark.unit


def test_fold_takes_last_phase_and_first_milestone_reporting_later_duplicates() -> None:
    """Three behaviors in one fold, each independently checkable:

    1. ``phase`` resolves to the LAST ``phase`` record's value (D3: the gate folds the
       newest phase declaration), not the first and not a concatenation.
    2. ``milestones["defined"]`` is the FIRST ``defined`` record (its original sha),
       even though a second ``defined`` record with a DIFFERENT sha appears later in
       the stream — the milestone is immutable at the model level (A4.2).
    3. The later, different-sha ``defined`` record is captured in
       ``duplicate_milestones`` as a finding, never dropped and never silently applied.
    4. A malformed line (bad JSON) is skipped and reported as a parse error without
       losing the well-formed records around it.
    """
    text = "\n".join(
        [
            '{"ts":"2026-08-27T10:00:00Z","event":"phase","agent":"product-engineer","data":{"phase":"DEFINITION"}}',
            '{"ts":"2026-08-27T10:00:01Z","event":"defined","agent":"product-engineer","data":{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","pr":null}}',
            "not-json-at-all",
            '{"ts":"2026-08-27T11:00:00Z","event":"phase","agent":"software-engineer","data":{"phase":"IMPLEMENTATION"}}',
            '{"ts":"2026-08-27T12:00:00Z","event":"defined","agent":"project-auditor","data":{"sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","pr":210}}',
        ]
    )

    events, errors = parse_release_events(text)

    assert len(errors) == 1
    assert "line 3" in errors[0]
    assert len(events) == 4  # the malformed line never entered the event stream

    fold = fold_release_events(events)

    assert fold.phase == "IMPLEMENTATION"  # last phase record wins, not the first
    assert fold.milestones["defined"].data["sha"] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert len(fold.duplicate_milestones) == 1
    assert fold.duplicate_milestones[0].data["sha"] == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    # the duplicate never overwrote the first-seen sha
    assert fold.milestones["defined"].data["sha"] != fold.duplicate_milestones[0].data["sha"]
