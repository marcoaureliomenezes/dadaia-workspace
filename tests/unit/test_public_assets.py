"""Unit tests for public asset staging and runtime projections."""

import json
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def test_stage_creates_agentic_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()

    manager.stage(workspace)

    manifest_path = workspace / ".dadaia" / "agentic" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1"
    assert any(asset["path"] == "data/AGENTS.md" for asset in manifest["assets"])


def test_install_all_projects_runtime_assets(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()

    manager.install(workspace, target="all")

    assert (workspace / "AGENTS.md").exists()
    assert (workspace / ".agents" / "skills" / "dadaia-grill-me" / "SKILL.md").exists()
    assert (workspace / ".claude" / "agents" / "software-architect.md").exists()
    assert (workspace / ".codex" / "hooks.json").exists()
    assert (workspace / ".codex" / "config.toml").exists()
    assert (workspace / ".codex" / "rules" / "dadaia-workspace-dev-guardrail.md").exists()
    assert (workspace / ".opencode" / "commands" / "spec-context.md").exists()
    assert (workspace / "opencode.json").exists()


def test_install_preserves_existing_files_without_force(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    agents_md = workspace / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text("custom\n", encoding="utf-8")

    FileSystemPublicAssetManager().install(workspace, target="all")

    assert agents_md.read_text(encoding="utf-8") == "custom\n"


def test_install_overwrites_existing_files_with_force(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    agents_md = workspace / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text("custom\n", encoding="utf-8")

    FileSystemPublicAssetManager().install(workspace, target="all", force=True)

    assert agents_md.read_text(encoding="utf-8").startswith("# dadaia Labs")


_CLASSIFY_WORKFLOWS_CASES = [
    {
        "id": "codex_linear",
        "content": "# linear workflow\nstep: do_something\n",
        "expected_in": ["[not-applicable] codex:workflows/sample.workflow.md (no workflow runtime)"],
        "expected_not_in": ["[partial] opencode:workflows/sample.workflow.md"],
    },
    {
        "id": "codex_parallel",
        "content": "# parallel workflow\nparallel_group: batch_a\nstep: do_something\n",
        "expected_in": ["[not-applicable] codex:workflows/sample.workflow.md (no workflow runtime)"],
        "expected_not_in": ["[ok] opencode:workflows/sample.workflow.md"],
    },
    {
        "id": "opencode_linear",
        "content": "# linear workflow\nstep: do_something\n",
        "expected_in": ["[ok] opencode:workflows/sample.workflow.md"],
        "expected_not_in": ["[partial] opencode:workflows/sample.workflow.md"],
    },
    {
        "id": "opencode_parallel",
        "content": "# parallel workflow\nparallel_group: batch_a\nstep: do_something\n",
        "expected_in": ["[partial] opencode:workflows/sample.workflow.md (parallel_group sequentially)"],
        "expected_not_in": ["[ok] opencode:workflows/sample.workflow.md"],
    },
]


@pytest.mark.parametrize("case", _CLASSIFY_WORKFLOWS_CASES, ids=[str(c["id"]) for c in _CLASSIFY_WORKFLOWS_CASES])
def test_classify_workflows_quadrants(tmp_path: Path, case: dict) -> None:  # type: ignore[type-arg]
    agentic_dir = tmp_path / "agentic"
    workflows_dir = agentic_dir / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "sample.workflow.md").write_text(case["content"], encoding="utf-8")

    result = FileSystemPublicAssetManager()._classify_workflows(agentic_dir)  # noqa: SLF001

    for expected in case["expected_in"]:
        assert expected in result, f"Expected {expected!r} in result; got {result}"
    for not_expected in case["expected_not_in"]:
        assert not_expected not in result, f"Did not expect {not_expected!r} in result; got {result}"
