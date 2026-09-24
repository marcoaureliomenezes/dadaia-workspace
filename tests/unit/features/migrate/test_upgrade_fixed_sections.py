"""Intent: CONTRACT — T-048-05 (SPEC 0.4.8 AC4.3, R6): ``specs upgrade`` on a v6 tree ends
stamped v7 WITH its fixed law sections, so the specs doctor reports 0 errors — the S3 dead
end (upgrade said "no-op", doctor said FIXED-1) is gone. Size: SMALL."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.core import specs_version
from dadaia_workspace.core.fixed_sections import FIXED_SECTIONS
from dadaia_workspace.features.migrate.upgrade import upgrade
from dadaia_workspace.features.specs import SpecsDoctor, canon

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public"
_FIXED_BLOCK = re.compile(
    r"\n*<!-- dadaia:fixed [\w-]+ -->\n.*?<!-- /dadaia:fixed [\w-]+ -->\n", re.S
)


def _v6_tree(tmp_path: Path) -> Path:
    """A 0.4.6-era tree: canon files, stamp 6, no fixed law blocks anywhere."""
    specs = tmp_path / "repo" / "specs"
    canon.scaffold(specs, project_name="v6")
    for rel, _ in FIXED_SECTIONS:
        path = specs / rel
        path.write_text(_FIXED_BLOCK.sub("\n", path.read_text(encoding="utf-8")), encoding="utf-8")
    specs_version.write_pattern_version(specs, 6)
    return specs


def test_a_v6_tree_ends_v7_with_fixed_sections_and_a_clean_doctor(tmp_path: Path) -> None:
    specs = _v6_tree(tmp_path)

    result = upgrade(specs)

    assert specs_version.read_pattern_version(specs) == 7
    assert not result.no_op
    assert sorted(p.relative_to(specs).as_posix() for p in result.fixed_restored) == sorted(
        rel for rel, _ in FIXED_SECTIONS
    )
    issues = SpecsDoctor(specs, public_dir=_PUBLIC, templates_dir=_PUBLIC / "templates").check()
    assert [i.to_dict() for i in issues if i.severity.value == "error"] == []


def test_dry_run_plans_the_fixed_sections_and_writes_nothing(tmp_path: Path) -> None:
    specs = _v6_tree(tmp_path)
    before = {p: p.read_bytes() for p in specs.rglob("*") if p.is_file()}

    result = upgrade(specs, dry_run=True)

    assert len(result.fixed_restored) == len(FIXED_SECTIONS)
    assert {p: p.read_bytes() for p in specs.rglob("*") if p.is_file()} == before
