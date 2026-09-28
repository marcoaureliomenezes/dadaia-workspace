"""Release 0.4.6 candidate 1, FR1 (ADR 0007) — ``core.release_state`` owns the state
filename: ``_RELEASE.json`` canonical, legacy ``RELEASE.json`` recognised read-side so
a consumer instance keeps working until the doctor's rename fix runs.

Intent: CONTRACT (one filename decider — no reader may hand-build the name). Size: SMALL.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core import release_state
from dadaia_workspace.core.gitflow import resolve_live_release_id


def test_release_state_file_prefers_canonical_over_legacy(tmp_path: Path) -> None:
    (tmp_path / "_RELEASE.json").write_text("{}", encoding="utf-8")
    (tmp_path / "RELEASE.json").write_text("{}", encoding="utf-8")
    found = release_state.release_state_file(tmp_path)
    assert found is not None and found.name == "_RELEASE.json"


def test_release_state_file_accepts_legacy_alone(tmp_path: Path) -> None:
    (tmp_path / "RELEASE.json").write_text("{}", encoding="utf-8")
    found = release_state.release_state_file(tmp_path)
    assert found is not None and found.name == "RELEASE.json"


def test_release_state_file_none_when_absent(tmp_path: Path) -> None:
    assert release_state.release_state_file(tmp_path) is None


def test_resolve_live_release_names_one_dir_and_refuses_two(tmp_path: Path) -> None:
    """The live-release discovery goes through the ONE decider; two at once are an error."""
    for rid, name, live in (("1.0.0", "_RELEASE.json", None), ("3.0.0", "RELEASE.json", "1.0.0")):
        assert resolve_live_release_id(tmp_path) == (live, None)
        (tmp_path / "releases" / rid).mkdir(parents=True)
        (tmp_path / "releases" / rid / name).write_text("{}", encoding="utf-8")
    rid, err = resolve_live_release_id(tmp_path)
    assert rid is None and err is not None and "1.0.0" in err and "3.0.0" in err
