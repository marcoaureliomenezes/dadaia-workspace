"""Intent: CONTRACT — 0.4.6 AC12 (FR14/D14: the zone and canon tables are rendered from the
registry at ``public stage``); size: SMALL.

The two ``.dadaia/**`` law fragments carry placeholders; ``stage`` fills them from
``core.workspace_layout`` before the manifest hashes the staged bytes. The pure renderer is
pinned here (row shape, placeholder absence, untouched text); the ratchet in
``tests/contract/test_zone_registry.py`` pins the staged bytes against the registry row for
row.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.core.workspace_layout import DADAIA_ZONES, STATES_CANON
from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    render_registry_tables,
)

pytestmark = pytest.mark.unit

_PLACEHOLDERS = ("<!-- zones -->", "<!-- canon -->")


def test_zones_placeholder_renders_one_row_per_zone() -> None:
    out = render_registry_tables("before\n<!-- zones -->\nafter\n")
    rows = [line for line in out.splitlines() if line.startswith("| `")]
    assert len(rows) == len(DADAIA_ZONES) == 11
    assert rows[0] == (
        "| `agentic/` | staged public assets + manifest.json | projection | never | install |"
    )
    assert "| `tmp/` | scratch + evidence | ephemeral | 86400 | runtime |" in rows
    assert out.startswith("before\n| Zone | Purpose | Class | TTL | Creator |\n|---|")
    assert out.endswith(
        "| operator |\n| `.venv/` | workspace venv; never scanned | managed | never | init |\nafter\n"
    )


def test_canon_placeholder_renders_the_closed_canon_sorted() -> None:
    out = render_registry_tables("<!-- canon -->")
    header, rule, *rows = out.splitlines()
    assert header == "| Entry |" and rule == "|---|"
    assert [row.strip("| `") for row in rows] == sorted(STATES_CANON)
    assert len(rows) == 11


def test_text_without_placeholders_is_returned_unchanged() -> None:
    assert render_registry_tables("# plain\n| a | b |\n") == "# plain\n| a | b |\n"


def test_stage_renders_every_data_fragment_before_the_manifest_hashes_it(
    tmp_path: Path,
) -> None:
    FileSystemPublicAssetManager().stage(tmp_path)
    agentic = tmp_path / ".dadaia" / "agentic"
    fragments = sorted((agentic / "data").glob("*.md"))
    assert fragments
    leftovers = [
        p.name for p in fragments if any(ph in p.read_text("utf-8") for ph in _PLACEHOLDERS)
    ]
    assert not leftovers
    manifest = json.loads((agentic / "manifest.json").read_text("utf-8"))
    recorded = {a["path"]: a["sha256"] for a in manifest["assets"]}
    for name in ("dadaia-AGENTS.md", "states-AGENTS.md"):
        rendered = agentic / "data" / name
        assert recorded[f"data/{name}"] == hashlib.sha256(rendered.read_bytes()).hexdigest()
