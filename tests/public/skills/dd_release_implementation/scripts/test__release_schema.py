"""sa-release-id-has-three-grammars: a release id has ONE grammar, the
script's bare M.m.p (`_release_schema.SEMVER_RE`); core consults it; archived dirs are
exempt by location. Size: SMALL.
"""

from __future__ import annotations

import os
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


def test_the_release_instant_reader_reads_an_instant_with_no_offset_as_utc() -> None:
    """bug-balance-cuts-a-non-utc-closure-day-to-local (redo of 3fdfebebc): `_utc` reads every
    instant in UTC — an offset converts, `Z` and `+00:00` are UTC, no offset is UTC and never
    the host's zone (run on a host three hours behind UTC), a malformed one raises ValueError."""
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]); import _release_schema as r\n"
        "for ts in sys.argv[2:]:\n"
        "    try: print(r.utc(ts).isoformat())\n"
        "    except ValueError: print('ValueError')\n"
    )  # fmt: skip
    instants = ["2026-10-06T23:30:00", "2026-10-06T23:30:00Z", "2026-10-06T23:30:00+00:00",
                "2026-10-06T23:30:00-03:00", "not-a-timestamp", ""]  # fmt: skip
    env = {**os.environ, "TZ": "UTC+3"}
    out = subprocess.run([sys.executable, "-c", probe, str(_SCRIPTS), *instants],
                         capture_output=True, text=True, env=env, check=True)  # fmt: skip
    assert out.stdout.split() == ["2026-10-06T23:30:00+00:00"] * 3 + ["2026-10-07T02:30:00+00:00"] + ["ValueError"] * 2  # fmt: skip


@pytest.mark.parametrize("task_id", ["J2.T3", "J2.S1.T3"], ids=["current", "historical"])
def test_a_job_accepts_both_supported_task_id_shapes(task_id: str) -> None:
    job = (
        "# Job 2\n\n"
        "| task | AC | `W:` | outcome |\n"
        "|---|---|---|---|\n"
        f"| {task_id} | AC2.1 | `src/x.py` | parser owner |\n"
    )

    assert _release_schema.job_errors(job, "tasks/job2.md") == []
