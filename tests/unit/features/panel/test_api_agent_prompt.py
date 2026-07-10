"""Unit tests for GET /api/agents/<id>/prompt.

Panel auth removed by operator decision 2026-06-11 — these are view-level unit
tests (no HTTP credential); the no-auth + Host-guard handler contract is pinned
in test_no_auth_contract.py.

Internals (``_AGENT_ID_RE``, ``_strip_frontmatter``) are exercised only through
the executed view path — no direct micro-unit tests of the regex/stripper in
isolation (the golden also pins prompt 200/400/404 bodies).

Three survivors:
  1. View happy 200 shape + frontmatter stripped.
  2. View 400 param (bad chars, .., absolute, symlink escape) + content-type.
  3. View 404 valid-id-no-file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.agent import AgentPromptResult
from dadaia_workspace.features.agents.reader import FileSystemAgentsProvider
from dadaia_workspace.features.panel.views.api_agents import render_api_agent_prompt

pytestmark = pytest.mark.unit


def _write_agent(agents_dir: Path, agent_id: str, body: str = "You are a test agent.") -> Path:
    """Write a minimal agent .md file to agents_dir and return its path."""
    content = f"---\nname: {agent_id}\ndescription: Test agent.\nmodel: claude-test\n---\n\n{body}"
    path = agents_dir / f"{agent_id}.md"
    path.write_text(content, encoding="utf-8")
    return path


class _FakeService:
    """Minimal fake of PanelService exposing ``workspace_root`` + ``get_agent_prompt``.

    ``get_agent_prompt`` delegates to the real ``FileSystemAgentsProvider`` so the
    view tests still exercise genuine prompt resolution, traversal defence, and
    not-found behavior through the executed path.
    """

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    def get_agent_prompt(self, agent_id: str) -> AgentPromptResult:
        return FileSystemAgentsProvider().get_prompt(agent_id, self._workspace_root)


def _make_view(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build the view callable with agents in a temp dir."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(agents_dir))
    _write_agent(agents_dir, "software-engineer", body="You implement code.")
    service = _FakeService(workspace_root=tmp_path)
    return render_api_agent_prompt(service)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. View happy 200 shape + frontmatter stripped
# ---------------------------------------------------------------------------


def test_happy_path_200_shape_and_frontmatter_stripped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    view = _make_view(tmp_path, monkeypatch)
    status, content_type, body = view(agent_id="software-engineer")

    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert data["agent_id"] == "software-engineer"
    assert "system_prompt" in data
    assert "source_path" in data
    assert "You implement code." in data["system_prompt"]
    assert "name:" not in data["system_prompt"]
    assert "---" not in data["system_prompt"]


# ---------------------------------------------------------------------------
# 2. View 400 param (bad chars, .., absolute, symlink escape) + content-type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "agent_id",
    [
        pytest.param("agent.md", id="dot-in-id"),
        pytest.param("..", id="double-dot"),
        pytest.param("/etc/passwd", id="absolute-path"),
        pytest.param("../../etc/passwd", id="relative-traversal"),
        pytest.param("SoftwareEngineer", id="uppercase-rejected"),
        pytest.param("agent name", id="space-rejected"),
        pytest.param("", id="empty-string"),
    ],
)
def test_invalid_id_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, agent_id: str
) -> None:
    view = _make_view(tmp_path, monkeypatch)
    status, content_type, body = view(agent_id=agent_id)

    assert status == 400
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert data["error"] == "invalid_agent_id"

    # Only run the shared symlink-escape check once (independent of the id row above):
    # a symlink inside the agents dir that resolves outside it is rejected as 400
    # (defence-in-depth Path.resolve().is_relative_to(base) check).
    if agent_id != "agent.md":
        return

    agents_dir = tmp_path / "agents"
    outside = tmp_path / "outside.md"
    outside.write_text(
        "---\nname: evil-link\ndescription: outside\n---\n\nEvil prompt.", encoding="utf-8"
    )
    (agents_dir / "evil-link.md").symlink_to(outside)

    service = _FakeService(workspace_root=tmp_path)
    symlink_view = render_api_agent_prompt(service)  # type: ignore[arg-type]

    symlink_status, symlink_content_type, symlink_body = symlink_view(agent_id="evil-link")
    assert symlink_status == 400
    assert symlink_content_type == "application/json; charset=utf-8"
    symlink_data = json.loads(symlink_body)
    assert symlink_data["error"] == "invalid_agent_id"


# ---------------------------------------------------------------------------
# 3. View 404 valid-id-no-file
# ---------------------------------------------------------------------------


def test_valid_id_no_matching_file_returns_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    view = _make_view(tmp_path, monkeypatch)
    status, content_type, body = view(agent_id="nonexistent-agent")

    assert status == 404
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert data["error"] == "not_found"
