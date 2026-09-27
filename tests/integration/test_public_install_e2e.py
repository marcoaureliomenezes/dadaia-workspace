"""The rendered ``.dadaia/**`` law fragments (0.4.6 AC12) and no ``.dadaia/scripts``
projection (0.4.6 AC10).

Intent: CONTRACT — 0.4.6 AC12 (FR14) + 0.4.6 AC10 (FR12); size: MEDIUM.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.workspace_layout import DADAIA_ZONES, STATES_CANON
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def _table_rows(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("| `")]


def test_installed_dadaia_agents_md_carries_the_rendered_zone_table(tmp_path: Path) -> None:
    """After ``install()`` the projected ``.dadaia/AGENTS.md`` carries exactly one
    row per registry zone and no placeholder; ``states/AGENTS.md`` carries the closed canon."""
    ws = tmp_path / "ws"
    ws.mkdir()
    FileSystemPublicAssetManager().install(ws)

    zones = (ws / ".dadaia" / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- zones -->" not in zones
    rows = _table_rows(zones)
    assert len(rows) == len(DADAIA_ZONES) == 12
    assert [row.split("|")[1].strip().strip("`").rstrip("/") for row in rows] == [
        zone.name for zone in DADAIA_ZONES
    ]

    states = (ws / ".dadaia" / "states" / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- canon -->" not in states
    assert {row.strip("| `") for row in _table_rows(states)} == STATES_CANON


def test_install_all_projects_no_dadaia_scripts(tmp_path: Path) -> None:
    """0.4.6 AC10 (FR12): ``install()`` creates no ``.dadaia/scripts`` and the
    staged manifest names no such path. Git hooks and CI execute the package copy under
    ``dadaia_workspace/public/scripts/``; only the ``agentic/scripts`` staging survives."""
    ws = tmp_path / "ws"
    ws.mkdir()
    FileSystemPublicAssetManager().install(ws)

    assert not (ws / ".dadaia" / "scripts").exists()
    assert (ws / ".dadaia" / "agentic" / "scripts").is_dir()
    manifest = (ws / ".dadaia" / "agentic" / "manifest.json").read_text(encoding="utf-8")
    assert ".dadaia/scripts" not in manifest
