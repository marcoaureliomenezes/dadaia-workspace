"""ADR 0090: `_RELEASE.json` is the one state filename, decided by
core.release_state; sa-release-json-validated-three-times#B4: a legacy RELEASE.json dir is
live for neither the doctor nor release.py live_ids. Size: SMALL.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dadaia_workspace.core import release_state
from dadaia_workspace.core.gitflow import resolve_live_release_id
from dadaia_workspace.features.specs.doctor_common import resolve_active_release

sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                       / "dadaia_workspace/public/skills/dd-release-implementation/scripts"))  # fmt: skip
import _release_store  # noqa: E402

_DOC = '{"schema": "release-state-v1", "release": "1.0.0", "phase": "IMPLEMENTATION"}'


def test_canonical_filename_is_underscore_release_json() -> None:
    assert release_state.RELEASE_STATE_FILENAME == "_RELEASE.json"


def test_a_legacy_state_file_makes_no_release_live(tmp_path: Path) -> None:
    """The ONE live reader, the doctor and `live_ids` agree; two live dirs are an error."""
    (tmp_path / "releases" / "1.0.0").mkdir(parents=True)
    (tmp_path / "releases" / "1.0.0" / "RELEASE.json").write_text(_DOC, encoding="utf-8")
    assert (resolve_active_release(tmp_path), _release_store.live_ids(tmp_path)) == (
        (None, None),
        [],
    )
    (tmp_path / "releases" / "1.0.0" / "_RELEASE.json").write_text(_DOC, encoding="utf-8")
    assert (resolve_active_release(tmp_path), _release_store.live_ids(tmp_path)) == (
        ("1.0.0", "IMPLEMENTATION"),
        ["1.0.0"],
    )
    (tmp_path / "releases" / "3.0.0").mkdir()
    (tmp_path / "releases" / "3.0.0" / "_RELEASE.json").write_text(_DOC, encoding="utf-8")
    assert (resolve_live_release_id(tmp_path), len(_release_store.live_ids(tmp_path))) == (None, 2)
