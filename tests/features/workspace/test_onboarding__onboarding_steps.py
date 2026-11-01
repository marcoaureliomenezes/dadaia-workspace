"""The census of the onboarding step list — ids
and order — replaces the old regex census of fix text. A step's kind follows its fix line."""

from __future__ import annotations

from dadaia_workspace.features.workspace.onboarding import STEP_IDS, STEPS


def test_the_step_list_is_the_spec_order() -> None:
    assert STEP_IDS == ("context", "bind", "constitution", "specs", "first-pass", "publish")
    assert [step_id for step_id, *_ in STEPS] == [
        "bind",
        "constitution",
        "specs",
        "first-pass",
        "publish",
    ]
