"""T-016-00: agents.index.json pre-compilation for the SDD gate RULE D."""

from __future__ import annotations

from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            _AGENT_WITH_WL,
            ["specs/releases/<ctx>/**", ".dadaia/reports/<ctx>/my-agent/**"],
            id="extracts-only-write-globs",
        ),
        pytest.param(_AGENT_NO_WL, [], id="empty-when-absent"),
        pytest.param("# just a body, no frontmatter", [], id="no-frontmatter"),
    ],
)
def test_parse_write_allowlist(text: str, expected: list[str]) -> None:
    assert _parse_write_allowlist(text) == expected


def test_build_agents_index_maps_every_agent_and_empty_when_no_dir(tmp_path: Path) -> None:
    agentic_dir = tmp_path / ".dadaia" / "agentic"
    agents_dir = agentic_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "my-agent.md").write_text(_AGENT_WITH_WL, encoding="utf-8")
    (agents_dir / "bare-agent.md").write_text(_AGENT_NO_WL, encoding="utf-8")

    index = build_agents_index(agentic_dir)

    assert set(index) == {"my-agent", "bare-agent"}
    assert index["my-agent"] == ["specs/releases/<ctx>/**", ".dadaia/reports/<ctx>/my-agent/**"]
    assert index["bare-agent"] == []

    empty_agentic_dir = tmp_path / "empty" / ".dadaia" / "agentic"
    empty_agentic_dir.mkdir(parents=True)
    assert build_agents_index(empty_agentic_dir) == {}
