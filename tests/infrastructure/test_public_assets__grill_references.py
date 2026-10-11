"""AC1.4 (rc-14 J8): `public install` projects the stage references and the report CSS of
`dd-grill-me`. Size: MEDIUM (a real install into tmp_path).

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

pytestmark = pytest.mark.slow(reason="public asset install writes projected workspace files")

_GRILL_FILES = (
    "references/backlog.md",
    "references/release.md",
    "references/adr.md",
    "references/plan.md",
    "scripts/report.css",
)


def test_install_projects_the_grill_references_and_report_css(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / ".dadaia" / "states").mkdir(parents=True)

    FileSystemPublicAssetManager().install(workspace_root, harness="claude")

    skill = workspace_root / ".claude" / "skills" / "dd-grill-me"
    assert [rel for rel in _GRILL_FILES if not (skill / rel).is_file()] == []
