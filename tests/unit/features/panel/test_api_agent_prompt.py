"""Unit tests for GET /api/agents/<id>/prompt.

Coverage:
- Happy path: valid agent_id returns 200 with correct shape
- Response shape: agent_id, system_prompt (frontmatter stripped), source_path present
- Invalid id characters: returns 400 (NOT 404)
- Double-dot traversal attempt: returns 400
- Absolute-path-style attempt: returns 400
- Path traversal via symlink that escapes base_dir: returns 400
- 404 on valid id that has no corresponding agent file
- Bearer auth: 401 when missing or wrong token (handler integration test)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.agents.reader import (
    _AGENT_ID_RE,
    AgentNotFoundError,
    InvalidAgentIdError,
    _strip_frontmatter,
    get_prompt,
)
from dadaia_workspace.features.panel.views.api import render_api_agent_prompt

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _write_agent(agents_dir: Path, agent_id: str, body: str = "You are a test agent.") -> Path:
    """Write a minimal agent .md file to agents_dir and return its path."""
    content = f"---\nname: {agent_id}\ndescription: Test agent.\nmodel: claude-test\n---\n\n{body}"
    path = agents_dir / f"{agent_id}.md"
    path.write_text(content, encoding="utf-8")
    return path


class _FakeService:
    """Minimal fake of PanelService exposing the public ``workspace_root``."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root


# ---------------------------------------------------------------------------
# Unit tests: _strip_frontmatter
# ---------------------------------------------------------------------------


class TestStripFrontmatter:
    def test_strips_frontmatter(self) -> None:
        text = "---\nname: foo\n---\n\n# Hello\n\nWorld."
        result = _strip_frontmatter(text)
        assert result == "# Hello\n\nWorld."

    def test_no_frontmatter_returns_text(self) -> None:
        text = "# Just a heading\n\nSome content."
        result = _strip_frontmatter(text)
        assert result == text.strip()

    def test_frontmatter_only_returns_empty(self) -> None:
        text = "---\nname: foo\n---\n"
        result = _strip_frontmatter(text)
        assert result == ""

    def test_unclosed_frontmatter_returns_text(self) -> None:
        """When the closing delimiter is absent, the full text is returned."""
        text = "---\nname: foo\nno closing delimiter"
        result = _strip_frontmatter(text)
        assert result == text.strip()


# ---------------------------------------------------------------------------
# Unit tests: _AGENT_ID_RE validation
# ---------------------------------------------------------------------------


class TestAgentIdRegex:
    def test_valid_simple(self) -> None:
        assert _AGENT_ID_RE.match("software-engineer") is not None

    def test_valid_with_underscore(self) -> None:
        assert _AGENT_ID_RE.match("my_agent") is not None

    def test_valid_alphanumeric(self) -> None:
        assert _AGENT_ID_RE.match("agent01") is not None

    def test_single_char_valid(self) -> None:
        assert _AGENT_ID_RE.match("a") is not None

    def test_rejects_dot(self) -> None:
        assert _AGENT_ID_RE.match("agent.md") is None

    def test_rejects_double_dot(self) -> None:
        assert _AGENT_ID_RE.match("..") is None

    def test_rejects_slash(self) -> None:
        assert _AGENT_ID_RE.match("../../etc/passwd") is None

    def test_rejects_uppercase(self) -> None:
        assert _AGENT_ID_RE.match("SoftwareEngineer") is None

    def test_rejects_starts_with_hyphen(self) -> None:
        assert _AGENT_ID_RE.match("-bad") is None

    def test_rejects_ends_with_hyphen(self) -> None:
        assert _AGENT_ID_RE.match("bad-") is None

    def test_rejects_empty_string(self) -> None:
        assert _AGENT_ID_RE.match("") is None

    def test_rejects_absolute_path(self) -> None:
        assert _AGENT_ID_RE.match("/etc/passwd") is None

    def test_rejects_space(self) -> None:
        assert _AGENT_ID_RE.match("agent name") is None


# ---------------------------------------------------------------------------
# Unit tests: get_prompt — happy path
# ---------------------------------------------------------------------------


class TestGetPromptHappyPath:
    def test_returns_body_and_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_prompt returns (body, source_path) for a valid agent."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        monkeypatch.setenv("DADAIA_AGENTS_DIR", str(agents_dir))
        _write_agent(agents_dir, "software-engineer", body="You are the software engineer.")

        body, source = get_prompt("software-engineer", tmp_path)

        assert "software engineer" in body.lower()
        assert source.name == "software-engineer.md"
        assert source.parent.resolve() == agents_dir.resolve()

    def test_frontmatter_is_stripped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Frontmatter must not appear in the returned prompt body."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        monkeypatch.setenv("DADAIA_AGENTS_DIR", str(agents_dir))
        _write_agent(agents_dir, "qa-engineer", body="You test things.")

        body, _ = get_prompt("qa-engineer", tmp_path)

        assert "---" not in body
        assert "name:" not in body
        assert "You test things." in body


# ---------------------------------------------------------------------------
# Unit tests: get_prompt — invalid IDs raise InvalidAgentIdError (→ 400)
# ---------------------------------------------------------------------------


class TestGetPromptInvalidId:
    def test_dot_in_id_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidAgentIdError):
            get_prompt("agent.md", tmp_path)

    def test_double_dot_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidAgentIdError):
            get_prompt("..", tmp_path)

    def test_path_separator_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidAgentIdError):
            get_prompt("../../etc/passwd", tmp_path)

    def test_absolute_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidAgentIdError):
            get_prompt("/etc/passwd", tmp_path)

    def test_uppercase_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidAgentIdError):
            get_prompt("SoftwareEngineer", tmp_path)

    def test_empty_string_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidAgentIdError):
            get_prompt("", tmp_path)


# ---------------------------------------------------------------------------
# Unit tests: get_prompt — missing agent raises AgentNotFoundError (→ 404)
# ---------------------------------------------------------------------------


class TestGetPromptNotFound:
    def test_missing_agent_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Valid ID but no file → AgentNotFoundError."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        monkeypatch.setenv("DADAIA_AGENTS_DIR", str(agents_dir))

        with pytest.raises(AgentNotFoundError):
            get_prompt("nonexistent-agent", tmp_path)

    def test_no_agents_dir_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no agents dir exists at all → AgentNotFoundError."""
        monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)

        with pytest.raises(AgentNotFoundError):
            get_prompt("software-engineer", tmp_path)


# ---------------------------------------------------------------------------
# Unit tests: get_prompt — symlink path traversal → InvalidAgentIdError (→ 400)
# ---------------------------------------------------------------------------


class TestGetPromptSymlinkTraversal:
    def test_symlink_escape_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A symlink in the agents dir that points outside the base raises InvalidAgentIdError.

        This exercises the defence-in-depth Path.resolve().is_relative_to(base)
        check that keeps prompt lookup inside the configured agents directory.
        """
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        monkeypatch.setenv("DADAIA_AGENTS_DIR", str(agents_dir))

        # Create a real file outside the agents dir.
        outside = tmp_path / "outside.md"
        outside.write_text(
            "---\nname: evil\ndescription: outside\n---\n\nEvil prompt.", encoding="utf-8"
        )

        # Create a symlink inside agents_dir pointing to the outside file.
        # The link name must match the agent_id we will request.
        # NOTE: the id "evil-link" would normally resolve to agents_dir/evil-link.md,
        # but after Path.resolve() it points to tmp_path/outside.md which is NOT
        # relative to agents_dir.
        symlink_path = agents_dir / "evil-link.md"
        symlink_path.symlink_to(outside)

        with pytest.raises(InvalidAgentIdError):
            get_prompt("evil-link", tmp_path)


# ---------------------------------------------------------------------------
# Unit tests: render_api_agent_prompt view factory
# ---------------------------------------------------------------------------


class TestRenderApiAgentPromptView:
    def _make_view(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Build the view callable with agents in a temp dir."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        monkeypatch.setenv("DADAIA_AGENTS_DIR", str(agents_dir))
        _write_agent(agents_dir, "software-engineer", body="You implement code.")
        service = _FakeService(workspace_root=tmp_path)
        return render_api_agent_prompt(service)  # type: ignore[arg-type]

    def test_happy_path_200(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Valid agent_id returns 200 with correct shape."""
        view = self._make_view(tmp_path, monkeypatch)
        status, content_type, body = view(agent_id="software-engineer")

        assert status == 200
        assert "application/json" in content_type
        data = json.loads(body)
        assert data["agent_id"] == "software-engineer"
        assert "system_prompt" in data
        assert "source_path" in data

    def test_happy_path_body_content(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """system_prompt contains the Markdown body, frontmatter stripped."""
        view = self._make_view(tmp_path, monkeypatch)
        _, _, body_bytes = view(agent_id="software-engineer")
        data = json.loads(body_bytes)

        assert "You implement code." in data["system_prompt"]
        assert "name:" not in data["system_prompt"]

    def test_invalid_id_chars_returns_400(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """agent_id with invalid chars returns 400, NOT 404."""
        view = self._make_view(tmp_path, monkeypatch)
        status, _, body_bytes = view(agent_id="agent.md")

        assert status == 400
        data = json.loads(body_bytes)
        assert data["error"] == "invalid_agent_id"

    def test_double_dot_traversal_returns_400(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """.. in agent_id returns 400."""
        view = self._make_view(tmp_path, monkeypatch)
        status, _, _ = view(agent_id="..")
        assert status == 400

    def test_absolute_path_attempt_returns_400(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """/etc/passwd style id returns 400."""
        view = self._make_view(tmp_path, monkeypatch)
        status, _, _ = view(agent_id="/etc/passwd")
        assert status == 400

    def test_missing_agent_returns_404(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valid id format but no matching file → 404."""
        view = self._make_view(tmp_path, monkeypatch)
        status, _, body_bytes = view(agent_id="nonexistent-agent")

        assert status == 404
        data = json.loads(body_bytes)
        assert data["error"] == "not_found"

    def test_response_content_type_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Content-Type must be application/json; charset=utf-8 for all responses."""
        view = self._make_view(tmp_path, monkeypatch)

        for agent_id, _expected_status in [
            ("software-engineer", 200),
            ("nonexistent-agent", 404),
            ("bad.id", 400),
        ]:
            _, content_type, _ = view(agent_id=agent_id)
            assert content_type == "application/json; charset=utf-8", (
                f"Wrong content-type for agent_id={agent_id!r}: {content_type!r}"
            )

    def test_symlink_traversal_returns_400(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Symlink escaping agents_dir returns 400 (defence-in-depth check)."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        monkeypatch.setenv("DADAIA_AGENTS_DIR", str(agents_dir))

        # Real file outside agents dir.
        outside = tmp_path / "outside.md"
        outside.write_text(
            "---\nname: evil-link\ndescription: outside\n---\n\nEvil prompt.", encoding="utf-8"
        )
        # Symlink inside agents_dir pointing outside.
        (agents_dir / "evil-link.md").symlink_to(outside)

        service = _FakeService(workspace_root=tmp_path)
        view = render_api_agent_prompt(service)  # type: ignore[arg-type]

        status, _, body_bytes = view(agent_id="evil-link")
        assert status == 400
        data = json.loads(body_bytes)
        assert data["error"] == "invalid_agent_id"
