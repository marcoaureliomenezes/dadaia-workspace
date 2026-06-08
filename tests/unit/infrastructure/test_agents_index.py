"""T-016-00: agents.index.json pre-compilation for the SDD gate RULE D."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.install_helpers import build_agents_index
from dadaia_workspace.infrastructure.public_assets import _parse_write_allowlist

_AGENT_WITH_WL = """---
name: my-agent
model: claude-sonnet-4-6
paths:
  write_allowlist:
    - specs/releases/<ctx>/**
    - .dadaia/reports/<ctx>/my-agent/**
  read_allowlist:
    - specs/**
---
# Body
"""

_AGENT_NO_WL = """---
name: bare-agent
model: claude-sonnet-4-6
---
# Body
"""


def test_parse_write_allowlist_extracts_only_write_globs() -> None:
    wl = _parse_write_allowlist(_AGENT_WITH_WL)
    assert wl == ["specs/releases/<ctx>/**", ".dadaia/reports/<ctx>/my-agent/**"]


def test_parse_write_allowlist_empty_when_absent() -> None:
    assert _parse_write_allowlist(_AGENT_NO_WL) == []


def test_parse_write_allowlist_no_frontmatter() -> None:
    assert _parse_write_allowlist("# just a body, no frontmatter") == []


def test_build_agents_index_maps_every_agent(tmp_path: Path) -> None:
    agentic_dir = tmp_path / ".dadaia" / "agentic"
    agents_dir = agentic_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "my-agent.md").write_text(_AGENT_WITH_WL, encoding="utf-8")
    (agents_dir / "bare-agent.md").write_text(_AGENT_NO_WL, encoding="utf-8")

    index = build_agents_index(agentic_dir)

    assert set(index) == {"my-agent", "bare-agent"}
    assert index["my-agent"] == ["specs/releases/<ctx>/**", ".dadaia/reports/<ctx>/my-agent/**"]
    assert index["bare-agent"] == []


def test_build_agents_index_empty_when_no_agents_dir(tmp_path: Path) -> None:
    agentic_dir = tmp_path / ".dadaia" / "agentic"
    agentic_dir.mkdir(parents=True)
    assert build_agents_index(agentic_dir) == {}
