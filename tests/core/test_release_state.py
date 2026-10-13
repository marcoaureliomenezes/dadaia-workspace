"""core/release_state exposes
the state file's name and the id grammars only; no package module outside the release script validates a state
document. Size: SMALL.
"""

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
