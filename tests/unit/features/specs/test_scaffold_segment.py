"""scaffold_release_segment — alpha-N/rc-N segment scaffolding (T-ENG-02, ADR-5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs.scaffolder import scaffold_release_segment


def test_creates_spec_plan_tasks_under_segment(tmp_path: Path) -> None:
    res = scaffold_release_segment(tmp_path, "v0.1.6", "alpha-1")
    seg = tmp_path / "releases" / "v0.1.6" / "alpha-1"
    assert (seg / "SPEC.md").is_file()
    assert (seg / "PLAN.md").is_file()
    assert (seg / "TASKS.md").is_file()
    assert res.errors == []
    assert len(res.created) == 3
    spec = (seg / "SPEC.md").read_text()
    assert "**Segment:** alpha-1" in spec
    assert "**Release ID:** v0.1.6" in spec


def test_rc_segment(tmp_path: Path) -> None:
    scaffold_release_segment(tmp_path, "v0.2.0", "rc-2")
    assert (tmp_path / "releases" / "v0.2.0" / "rc-2" / "TASKS.md").is_file()


def test_rejects_non_semver_version(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SemVer"):
        scaffold_release_segment(tmp_path, "0.1.6", "alpha-1")


@pytest.mark.parametrize("bad", ["alpha1", "alpha", "beta-1", "rc1", "alpha-", "rc-x"])
def test_rejects_malformed_segment(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ValueError, match="segment"):
        scaffold_release_segment(tmp_path, "v0.1.6", bad)


def test_skip_then_force_overwrite(tmp_path: Path) -> None:
    scaffold_release_segment(tmp_path, "v0.1.6", "alpha-1")
    spec = tmp_path / "releases" / "v0.1.6" / "alpha-1" / "SPEC.md"
    spec.write_text("EDITED", encoding="utf-8")

    res_skip = scaffold_release_segment(tmp_path, "v0.1.6", "alpha-1", force=False)
    assert spec in res_skip.skipped
    assert spec.read_text() == "EDITED"

    res_force = scaffold_release_segment(tmp_path, "v0.1.6", "alpha-1", force=True)
    assert spec in res_force.created
    assert "EDITED" not in spec.read_text()
