"""Unit tests for dadaia_workspace.features.spec_artifacts.new_artifacts.

Intent: CONTRACT — release_new coverage (unchanged by SPEC v0.4.2/v0.12.0; the id-form
axis flipped by SPEC v0.5.0 FR1 boundary 2a / AS-13, T-050-06A).

Covers:
- AC-T7-1: release_new creates SPEC.md with Draft frontmatter
- AC-T7-2: release_new exits non-zero (raises FileExistsError) when dir exists
- AC-T7-5: release_new raises ValueError for invalid slug

``backlog_new`` MOVED to ``features.backlog.document`` at SPEC v0.4.2 FR1 (GRILL D1) —
its A1.1-A1.7 (formerly A3.1-A3.4) coverage relocated UNMODIFIED to
``tests/unit/features/backlog/test_document.py``, alongside the parser it now shares
its grammar with.

(The legacy ``bug_new`` scaffolder was retired in v0.1.53 — bugs are event-sourced JSONL
via ``dadaia bugs append``.)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_artifacts.new_artifacts import release_new


def test_existing_dir_raises_file_exists_error(tmp_path: Path) -> None:
    """AC-T7-2: raises FileExistsError when dir already exists."""
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "releases" / "my-feature-v1").mkdir(parents=True)

    with pytest.raises(FileExistsError, match=r"already exists"):
        release_new(specs, "my-feature-v1")


def test_accepts_bare_semver_release_id(tmp_path: Path) -> None:
    """H1 (bug release-new-rejects-semver-but-doctor-requires-it): the bare SemVer
    canon ``X.Y.Z`` — which `specs doctor` SPEC-DOC-027 REQUIRES for a live release dir
    since canon v6 (T-050-06A/AS-13) — must be accepted (it used to be rejected by the
    slug-only validator, pre-FR3)."""
    specs = tmp_path / "specs"
    specs.mkdir()

    result = release_new(specs, "0.1.23")
    assert (specs / "releases" / "0.1.23" / "SPEC.md").is_file()
    assert result.created is True


def test_refuses_v_prefixed_release_id_at_mint(tmp_path: Path) -> None:
    """A1.10/AS-13 (T-050-06A): the `v`-prefixed axis is retired-archive-only — minting
    a NEW release id carrying a `v` prefix is refused, even though the same string
    would have been accepted before the canon-v6 axis flip."""
    specs = tmp_path / "specs"
    specs.mkdir()

    with pytest.raises(ValueError, match=r"Invalid release ID"):
        release_new(specs, "v0.1.23")
    assert not (specs / "releases" / "v0.1.23").exists()


# ---------------------------------------------------------------------------
# release_new id validation matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "match"),
    [
        pytest.param("INVALID NAME", r"Invalid release ID", id="release-uppercase"),
        pytest.param("my feature v1", r"Invalid release ID", id="release-spaces"),
        pytest.param("1bad-slug", r"Invalid release ID", id="release-leading-digit"),
        # AS-13/T-050-06A: bare "0.1.23" is now the MINTABLE canon form (see
        # test_accepts_bare_semver_release_id); the v-prefixed retired axis is what's
        # refused at mint now (see test_refuses_v_prefixed_release_id_at_mint).
        pytest.param("v0.1", r"Invalid release ID", id="release-dotted-too-short"),
        pytest.param("v0.1.2.3", r"Invalid release ID", id="release-dotted-4-segments"),
        pytest.param("v1.2.x", r"Invalid release ID", id="release-dotted-non-numeric"),
    ],
)
def test_invalid_release_id_matrix(tmp_path: Path, slug: str, match: str) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    with pytest.raises(ValueError, match=match):
        release_new(specs, slug)


# ---------------------------------------------------------------------------
# release_new creation-content facets (+ other valid-slug shapes) — 1 test
# ---------------------------------------------------------------------------


def test_release_new_creation_content(tmp_path: Path) -> None:
    """AC-T7-1: SPEC.md is created with Draft status, the release id, every required
    frontmatter field, and releases/ is auto-created when absent. Also covers other
    valid-slug shapes (hyphenated, digits-after-first-letter)."""
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
