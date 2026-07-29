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


def test_segment_artifacts_pass_the_workflows_own_gates(tmp_path: Path) -> None:
    """Bug scaffold-artifacts-fail-own-workflow-gates (regression pin): a scaffolded
    segment's PLAN.md satisfies the plan dependency-table lint and the TASKS command
    hygiene lint, and every task line matches the implementation pipeline's marker
    grammar — a template regression must fail HERE, not in a consumer workflow run."""
    from types import SimpleNamespace

    from dadaia_workspace.features.lifecycle.pipeline import _TASK_MARKER_LINE_RES
    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionWorkflow,
    )

    res = scaffold_release_segment(tmp_path, "v0.1.6", "alpha-1")
    assert res.errors == []
    stub = SimpleNamespace(
        _selector=SimpleNamespace(spec_context=SimpleNamespace(specs_dir=tmp_path)),
        _release_id="v0.1.6/alpha-1",
    )
    assert ReleaseDefinitionWorkflow._validate_plan_dependency_table(stub) is None
    stub._unreadable_task_markers_block = lambda text: (
        ReleaseDefinitionWorkflow._unreadable_task_markers_block(stub, text)
    )
    assert ReleaseDefinitionWorkflow._validate_tasks_command_hygiene(stub) is None

    tasks_text = (tmp_path / "releases" / "v0.1.6" / "alpha-1" / "TASKS.md").read_text(
        encoding="utf-8"
    )
    task_lines = [ln for ln in tasks_text.splitlines() if ln.lstrip().startswith("- [")]
    assert task_lines, "segment TASKS stub must carry at least one task line"
    for line in task_lines:
        assert any(rx.search(line) for rx in _TASK_MARKER_LINE_RES), line
