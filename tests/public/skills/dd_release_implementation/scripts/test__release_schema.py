"""sa-release-id-has-three-grammars: a release id has ONE grammar, the
script's bare M.m.p (`_release_schema.SEMVER_RE`); core consults it; archived dirs are
exempt by location. Size: SMALL.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.release_state import RELEASE_ID_RE
from dadaia_workspace.features.specs.canon import is_canon_path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SCRIPTS = _REPO_ROOT / "dadaia_workspace/public/skills/dd-release-implementation/scripts"
sys.path.insert(0, str(_SCRIPTS))
import _release_schema  # noqa: E402


@pytest.mark.parametrize(
    ("release_id", "legal"),
    [
        ("0.5.0", True),
        ("10.20.30", True),
        ("0.5.0-rc1", False),
        ("v0.5.0", False),
        ("1.2", False),
        ("1.2.3-", False),
        ("next", False),
    ],  # fmt: skip
)
def test_one_release_id_grammar_everywhere(tmp_path: Path, release_id: str, legal: bool) -> None:
    """sa-release-id-has-three-grammars and sa-release-json-validated-three-times#B5: core,
    the canon and `release.py new` agree on every id — a suffix and a `v` are refused."""
    assert RELEASE_ID_RE.pattern == _release_schema.SEMVER_RE.pattern
    assert bool(RELEASE_ID_RE.match(release_id)) is legal
    assert is_canon_path(f"releases/{release_id}/rc-1/SPEC.md") is legal
    (tmp_path / "specs" / "releases").mkdir(parents=True)
    new = subprocess.run([sys.executable, str(_SCRIPTS / "release.py"), "new", release_id,
                          "--specs", str(tmp_path / "specs")], capture_output=True, text=True)  # fmt: skip
    assert (new.returncode == 0) is legal, new.stderr
