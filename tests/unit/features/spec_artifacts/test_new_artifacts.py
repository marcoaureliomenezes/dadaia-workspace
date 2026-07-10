"""Unit tests for dadaia_workspace.features.spec_artifacts.new_artifacts.

Covers:
- AC-T7-1: release_new creates SPEC.md with Draft frontmatter
- AC-T7-2: release_new exits non-zero (raises FileExistsError) when dir exists
- AC-T7-3: backlog_new creates slug.md with canonical frontmatter
- AC-T7-5: release_new raises ValueError for invalid slug
- AC-C-1..AC-C-5: per acceptance criteria

(The legacy ``bug_new`` scaffolder was retired in v0.1.53 — bugs are event-sourced JSONL
via ``dadaia bugs append``.)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dadaia_workspace.features.spec_artifacts.new_artifacts import (
    backlog_new,
    release_new,
)


def test_existing_dir_raises_file_exists_error(tmp_path: Path) -> None:
    """AC-T7-2 / AC-C-2: raises FileExistsError when dir already exists."""
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "releases" / "my-feature-v1").mkdir(parents=True)

    with pytest.raises(FileExistsError, match=r"already exists"):
        release_new(specs, "my-feature-v1")


def test_accepts_semver_release_id(tmp_path: Path) -> None:
    """H1 (bug release-new-rejects-semver-but-doctor-requires-it): the SemVer canon
    ``vX.Y.Z`` — which `specs doctor` SPEC-DOC-027 REQUIRES for a live release dir —
    must be accepted (it used to be rejected by the slug-only validator)."""
    specs = tmp_path / "specs"
    specs.mkdir()

    result = release_new(specs, "v0.1.23")
    assert (specs / "releases" / "v0.1.23" / "SPEC.md").is_file()
    assert result.created is True


# ---------------------------------------------------------------------------
# slug/id validation matrix — 1 param table (release_new + backlog_new)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fn", "slug", "match"),
    [
        pytest.param(release_new, "INVALID NAME", r"Invalid release ID", id="release-uppercase"),
        pytest.param(release_new, "my feature v1", r"Invalid release ID", id="release-spaces"),
        pytest.param(release_new, "1bad-slug", r"Invalid release ID", id="release-leading-digit"),
        pytest.param(release_new, "0.1.23", r"Invalid release ID", id="release-dotted-no-v"),
        pytest.param(release_new, "v0.1", r"Invalid release ID", id="release-dotted-too-short"),
        pytest.param(release_new, "v0.1.2.3", r"Invalid release ID", id="release-dotted-4-segments"),
        pytest.param(release_new, "v1.2.x", r"Invalid release ID", id="release-dotted-non-numeric"),
        pytest.param(backlog_new, "UPPERCASE SLUG", r"Invalid slug", id="backlog-uppercase"),
    ],
)
def test_invalid_id_matrix(tmp_path: Path, fn, slug: str, match: str) -> None:  # type: ignore[no-untyped-def]
    specs = tmp_path / "specs"
    specs.mkdir()
    with pytest.raises(ValueError, match=match):
        fn(specs, slug)


# ---------------------------------------------------------------------------
# release_new creation-content facets (+ other valid-slug shapes) — 1 test
# ---------------------------------------------------------------------------


def test_release_new_creation_content(tmp_path: Path) -> None:
    """AC-T7-1/AC-C-1: SPEC.md is created with Draft status, the release id, every
    required frontmatter field, and releases/ is auto-created when absent. Also
    covers other valid-slug shapes (hyphenated, digits-after-first-letter)."""
    specs = tmp_path / "specs"
    specs.mkdir()
    # releases/ deliberately NOT pre-created — auto-creation facet.

    result = release_new(specs, "my-feature-v1")

    spec_path = specs / "releases" / "my-feature-v1" / "SPEC.md"
    assert spec_path.is_file(), "SPEC.md must be created (AC-T7-1)"
    assert result.path == spec_path
    assert result.created is True

    content = spec_path.read_text(encoding="utf-8")
    assert "Status:** Draft" in content or "Status: Draft" in content
    assert "my-feature-v1" in content
    for field in ("Status", "Release ID", "Owner", "Opened"):
        assert field in content, f"Missing frontmatter field: {field}"

    # Other valid slug shapes also create successfully.
    for slug in ("hyphenated-release-v1", "release2026"):
        other_result = release_new(specs, slug)
        assert other_result.path.is_file()


# ---------------------------------------------------------------------------
# backlog_new creation-content facets — 1 test
# ---------------------------------------------------------------------------


def test_backlog_new_creation_content(tmp_path: Path) -> None:
    """AC-T7-3/AC-C-3: backlog stub is created with frontmatter, the v0.1.55 FR5
    description + commented intents[] teaching template, and backlog/ auto-creates.
    A pre-existing file raises FileExistsError."""
    specs = tmp_path / "specs"
    specs.mkdir()
    # backlog/ deliberately NOT pre-created — auto-creation facet.

    result = backlog_new(specs, "cool-idea")

    target = specs / "backlog" / "cool-idea.md"
    assert target.is_file(), "cool-idea.md must be created (AC-T7-3)"
    assert result.path == target
    assert result.created is True

    content = target.read_text(encoding="utf-8")
    assert "title:" in content
    assert "status: idea" in content
    assert "opened:" in content

    frontmatter = content.split("---", 2)[1]
    parsed = yaml.safe_load(frontmatter)
    assert parsed.get("status") == "idea"
    assert "description" in parsed
    # The intents template is a COMMENTED teaching block, not a live frontmatter binding.
    assert "intents:" in content  # inside the HTML comment
    assert "<!--" in content and "-->" in content
    assert parsed.get("intents") is None  # no live intents ⇒ idea stays doctor-clean
    for kind in ("code", "cli", "catalog", "doc", "invariant"):
        assert kind in content

    with pytest.raises(FileExistsError, match=r"already exists"):
        backlog_new(specs, "cool-idea")
