"""sa-release-json-validated-three-times#B7: core/release_state exposes
phase reading only; no package module outside the release script validates a state
document. Size: SMALL.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core import release_state

pytestmark = pytest.mark.unit

_PACKAGE = Path(__file__).resolve().parents[3] / "dadaia_workspace"


def test_core_reads_the_phase_and_judges_nothing() -> None:
    assert sorted(release_state.__all__) == [
        "CANDIDATE_RE",
        "LEGACY_RELEASE_STATE_FILENAME",
        "RELEASE_ID_RE",
        "RELEASE_STATE_FILENAME",
        "read_phase",
    ]
    assert release_state.read_phase('{"phase": "CLOSURE"}') == "CLOSURE"
    assert release_state.read_phase('{"phase": "closure", "extra": 1}') == "closure"
    assert release_state.read_phase("{") is None
    assert release_state.read_phase('["phase"]') is None
    assert release_state.read_phase('{"phase": ""}') is None


def test_no_release_validity_decision_lives_outside_the_script() -> None:
    offenders = [
        p.relative_to(_PACKAGE).as_posix()
        for p in _PACKAGE.rglob("*.py")
        if "public" not in p.parts
        and (
            '"releases/release-state-v1"' in (t := p.read_text("utf-8"))
            or "parse_release_state" in t
        )
    ]
    assert offenders == []
