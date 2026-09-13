"""The ONE definition of a hand edit (0.4.7 FR6, T-047-30).

Intent: CONTRACT — 0.4.7 FR6 / SPEC §5 baseline (a record older than the store's first
governance event is never a hand edit; a record with an event whose hash no longer
matches always is; `record_ts=None` opts a timestamp-less record out of the no-event
shape).
Size: SMALL — one pure core record, no store, no CLI, no disk.

Structural frame: the ledger rules and the release-tree rule both ask this one object,
so "what is a hand edit" is decided once. These are the branches the CLI-level tests
cannot reach — the 564 pre-verb bug records are exactly the silence pinned below.
"""

from __future__ import annotations

from dadaia_workspace.core.models.telemetry import GovernanceBaseline, GovernanceEvent, record_hash

_RECORD = {"id": "b-1", "ts": "2026-09-10T00:00:00Z", "cause": "the cause a verb wrote"}


def _event(
    record: dict[str, object], *, ts: str = "2026-09-12T00:00:00Z", record_id: str = "b-1"
) -> GovernanceEvent:
    return GovernanceEvent(
        event_id="e-1",
        ts=ts,
        session_id="s",
        context="dadaia-workspace",
        verb="resolve",
        ledger="bugs",
        record_id=record_id,
        record_hash=record_hash(record),
    )


def _ask(baseline: GovernanceBaseline, record: dict[str, object]) -> str | None:
    return baseline.hand_edit(
        ledger="bugs", record_id="b-1", record=record, record_ts=str(record["ts"])
    )


def test_record_still_hashing_to_its_event_is_not_a_hand_edit() -> None:
    assert _ask(GovernanceBaseline((_event(_RECORD),)), _RECORD) is None


def test_record_changed_after_its_verb_names_the_verb_and_the_event_time() -> None:
    message = _ask(GovernanceBaseline((_event(_RECORD),)), {**_RECORD, "cause": "hand-typed"})
    assert message is not None
    assert "`resolve`" in message
    assert "2026-09-12T00:00:00Z" in message


def test_record_older_than_the_stores_first_event_is_never_a_hand_edit() -> None:
    """SPEC 0.4.7 §5: pre-verb history is not drift — the existing bug ledger enters
    measurement only when a verb touches it."""
    baseline = GovernanceBaseline(
        (_event({"id": "other"}, ts="2026-09-12T00:00:00Z", record_id="other"),)
    )
    assert baseline.first_ts == "2026-09-12T00:00:00Z"
    assert _ask(baseline, {"id": "b-1", "ts": "2026-01-01T00:00:00Z"}) is None


def test_record_newer_than_the_baseline_with_no_event_is_a_hand_edit() -> None:
    baseline = GovernanceBaseline(
        (_event({"id": "other"}, ts="2026-09-12T00:00:00Z", record_id="other"),)
    )
    message = _ask(baseline, {"id": "b-1", "ts": "2026-09-13T00:00:00Z"})
    assert message is not None
    assert "no governance verb ever wrote this record" in message


def test_a_timestampless_record_opts_out_of_the_no_event_shape() -> None:
    """`_RELEASE.json` carries no ts of its own, so an unevented release is silent."""
    baseline = GovernanceBaseline(
        (_event({"id": "other"}, ts="2026-09-12T00:00:00Z", record_id="other"),)
    )
    assert baseline.hand_edit(ledger="releases", record_id="0.4.7", record={"phase": "X"}) is None


def test_an_empty_baseline_is_silent() -> None:
    """A store that holds no event yet is a store with no baseline to measure against —
    and `first_ts` has no answer, so the rule must never reach it."""
    assert GovernanceBaseline(()).hand_edit(ledger="bugs", record_id="b-1", record={}) is None
