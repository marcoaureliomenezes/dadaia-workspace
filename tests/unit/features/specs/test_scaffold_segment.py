"""scaffold_release_segment — alpha-N/rc-N segment scaffolding (T-ENG-02, ADR-5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs.scaffolder import scaffold_release_segment


@pytest.mark.parametrize(
    ("version", "segment"),
    [
        pytest.param("v0.1.6", "alpha-1", id="alpha-segment-creates-spec-plan-tasks"),
        pytest.param("v0.2.0", "rc-2", id="rc-segment-creates-tasks"),
    ],
)
def test_creates_spec_plan_tasks_under_segment(tmp_path: Path, version: str, segment: str) -> None:
    res = scaffold_release_segment(tmp_path, version, segment)
    seg = tmp_path / "releases" / version / segment
    assert (seg / "SPEC.md").is_file()
    assert (seg / "PLAN.md").is_file()
    assert (seg / "TASKS.md").is_file()
    assert res.errors == []
    assert len(res.created) == 3
    spec = (seg / "SPEC.md").read_text()
    assert f"**Segment:** {segment}" in spec
    assert f"**Release ID:** {version}" in spec


@pytest.mark.parametrize(
    ("version", "segment", "match"),
    [
        pytest.param("0.1.6", "alpha-1", "SemVer", id="rejects-non-semver-version"),
        pytest.param("v0.1.6", "alpha1", "segment", id="rejects-malformed-segment-alpha1"),
        pytest.param("v0.1.6", "alpha", "segment", id="rejects-malformed-segment-alpha"),
        pytest.param("v0.1.6", "beta-1", "segment", id="rejects-malformed-segment-beta"),
        pytest.param("v0.1.6", "rc1", "segment", id="rejects-malformed-segment-rc1"),
        pytest.param("v0.1.6", "alpha-", "segment", id="rejects-malformed-segment-alpha-trailing"),
        pytest.param("v0.1.6", "rc-x", "segment", id="rejects-malformed-segment-rc-x"),
    ],
)
def test_rejects_invalid_input(tmp_path: Path, version: str, segment: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        scaffold_release_segment(tmp_path, version, segment)
