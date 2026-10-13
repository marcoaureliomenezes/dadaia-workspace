"""`_RELEASE.json` is the one state filename, decided by core.release_state; a legacy
RELEASE.json dir is live for neither the doctor nor release.py live_ids. Size: SMALL.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dadaia_workspace.core import release_state
from dadaia_workspace.core.gitflow import DEFAULT, work_branch
from dadaia_workspace.features.specs.doctor_common import resolve_active_release

sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                       / "dadaia_workspace/public/skills/dd-bug-resolution/scripts"))  # fmt: skip
import _grammar  # noqa: E402

_DOC = '{"schema": "release-state-v1", "release": "1.0.0", "phase": "IMPLEMENTATION"}'


def test_canonical_filename_is_underscore_release_json() -> None:
    assert release_state.RELEASE_STATE_FILENAME == "_RELEASE.json"


def test_a_legacy_state_file_makes_no_release_live(tmp_path: Path) -> None:
    """The ONE live reader, the doctor and `live_ids` agree; two live dirs are an error."""
    (tmp_path / "releases" / "1.0.0").mkdir(parents=True)
    (tmp_path / "releases" / "1.0.0" / "RELEASE.json").write_text(_DOC, encoding="utf-8")
    assert (resolve_active_release(tmp_path), _grammar.live_ids(tmp_path)) == (
        (None, None),
        [],
    )
    (tmp_path / "releases" / "1.0.0" / "_RELEASE.json").write_text(_DOC, encoding="utf-8")
    assert (resolve_active_release(tmp_path), _grammar.live_ids(tmp_path)) == (
        ("1.0.0", "IMPLEMENTATION"),
        ["1.0.0"],
    )
    (tmp_path / "releases" / "3.0.0").mkdir()
    (tmp_path / "releases" / "3.0.0" / "_RELEASE.json").write_text(_DOC, encoding="utf-8")
    assert (work_branch(tmp_path, DEFAULT), len(_grammar.live_ids(tmp_path))) == (
        "feature/0.1.0",
        2,
    )
