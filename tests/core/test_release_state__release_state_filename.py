"""`_RELEASE.json` is the one state filename, decided by core.release_state; a legacy
RELEASE.json dir is live for neither the doctor nor release.py live_ids. Size: SMALL.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

from dadaia_workspace.core import release_state
from dadaia_workspace.core.gitflow import live_release_id
from dadaia_workspace.features.specs.doctor_common import resolve_active_release

sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                       / "dadaia_workspace/public/skills/dd-bug-resolution/scripts"))  # fmt: skip
import _grammar

from tests.helpers.oslib import read_text, write_text

_DOC = json.dumps({"schema": "release-state-v1", "release": "1.0.0", "phase": "IMPLEMENTATION",
                   "defined": None, "implemented": None, "shipped": None, "log": []})  # fmt: skip


def test_canonical_filename_is_underscore_release_json() -> None:
    assert release_state.RELEASE_STATE_FILENAME == _grammar.STATE == "_RELEASE.json"


def test_the_package_spells_the_state_filename_nowhere() -> None:
    """The kernel's `STATE` is the one spelling; the package reads it, never retypes it."""
    package = Path(__file__).resolve().parents[2] / "dadaia_workspace"
    spelled = [
        p.relative_to(package).as_posix()
        for p in package.rglob("*.py")
        if "public" not in p.relative_to(package).parts[:1]
        and any(
            isinstance(n, ast.Constant) and n.value == "_RELEASE.json"
            for n in ast.walk(ast.parse(read_text(p)))
        )
    ]
    assert spelled == []


def test_a_legacy_state_file_makes_no_release_live(tmp_path: Path) -> None:
    """The ONE live reader, the doctor and `live_ids` agree; two live dirs are an error."""
    (tmp_path / "releases" / "1.0.0").mkdir(parents=True)
    write_text(tmp_path / "releases" / "1.0.0" / "RELEASE.json", _DOC)
    assert (resolve_active_release(tmp_path), _grammar.live_ids(tmp_path)) == (
        (None, None),
        [],
    )
    write_text(tmp_path / "releases" / "1.0.0" / "_RELEASE.json", _DOC)
    assert (resolve_active_release(tmp_path), _grammar.live_ids(tmp_path)) == (
        ("1.0.0", "IMPLEMENTATION"),
        ["1.0.0"],
    )
    (tmp_path / "releases" / "3.0.0").mkdir()
    write_text(tmp_path / "releases" / "3.0.0" / "_RELEASE.json", _DOC)
    assert (live_release_id(tmp_path), len(_grammar.live_ids(tmp_path))) == (None, 2)
