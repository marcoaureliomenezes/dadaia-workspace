"""``public doctor`` must never stay silent about a file it does not manage.

Bug ``claude-doctor-blind-to-unmanaged-projection-files``: doctor walked
staging→projection only, so a file present in ``.claude/rules`` but absent from staging
produced no line at all. The rules corpus is loaded into every session's context, so an
unmanaged file there is an instruction-injection surface — and after the ownership fix
for ``claude-install-prunes-operator-authored-files`` such a file also survives installs
forever. Silence is the wrong answer in both directions.

Exit code stays 0 deliberately. The Workspace Root Law's operator exception makes an
operator-authored rule/agent/skill *legitimate*, so failing on it would make doctor-green
unreachable for a workspace that uses the exception as designed. The contract enforced
here is weaker but honest: doctor SEES and NAMES every unmanaged file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(ws)
    manager = FileSystemPublicAssetManager()
    manager.stage(ws)
    manager.install(ws, target="claude")
    return ws


def test_a_clean_projection_reports_no_unmanaged_file(workspace: Path) -> None:
    lines = FileSystemPublicAssetManager().doctor(workspace)
    assert not [line for line in lines if "unmanaged" in line], (
        "a freshly installed projection has no unmanaged files; a check that fires here "
        "would be noise the operator learns to ignore"
    )


@pytest.mark.parametrize(
    ("group", "relative"),
    [
        ("rules", "smuggled.md"),
        ("agents", "smuggled.md"),
        ("skills", "smuggled/SKILL.md"),
    ],
)
def test_doctor_names_an_unmanaged_file_in_the_claude_projection(
    workspace: Path, group: str, relative: str
) -> None:
    planted = workspace / ".claude" / group / relative
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_text("---\nname: smuggled\n---\n\nNot from staging.\n", encoding="utf-8")

    lines = FileSystemPublicAssetManager().doctor(workspace)

    named = [line for line in lines if "unmanaged" in line and relative.split("/")[0] in line]
    assert named, (
        f"doctor said nothing about .claude/{group}/{relative}, which is loaded into "
        f"every session's context but is not lib-originated. Lines were: {lines}"
    )
