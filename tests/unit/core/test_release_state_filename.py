"""Release 0.4.6 candidate 1, FR1 (ADR 0007) — ``core.release_state`` owns the state
filename: ``_RELEASE.json`` canonical, legacy ``RELEASE.json`` recognised read-side so
a consumer instance keeps working until the doctor's rename fix runs.

Intent: CONTRACT (one filename decider — no reader may hand-build the name). Size: SMALL.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core import release_state
from dadaia_workspace.features.specs.doctor_common import resolve_live_release_id


def _state_doc(release: str) -> str:
    return json.dumps(
        {
            "schema": "release-state-v1",
            "release": release,
            "phase": "IMPLEMENTATION",
            "rc": None,
            "defined": None,
            "implemented": None,
            "shipped": None,
            "audited": None,
            "log": [],
        }
    )


def test_canonical_filename_is_underscore_release_json() -> None:
    assert release_state.RELEASE_STATE_FILENAME == "_RELEASE.json"
    assert release_state.LEGACY_RELEASE_STATE_FILENAME == "RELEASE.json"


def test_release_state_file_prefers_canonical_over_legacy(tmp_path: Path) -> None:
    (tmp_path / "_RELEASE.json").write_text(_state_doc("1.0.0"), encoding="utf-8")
    (tmp_path / "RELEASE.json").write_text(_state_doc("1.0.0"), encoding="utf-8")
    found = release_state.release_state_file(tmp_path)
    assert found is not None and found.name == "_RELEASE.json"


def test_release_state_file_accepts_legacy_alone(tmp_path: Path) -> None:
    (tmp_path / "RELEASE.json").write_text(_state_doc("1.0.0"), encoding="utf-8")
    found = release_state.release_state_file(tmp_path)
    assert found is not None and found.name == "RELEASE.json"


def test_release_state_file_none_when_absent(tmp_path: Path) -> None:
    assert release_state.release_state_file(tmp_path) is None


def test_resolve_live_release_sees_canonical_and_legacy_dirs(tmp_path: Path) -> None:
    """The live-release discovery goes through the ONE decider: a canonical-shape
    release and a legacy-shape release are both live; two at once stay an error."""
    releases = tmp_path / "releases"
    (releases / "1.0.0").mkdir(parents=True)
    (releases / "1.0.0" / "_RELEASE.json").write_text(_state_doc("1.0.0"), encoding="utf-8")
    rid, err = resolve_live_release_id(tmp_path)
    assert (rid, err) == ("1.0.0", None)

    legacy = tmp_path / "legacy-ws"
    (legacy / "releases" / "2.0.0").mkdir(parents=True)
    (legacy / "releases" / "2.0.0" / "RELEASE.json").write_text(
        _state_doc("2.0.0"), encoding="utf-8"
    )
    rid, err = resolve_live_release_id(legacy)
    assert (rid, err) == ("2.0.0", None)

    (releases / "3.0.0").mkdir()
    (releases / "3.0.0" / "RELEASE.json").write_text(_state_doc("3.0.0"), encoding="utf-8")
    rid, err = resolve_live_release_id(tmp_path)
    assert rid is None and err is not None and "1.0.0" in err and "3.0.0" in err
