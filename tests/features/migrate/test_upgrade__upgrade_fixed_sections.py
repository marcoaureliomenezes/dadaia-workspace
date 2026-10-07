"""T-048-05 (SPEC 0.4.8 AC4.3, R6): ``specs upgrade`` on a v6 tree ends
stamped canonical WITH its fixed law sections, so the specs doctor reports 0 errors — the S3 dead
end (upgrade said "no-op", doctor said FIXED-1) is gone. 0.5.0 WP-14: the repair is the
doctor's one writer, so the seam is the `specs upgrade` verb. Size: SMALL (CliRunner)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core import specs_version
from dadaia_workspace.core.fixed_sections import FIXED_SECTIONS
from dadaia_workspace.core.gitflow import merge_frontmatter
from dadaia_workspace.features.specs import SpecsDoctor, canon

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
#: specs/bugs/AGENTS.md as published at 570af642 (its sha256 is in shipped-hashes.json).
_SHIPPED_BUGS_LAW = Path(__file__).resolve().parents[2] / "fixtures/shipped/bugs-AGENTS.570af642.md"
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
    merge_frontmatter(specs, specs_pattern_version=6)
    return specs


@pytest.mark.medium
def test_a_v6_tree_ends_canonical_with_fixed_sections_and_a_clean_doctor(tmp_path: Path) -> None:
    """sa-specs-upgrade-writes-through-symlinks#B3, sa-specs-upgrade-writes-through-symlinks#B4: the hop, then the doctor's repair set — a superseded shipped scoped
    law (a real published specs/bugs/AGENTS.md) is refreshed too: no TREE-5, no FIXED."""
    specs = _v6_tree(tmp_path)
    (specs / "bugs" / "AGENTS.md").write_bytes(_SHIPPED_BUGS_LAW.read_bytes())

    result = CliRunner().invoke(app, ["specs", "upgrade", "--specs-dir", str(specs)])

    assert result.exit_code == 0, result.output
    assert specs_version.state(specs)[0] == "canonical"
    for rel, _ in FIXED_SECTIONS:
        assert f"fix FIXED-1 {specs / rel}" in result.output
    issues = SpecsDoctor(specs, public_dir=_PUBLIC, templates_dir=_PUBLIC / "templates").check()
    assert [i.code for i in issues if i.code == "TREE-5" or i.code.startswith("FIXED")] == []
    assert [i for i in issues if i.verdict == "error"] == []


def test_dry_run_plans_the_fixed_sections_and_writes_nothing(tmp_path: Path) -> None:
    specs = _v6_tree(tmp_path)
    before = {p: p.read_bytes() for p in specs.rglob("*") if p.is_file()}

    result = CliRunner().invoke(app, ["specs", "upgrade", "--specs-dir", str(specs), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert result.output.count("would fix FIXED-1") == len(FIXED_SECTIONS)
    assert {p: p.read_bytes() for p in specs.rglob("*") if p.is_file()} == before
