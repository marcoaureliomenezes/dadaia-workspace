"""core/release_state exposes the state file's name and the id grammars only. Size: SMALL."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core import release_state

_PACKAGE = Path(__file__).resolve().parents[2] / "dadaia_workspace"


def test_core_exposes_the_name_and_the_grammars_only() -> None:
    assert sorted(release_state.__all__) == [
        "CANDIDATE_RE",
        "LEGACY_RELEASE_STATE_FILENAME",
        "RELEASE_ID_RE",
        "RELEASE_STATE_FILENAME",
    ]
