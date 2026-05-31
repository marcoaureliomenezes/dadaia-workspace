"""Unit tests for dadaia_workspace.features.spec_artifacts.new_artifacts.

Covers:
- AC-T7-1: release_new creates SPEC.md with Draft frontmatter
- AC-T7-2: release_new exits non-zero (raises FileExistsError) when dir exists
- AC-T7-3: backlog_new creates slug.md with canonical frontmatter
- AC-T7-4: bug_new creates slug.md with session_id: null
- AC-T7-5: release_new raises ValueError for invalid slug
- AC-C-1..AC-C-5: per acceptance criteria
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_artifacts.new_artifacts import (
    backlog_new,
    bug_new,
    release_new,
)

# ── release_new ───────────────────────────────────────────────────────────────


class TestReleaseNew:
    """Tests for release_new()."""

    def test_creates_release_spec_md(self, tmp_path: Path) -> None:
        """AC-T7-1 / AC-C-1: creates specs/releases/<id>/SPEC.md."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "releases").mkdir()

        result = release_new(specs, "my-feature-v1")

        spec_path = specs / "releases" / "my-feature-v1" / "SPEC.md"
        assert spec_path.is_file(), "SPEC.md must be created (AC-T7-1)"
        assert result.path == spec_path
        assert result.created is True

    def test_spec_md_contains_draft_status(self, tmp_path: Path) -> None:
        """AC-T7-1: SPEC.md contains Status: Draft."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "releases").mkdir()

        release_new(specs, "my-feature-v1")
        content = (specs / "releases" / "my-feature-v1" / "SPEC.md").read_text(encoding="utf-8")
        assert "Status:** Draft" in content or "Status: Draft" in content, (
            "SPEC.md must contain Status: Draft (AC-T7-1)"
        )

    def test_spec_md_contains_release_id(self, tmp_path: Path) -> None:
        """SPEC.md must contain the release ID."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "releases").mkdir()

        release_new(specs, "my-feature-v1")
        content = (specs / "releases" / "my-feature-v1" / "SPEC.md").read_text(encoding="utf-8")
        assert "my-feature-v1" in content

    def test_spec_md_contains_required_frontmatter_fields(self, tmp_path: Path) -> None:
        """SPEC.md must contain all required frontmatter fields."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "releases").mkdir()

        release_new(specs, "my-feature-v1")
        content = (specs / "releases" / "my-feature-v1" / "SPEC.md").read_text(encoding="utf-8")
        for field in ("Status", "Release ID", "Owner", "Opened"):
            assert field in content, f"Missing frontmatter field: {field}"

    def test_creates_releases_dir_if_missing(self, tmp_path: Path) -> None:
        """release_new creates releases/ directory if absent."""
        specs = tmp_path / "specs"
        specs.mkdir()
        # Do NOT pre-create releases/

        release_new(specs, "my-feature-v1")

        assert (specs / "releases" / "my-feature-v1" / "SPEC.md").is_file()

    def test_existing_dir_raises_file_exists_error(self, tmp_path: Path) -> None:
        """AC-T7-2 / AC-C-2: raises FileExistsError when dir already exists."""
        specs = tmp_path / "specs"
        specs.mkdir()
        # Pre-create the directory
        (specs / "releases" / "my-feature-v1").mkdir(parents=True)

        with pytest.raises(FileExistsError, match=r"already exists"):
            release_new(specs, "my-feature-v1")

    def test_invalid_slug_uppercase_raises_value_error(self, tmp_path: Path) -> None:
        """AC-T7-5 / AC-C-5: slug with uppercase raises ValueError."""
        specs = tmp_path / "specs"
        specs.mkdir()

        with pytest.raises(ValueError, match=r"Invalid release ID"):
            release_new(specs, "INVALID NAME")

    def test_invalid_slug_spaces_raises_value_error(self, tmp_path: Path) -> None:
        """AC-T7-5 / AC-C-5: slug with spaces raises ValueError."""
        specs = tmp_path / "specs"
        specs.mkdir()

        with pytest.raises(ValueError, match=r"Invalid release ID"):
            release_new(specs, "my feature v1")

    def test_invalid_slug_starting_with_digit(self, tmp_path: Path) -> None:
        """Slug starting with a digit raises ValueError."""
        specs = tmp_path / "specs"
        specs.mkdir()

        with pytest.raises(ValueError, match=r"Invalid release ID"):
            release_new(specs, "1bad-slug")

    def test_valid_slug_with_hyphens(self, tmp_path: Path) -> None:
        """Hyphenated slugs are valid."""
        specs = tmp_path / "specs"
        specs.mkdir()

        result = release_new(specs, "my-feature-v1")
        assert result.path.is_file()

    def test_valid_slug_with_digits(self, tmp_path: Path) -> None:
        """Slugs with digits after the first letter are valid."""
        specs = tmp_path / "specs"
        specs.mkdir()

        result = release_new(specs, "release2026")
        assert result.path.is_file()


# ── backlog_new ───────────────────────────────────────────────────────────────


class TestBacklogNew:
    """Tests for backlog_new()."""

    def test_creates_backlog_md(self, tmp_path: Path) -> None:
        """AC-T7-3 / AC-C-3: creates specs/backlog/<slug>.md."""
        specs = tmp_path / "specs"
        specs.mkdir()

        result = backlog_new(specs, "cool-idea")

        target = specs / "backlog" / "cool-idea.md"
        assert target.is_file(), "cool-idea.md must be created (AC-T7-3)"
        assert result.path == target
        assert result.created is True

    def test_backlog_md_contains_frontmatter(self, tmp_path: Path) -> None:
        """Backlog entry must contain YAML frontmatter."""
        specs = tmp_path / "specs"
        specs.mkdir()

        backlog_new(specs, "cool-idea")
        content = (specs / "backlog" / "cool-idea.md").read_text(encoding="utf-8")
        assert "title:" in content
        assert "status: idea" in content
        assert "opened:" in content

    def test_creates_backlog_dir_if_missing(self, tmp_path: Path) -> None:
        """backlog_new creates backlog/ directory if absent."""
        specs = tmp_path / "specs"
        specs.mkdir()

        backlog_new(specs, "cool-idea")
        assert (specs / "backlog" / "cool-idea.md").is_file()

    def test_existing_file_raises(self, tmp_path: Path) -> None:
        """Raises FileExistsError when file already exists."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "backlog").mkdir()
        (specs / "backlog" / "cool-idea.md").write_text("existing", encoding="utf-8")

        with pytest.raises(FileExistsError, match=r"already exists"):
            backlog_new(specs, "cool-idea")

    def test_invalid_slug_raises(self, tmp_path: Path) -> None:
        """Invalid slug raises ValueError."""
        specs = tmp_path / "specs"
        specs.mkdir()

        with pytest.raises(ValueError, match=r"Invalid slug"):
            backlog_new(specs, "UPPERCASE SLUG")


# ── bug_new ───────────────────────────────────────────────────────────────────


class TestBugNew:
    """Tests for bug_new()."""

    def test_creates_bug_md(self, tmp_path: Path) -> None:
        """AC-T7-4 / AC-C-4: creates specs/bugs/<slug>.md."""
        specs = tmp_path / "specs"
        specs.mkdir()

        result = bug_new(specs, "login-crash")

        target = specs / "bugs" / "login-crash.md"
        assert target.is_file(), "login-crash.md must be created (AC-T7-4)"
        assert result.path == target
        assert result.created is True

    def test_bug_md_has_session_id_null(self, tmp_path: Path) -> None:
        """AC-T7-4 / AC-C-4: session_id: null must appear in the file."""
        specs = tmp_path / "specs"
        specs.mkdir()

        bug_new(specs, "login-crash")
        content = (specs / "bugs" / "login-crash.md").read_text(encoding="utf-8")
        assert "session_id: null" in content, "Bug file must contain session_id: null (AC-T7-4)"

    def test_bug_md_contains_frontmatter(self, tmp_path: Path) -> None:
        """Bug report must contain required frontmatter fields."""
        specs = tmp_path / "specs"
        specs.mkdir()

        bug_new(specs, "login-crash")
        content = (specs / "bugs" / "login-crash.md").read_text(encoding="utf-8")
        assert "title:" in content
        assert "severity: TBD" in content
        assert "opened:" in content
        assert "session_id: null" in content

    def test_creates_bugs_dir_if_missing(self, tmp_path: Path) -> None:
        """bug_new creates bugs/ directory if absent."""
        specs = tmp_path / "specs"
        specs.mkdir()

        bug_new(specs, "login-crash")
        assert (specs / "bugs" / "login-crash.md").is_file()

    def test_existing_file_raises(self, tmp_path: Path) -> None:
        """Raises FileExistsError when file already exists."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "bugs").mkdir()
        (specs / "bugs" / "login-crash.md").write_text("existing", encoding="utf-8")

        with pytest.raises(FileExistsError, match=r"already exists"):
            bug_new(specs, "login-crash")

    def test_invalid_slug_raises(self, tmp_path: Path) -> None:
        """Invalid slug raises ValueError."""
        specs = tmp_path / "specs"
        specs.mkdir()

        with pytest.raises(ValueError, match=r"Invalid slug"):
            bug_new(specs, "UPPERCASE")

    def test_no_session_id_env_var_does_not_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-T7-4: R1 spec — bug_new does NOT block when DADAIA_SESSION_ID is absent."""
        monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)
        specs = tmp_path / "specs"
        specs.mkdir()

        # Must NOT raise regardless of session state
        result = bug_new(specs, "no-session-bug")
        assert result.path.is_file()
        content = result.path.read_text(encoding="utf-8")
        assert "session_id: null" in content
