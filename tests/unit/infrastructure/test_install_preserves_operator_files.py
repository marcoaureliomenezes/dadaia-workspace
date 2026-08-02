"""An operator's own rule/agent/skill must survive a routine ``public install``.

Bug ``claude-install-prunes-operator-authored-files``: ``copy_tree`` pruned every
projected file absent from staging, and an operator-authored file is *always* absent
from staging. So writing your own ``.claude/rules/my-own.md`` and then running a plain
``dadaia public install`` silently deleted it — the same data-loss class that
``settings.json`` was fixed for, on the directory projections instead of the file.

The ownership boundary is: dadaia may prune only what dadaia previously projected. That
is what the projection ledger records; a file dadaia never wrote is never dadaia's to
delete. The complementary half — a genuinely stale lib projection IS still pruned — is
covered by ``test_install_prune.py`` and must stay green.
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
    return ws


@pytest.mark.parametrize(
    ("group", "relative", "body"),
    [
        ("rules", "my-own-rule.md", "# my own rule\n\nOperator law.\n"),
        ("agents", "my-own-agent.md", "---\nname: my-own-agent\n---\n\nMine.\n"),
        ("skills", "my-own-skill/SKILL.md", "---\nname: my-own-skill\n---\n\nMine.\n"),
    ],
)
def test_install_does_not_delete_operator_authored_claude_files(
    workspace: Path, group: str, relative: str, body: str
) -> None:
    manager = FileSystemPublicAssetManager()
    manager.stage(workspace)
    manager.install(workspace, target="claude")

    mine = workspace / ".claude" / group / relative
    mine.parent.mkdir(parents=True, exist_ok=True)
    mine.write_text(body, encoding="utf-8")

    installed = manager.install(workspace, target="claude")

    assert mine.exists(), (
        f".claude/{group}/{relative} was authored by the operator and is not "
        "lib-originated — install must never delete it"
    )
    assert mine.read_text(encoding="utf-8") == body, "operator content must be untouched"
    assert not any("[prune]" in line and relative in line for line in installed)
