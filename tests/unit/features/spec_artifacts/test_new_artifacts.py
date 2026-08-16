"""Unit tests for dadaia_workspace.features.spec_artifacts.new_artifacts.

Intent: CONTRACT — v0.12.0 A3.1-A3.4 (backlog_new); legacy release_new coverage kept
unchanged (release_new is not touched by SPEC v0.12.0 FR3).

Covers:
- AC-T7-1: release_new creates SPEC.md with Draft frontmatter
- AC-T7-2: release_new exits non-zero (raises FileExistsError) when dir exists
- AC-T7-5: release_new raises ValueError for invalid slug
- A3.1: backlog_new on a tree with no BACKLOG.md creates the document with both
  section headings and one conformant ACTIVE subsection.
- A3.2: backlog_new on an existing document appends one subsection and leaves every
  other byte of the file unchanged (byte-diff assertion).
- A3.3: a slug already present in ACTIVE or LEDGER is refused (FileExistsError, the
  slug-uniqueness invariant replacing file-level no-clobber — grill P11).
- A3.4: an invalid slug is refused with the unchanged ``^[a-z][a-z0-9-]+$`` message.

(The legacy ``bug_new`` scaffolder was retired in v0.1.53 — bugs are event-sourced JSONL
via ``dadaia bugs append``.)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_artifacts.new_artifacts import (
    backlog_new,
    release_new,
)


def test_existing_dir_raises_file_exists_error(tmp_path: Path) -> None:
    """AC-T7-2: raises FileExistsError when dir already exists."""
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
        pytest.param(
            release_new, "v0.1.2.3", r"Invalid release ID", id="release-dotted-4-segments"
        ),
        pytest.param(release_new, "v1.2.x", r"Invalid release ID", id="release-dotted-non-numeric"),
        # A3.4 — backlog_new's slug validation message is unchanged.
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
    """AC-T7-1: SPEC.md is created with Draft status, the release id, every required
    frontmatter field, and releases/ is auto-created when absent. Also covers other
    valid-slug shapes (hyphenated, digits-after-first-letter). release_new is
    untouched by SPEC v0.12.0 (FR3 scopes backlog_new only)."""
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
# backlog_new — A3.1: authors BACKLOG.md (both headings + one conformant subsection)
# ---------------------------------------------------------------------------


def test_backlog_new_on_absent_document_creates_both_sections_and_one_subsection(
    tmp_path: Path,
) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    # backlog/ deliberately NOT pre-created — auto-creation facet.

    result = backlog_new(specs, "cool-idea")

    target = specs / "backlog" / "BACKLOG.md"
    assert target.is_file(), "BACKLOG.md must be created (A3.1)"
    assert result.path == target
    assert result.created is True

    content = target.read_text(encoding="utf-8")
    assert content.count("## ACTIVE") == 1
    assert content.count("## LEDGER") == 1
    assert content.index("## ACTIVE") < content.index("## LEDGER")
    assert "### cool-idea" in content
    assert content.index("### cool-idea") > content.index("## ACTIVE")
    assert content.index("### cool-idea") < content.index("## LEDGER")

    assert "- **Title:** cool-idea" in content
    assert "- **Status:** idea" in content
    assert "- **Provenance:**" in content
    from datetime import UTC, datetime

    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    assert f"- **Opened:** {today}" in content

    # The intents teaching comment is preserved (SPEC FR3), as a commented block, not
    # a live `**Intents:**` binding — an `idea` stays doctor-clean with none.
    assert "<!--" in content and "-->" in content
    assert "**Intents:**" in content  # named inside the teaching comment
    for kind in ("code", "cli", "catalog", "doc", "invariant"):
        assert kind in content

    # The fresh subsection parses clean under the single-source document model.
    from dadaia_workspace.features.backlog.document import load_document

    doc = load_document(specs / "backlog")
    assert doc.errors == ()
    assert len(doc.active) == 1
    assert doc.active[0].slug == "cool-idea"
    assert doc.active[0].status == "idea"
    assert doc.active[0].intents == ()


# ---------------------------------------------------------------------------
# backlog_new — A3.2: append leaves every other byte unchanged (byte-diff assertion)
# ---------------------------------------------------------------------------


def test_backlog_new_append_leaves_every_other_byte_unchanged(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    backlog_new(specs, "first-idea")

    target = specs / "backlog" / "BACKLOG.md"
    before = target.read_text(encoding="utf-8")

    backlog_new(specs, "second-idea")
    after = target.read_text(encoding="utf-8")

    assert after != before
    assert after.startswith(before[: before.index("## LEDGER")]), (
        "everything before the LEDGER heading in the original file must survive "
        "byte-for-byte, with the new subsection appended just ahead of it"
    )
    assert after.endswith(before[before.index("## LEDGER") :]), (
        "the LEDGER heading and everything after it must survive byte-for-byte"
    )
    assert "### second-idea" in after
    assert "### first-idea" in after


# ---------------------------------------------------------------------------
# backlog_new — A3.3: slug uniqueness across ACTIVE ∪ LEDGER (not file-level no-clobber)
# ---------------------------------------------------------------------------


def test_backlog_new_refuses_slug_already_in_active(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    backlog_new(specs, "cool-idea")

    with pytest.raises(FileExistsError, match=r"already exists"):
        backlog_new(specs, "cool-idea")


def test_backlog_new_refuses_slug_already_in_ledger(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    backlog_dir = specs / "backlog"
    backlog_dir.mkdir()
    (backlog_dir / "BACKLOG.md").write_text(
        "## ACTIVE\n\n## LEDGER\n\n- delivered-slug · DELIVERED · v0.9.0 · 2026-06-01\n",
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError, match=r"already exists"):
        backlog_new(specs, "delivered-slug")


# ---------------------------------------------------------------------------
# backlog_new — A3.4: invalid slug refused, message unchanged
# ---------------------------------------------------------------------------


def test_backlog_new_invalid_slug_refused_with_unchanged_message(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    with pytest.raises(ValueError, match=r"Invalid slug"):
        backlog_new(specs, "Not-A-Valid-Slug")
