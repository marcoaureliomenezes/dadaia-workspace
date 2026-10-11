"""AC11.1: a staged skill holds no copy of another skill's kernel, schema or privacy file.

Size: MEDIUM (a real `public stage` into a temp dir; each entry point run as a subprocess).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure import public_assets
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

pytestmark = pytest.mark.slow(reason="real public stage into a temp dir + subprocess runs")

_OWNER = "dd-bug-resolution"
_KERNEL = [
    "_atomic",
    "_git",
    "_refusal",
    "_clock",
    "_platform",
    "_root",
    "_grammar",
    "_jsonl",
    "_commit",
    "_findings",
]
_NEVER_COPIED = ["_ledger.py", "_specs.py", "_privacy.py", "privacy_baseline.json"]
_SCHEMAS = [
    "bug-record-v1",
    "backlog-v1",
    "histo-record-v1",
    "release-state-v1",
    "finding-record-v1",
]

_SRC_SKILLS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "skills"

# The stage's input names the entry points: a script with a `__main__` block, no leading `_`.
_ENTRY_POINTS = sorted(
    p.relative_to(_SRC_SKILLS).as_posix()
    for p in _SRC_SKILLS.glob("*/scripts/*.py")
    if not p.name.startswith("_") and "__main__" in p.read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def skills(tmp_path_factory: pytest.TempPathFactory) -> Path:
    ws = tmp_path_factory.mktemp("no-shared-copies")
    FileSystemPublicAssetManager().stage(ws)
    return ws / ".dadaia" / "agentic" / "skills"


def _outside_owner(skills: Path, name: str) -> list[str]:
    return sorted(
        p.relative_to(skills).as_posix()
        for p in skills.rglob(name)
        if p.relative_to(skills).parts[0] != _OWNER
    )


def test_no_skill_but_the_owner_holds_a_kernel_or_privacy_file(skills: Path) -> None:
    names = [*_NEVER_COPIED, *(f"{m}.py" for m in _KERNEL)]
    assert {n: _outside_owner(skills, n) for n in names if _outside_owner(skills, n)} == {}


@pytest.mark.parametrize("schema", _SCHEMAS)
def test_each_moved_schema_exists_once_under_skills(schema: str, skills: Path) -> None:
    found = sorted(p.relative_to(skills).as_posix() for p in skills.rglob(f"{schema}.schema.json"))
    assert len(found) == 1, found


@pytest.mark.parametrize("table", ["_SKILL_SCRIPT_SHARED", "_SKILL_SCRIPT_SCHEMAS"])
def test_public_assets_defines_no_copy_table(table: str) -> None:
    assert not hasattr(public_assets, table)


def test_entry_points_were_found() -> None:
    assert len(_ENTRY_POINTS) > 5


@pytest.mark.parametrize("rel", _ENTRY_POINTS)
def test_entry_point_help_runs_with_a_clean_sys_path(
    rel: str, skills: Path, tmp_path: Path
) -> None:
    done = subprocess.run(
        [sys.executable, "-I", "-B", str(skills / rel), "--help"],
        cwd=tmp_path,
        env={},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-600:]
