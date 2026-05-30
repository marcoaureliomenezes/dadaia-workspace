"""Integration tests for `dadaia release new`, `dadaia backlog new`, `dadaia bug new`.

Tests use Typer's CliRunner on a real tmp_path filesystem.

Covers:
- AC-T7-1: release new creates SPEC.md with Draft frontmatter
- AC-T7-2: release new exits non-zero when dir exists
- AC-T7-3: backlog new creates slug.md with canonical frontmatter
- AC-T7-4: bug new creates slug.md with session_id: null
- AC-T7-5: release new exits non-zero for invalid slug
- AC-C-1..AC-C-5
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    """Return an empty specs/ directory."""
    s = tmp_path / "specs"
    s.mkdir()
    return s


# ── dadaia release new ────────────────────────────────────────────────────────


class TestReleaseNew:
    def test_creates_spec_md(self, specs: Path) -> None:
        """AC-T7-1 / AC-C-1: creates SPEC.md with Draft status."""
        result = _runner.invoke(
            app,
            ["release", "new", "my-feature-v1", "--specs-dir", str(specs)],
        )

        assert result.exit_code == 0, result.output
        spec_path = specs / "releases" / "my-feature-v1" / "SPEC.md"
        assert spec_path.is_file()
        content = spec_path.read_text(encoding="utf-8")
        assert "Status:** Draft" in content or "Status: Draft" in content

    def test_spec_md_contains_release_id(self, specs: Path) -> None:
        """SPEC.md body references the release ID."""
        _runner.invoke(
            app,
            ["release", "new", "my-feature-v1", "--specs-dir", str(specs)],
        )
        content = (specs / "releases" / "my-feature-v1" / "SPEC.md").read_text(encoding="utf-8")
        assert "my-feature-v1" in content

    def test_spec_md_required_fields(self, specs: Path) -> None:
        """SPEC.md must contain Owner and Opened fields."""
        _runner.invoke(
            app,
            ["release", "new", "my-feature-v1", "--specs-dir", str(specs)],
        )
        content = (specs / "releases" / "my-feature-v1" / "SPEC.md").read_text(encoding="utf-8")
        assert "Owner" in content
        assert "Opened" in content

    def test_existing_dir_exits_nonzero(self, specs: Path) -> None:
        """AC-T7-2 / AC-C-2: exits non-zero when release dir already exists."""
        (specs / "releases" / "my-feature-v1").mkdir(parents=True)

        result = _runner.invoke(
            app,
            ["release", "new", "my-feature-v1", "--specs-dir", str(specs)],
        )

        assert result.exit_code != 0
        # Error message must be informative
        assert "already exists" in result.output.lower() or "already exists" in (result.stderr or "")

    def test_invalid_slug_exits_nonzero(self, specs: Path) -> None:
        """AC-T7-5 / AC-C-5: invalid slug exits non-zero."""
        result = _runner.invoke(
            app,
            ["release", "new", "INVALID NAME", "--specs-dir", str(specs)],
        )
        assert result.exit_code != 0

    def test_missing_specs_dir_exits_nonzero(self, tmp_path: Path) -> None:
        """Non-existent specs_dir causes non-zero exit."""
        result = _runner.invoke(
            app,
            ["release", "new", "my-feature-v1", "--specs-dir", str(tmp_path / "nope")],
        )
        assert result.exit_code != 0


# ── dadaia backlog new ────────────────────────────────────────────────────────


class TestBacklogNew:
    def test_creates_backlog_md(self, specs: Path) -> None:
        """AC-T7-3 / AC-C-3: creates specs/backlog/cool-idea.md."""
        result = _runner.invoke(
            app,
            ["backlog", "new", "cool-idea", "--specs-dir", str(specs)],
        )

        assert result.exit_code == 0, result.output
        target = specs / "backlog" / "cool-idea.md"
        assert target.is_file()

    def test_backlog_md_contains_frontmatter(self, specs: Path) -> None:
        """Backlog entry contains title, status, and opened."""
        _runner.invoke(
            app,
            ["backlog", "new", "cool-idea", "--specs-dir", str(specs)],
        )
        content = (specs / "backlog" / "cool-idea.md").read_text(encoding="utf-8")
        assert "title:" in content
        assert "status: idea" in content
        assert "opened:" in content

    def test_invalid_slug_exits_nonzero(self, specs: Path) -> None:
        """Invalid slug causes non-zero exit."""
        result = _runner.invoke(
            app,
            ["backlog", "new", "INVALID", "--specs-dir", str(specs)],
        )
        assert result.exit_code != 0

    def test_missing_specs_dir_exits_nonzero(self, tmp_path: Path) -> None:
        """Non-existent specs_dir causes non-zero exit."""
        result = _runner.invoke(
            app,
            ["backlog", "new", "cool-idea", "--specs-dir", str(tmp_path / "nope")],
        )
        assert result.exit_code != 0


# ── dadaia bug new ────────────────────────────────────────────────────────────


class TestBugNew:
    def test_creates_bug_md_with_session_id_null(self, specs: Path) -> None:
        """AC-T7-4 / AC-C-4: creates specs/bugs/login-crash.md with session_id: null."""
        result = _runner.invoke(
            app,
            ["bug", "new", "login-crash", "--specs-dir", str(specs)],
        )

        assert result.exit_code == 0, result.output
        target = specs / "bugs" / "login-crash.md"
        assert target.is_file()
        content = target.read_text(encoding="utf-8")
        assert "session_id: null" in content

    def test_bug_md_contains_required_frontmatter(self, specs: Path) -> None:
        """Bug report contains title, severity, opened, session_id."""
        _runner.invoke(
            app,
            ["bug", "new", "login-crash", "--specs-dir", str(specs)],
        )
        content = (specs / "bugs" / "login-crash.md").read_text(encoding="utf-8")
        assert "title:" in content
        assert "severity: TBD" in content
        assert "opened:" in content
        assert "session_id: null" in content

    def test_no_session_env_does_not_block(
        self, specs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-T7-4: R1 spec — command succeeds without DADAIA_SESSION_ID."""
        monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)

        result = _runner.invoke(
            app,
            ["bug", "new", "login-crash", "--specs-dir", str(specs)],
        )

        assert result.exit_code == 0, result.output
        assert (specs / "bugs" / "login-crash.md").is_file()

    def test_invalid_slug_exits_nonzero(self, specs: Path) -> None:
        """Invalid slug causes non-zero exit."""
        result = _runner.invoke(
            app,
            ["bug", "new", "INVALID", "--specs-dir", str(specs)],
        )
        assert result.exit_code != 0

    def test_missing_specs_dir_exits_nonzero(self, tmp_path: Path) -> None:
        """Non-existent specs_dir causes non-zero exit."""
        result = _runner.invoke(
            app,
            ["bug", "new", "login-crash", "--specs-dir", str(tmp_path / "nope")],
        )
        assert result.exit_code != 0
