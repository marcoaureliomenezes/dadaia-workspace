"""Intent: CONTRACT — AC1.7 (T-050-17): the census of the onboarding step list — ids,
kinds and order — replaces the old regex census of fix text."""

from __future__ import annotations

from dadaia_workspace.features.workspace.onboarding import STEP_IDS, STEPS


def test_the_step_list_is_the_spec_order_with_its_kinds() -> None:
    assert STEP_IDS == ("context", "bind", "constitution", "specs", "first-pass", "publish")
    assert [(step_id, kind) for step_id, kind, *_ in STEPS] == [
        ("bind", "command"),
        ("constitution", "agent"),
        ("specs", "command"),
        ("first-pass", "agent"),
        ("publish", "command"),
    ]
