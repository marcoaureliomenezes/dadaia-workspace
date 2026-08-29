"""Unit tests for ``features.specs.memory_lint`` — the ONE canonical LINT-1 implementation
(v0.4.3 T-043-20/FR16).

This module is imported directly by ``doctor_memory.MemoryValidator.check_lint1_memory_atoms``
(no subprocess), and ``public/scripts/lint-memory-atoms.py`` is now a thin wrapper that
imports and calls this module's ``main()`` — this test file exercises the package module
as a normal Python import.

``tests/unit/scripts/test_lint_memory_atoms.py`` (which loaded the standalone script via
``importlib.util.spec_from_file_location`` and called its own ``lint_atom``/``lint_directory``/
``HEADING_ALLOWLIST``/etc.) is DELETED, ai-engineer's T-043-20 half (A16.1/A16.2): once the
script stopped owning those symbols, the file tested a surface that no longer exists on the
script. Its behavioral coverage (lint_atom/lint_directory scenarios, main() exit codes) was
already a byte-identical port of what this file covers — see
the functions above this docstring's insertion point. Four checks in the deleted file were
NOT duplicates — they validate real on-disk public assets (the frontmatter schema, the
scaffold atoms, the memory-feature template) against this package's canon, independent of
the script/package split — those four are ported below, now importing the package directly.

Intent: CONTRACT — v0.4.3 A16.1.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs.memory_lint import (
    lint_atom,
    lint_directory,
    load_frontmatter_schema,
    main,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

_REQUIRED_FM = {
    "title": "Fixture atom",
    "category": "core",
    "tldr": "fixture atom for memory_lint tests",
    "summary": "fixture atom for memory_lint tests, exercising the ported package module",
    "tags": ["fixture"],
}


def _make_atom(
    dir_path: Path,
    *,
    slug: str,
    body: str = "## Purpose\n\nBody text.\n",
    filename: str | None = None,
    extra_fm_fields: dict[str, object] | None = None,
) -> Path:
    fields = dict(_REQUIRED_FM)
    fields["slug"] = slug
    if extra_fm_fields:
        fields.update(extra_fm_fields)
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {v}" for v in value)
        else:
            lines.append(f'{key}: "{value}"')
    lines.append("---")
    content = "\n".join(lines) + "\n\n" + body
    path = dir_path / (filename or f"{slug}.md")
    path.write_text(content, encoding="utf-8")
    return path


def test_load_frontmatter_schema_returns_the_packaged_schema() -> None:
    schema = load_frontmatter_schema()
    assert schema["$id"] == "memory-frontmatter-v1"
    assert "slug" in schema["required"]


def test_valid_atom_with_a_normal_heading_has_no_errors_or_warnings(tmp_path: Path) -> None:
    schema = load_frontmatter_schema()
    path = _make_atom(tmp_path, slug="test-atom", body="## Purpose\n\nBody.\n")

    result = lint_atom(path, tmp_path, schema)

    assert not result.has_errors, result.errors
    assert not result.has_warnings, result.warnings


def test_forbidden_heading_is_an_error(tmp_path: Path) -> None:
    schema = load_frontmatter_schema()
    path = _make_atom(tmp_path, slug="test-atom", body="## Changelog\n\nnot allowed\n")

    result = lint_atom(path, tmp_path, schema)

    assert result.has_errors
    assert any("Forbidden heading" in e for e in result.errors)


def test_novel_heading_is_never_flagged(tmp_path: Path) -> None:
    """The heading-vocabulary check (a curated allowlist of "known" headings) is
    retired (v0.5.0): a heading vocabulary is prose policy, not a lint. A heading
    nobody has ever seen before is neither an error nor a warning — only frontmatter
    schema conformance, forbidden (changelog/history) headings, duplicate headings,
    and wikilink resolution remain mechanically checked."""
    schema = load_frontmatter_schema()
    path = _make_atom(
        tmp_path, slug="test-atom", body="## A Brand New Never Before Seen Heading\n\nx\n"
    )

    result = lint_atom(path, tmp_path, schema)

    assert not result.has_errors, result.errors
    assert not result.has_warnings, result.warnings


def test_duplicate_heading_is_an_error(tmp_path: Path) -> None:
    schema = load_frontmatter_schema()
    path = _make_atom(tmp_path, slug="test-atom", body="## Purpose\n\nOne.\n\n## Purpose\n\nTwo.\n")

    result = lint_atom(path, tmp_path, schema)

    assert any("Duplicate" in e for e in result.errors)


def test_missing_required_frontmatter_field_is_an_error(tmp_path: Path) -> None:
    schema = load_frontmatter_schema()
    content = (
        "---\n"
        "slug: test-atom\n"
        "category: core\n"  # title deliberately omitted
        'tldr: "x"\n'
        'summary: "x"\n'
        "tags:\n  - fixture\n"
        "---\n\n## Purpose\n\nBody.\n"
    )
    path = tmp_path / "test-atom.md"
    path.write_text(content, encoding="utf-8")

    result = lint_atom(path, tmp_path, schema)

    assert result.has_errors
    assert any("title" in e for e in result.errors)


def test_multiple_missing_required_fields_are_all_reported(tmp_path: Path) -> None:
    """Checker half of bug memory-trio-missing-required-frontmatter-fields:
    ``jsonschema.validate()`` (single-error) used to report only the FIRST missing
    required field, so an author fixing one at a time never saw the next until a
    re-run. ``lint_atom`` now iterates every schema error, so all missing fields
    surface in one pass."""
    schema = load_frontmatter_schema()
    content = "---\nslug: test-atom\ncategory: core\n---\n\n## Purpose\n\nBody.\n"
    path = tmp_path / "test-atom.md"
    path.write_text(content, encoding="utf-8")

    result = lint_atom(path, tmp_path, schema)

    assert result.has_errors
    for missing in ("title", "tldr", "summary", "tags"):
        assert any(missing in e for e in result.errors), (
            f"expected a distinct error naming {missing!r}, got: {result.errors}"
        )


def test_yaml_parse_error_is_diagnosed_as_a_parse_error_not_a_missing_delimiter(
    tmp_path: Path,
) -> None:
    """Bug memory-lint-blames-missing-delimiter-for-a-yaml-parse-error: an
    unquoted scalar containing ': ' inside a present --- delimited block used to be
    reported as "No valid YAML frontmatter found (expected --- delimited block)" —
    blaming a missing delimiter when the real cause is a YAML syntax error with its
    own line/column. The block IS present here; the diagnostic must name the YAML
    failure, never the delimiter."""
    schema = load_frontmatter_schema()
    content = (
        "---\n"
        "slug: test-atom\n"
        "tldr: Two-tier memory: 17 measured principles\n"  # unquoted ": " breaks YAML
        "---\n\n## Purpose\n\nBody.\n"
    )
    path = tmp_path / "test-atom.md"
    path.write_text(content, encoding="utf-8")

    result = lint_atom(path, tmp_path, schema)

    assert result.has_errors
    assert not any("delimited block" in e for e in result.errors), (
        f"blamed a missing delimiter for a present block: {result.errors}"
    )
    assert any("YAML is invalid" in e for e in result.errors)


def test_slug_mismatch_is_an_error(tmp_path: Path) -> None:
    schema = load_frontmatter_schema()
    path = _make_atom(tmp_path, slug="correct-slug", filename="wrong-stem.md")

    result = lint_atom(path, tmp_path, schema)

    assert any("slug" in e and "filename stem" in e for e in result.errors)


def test_wikilink_resolution_valid_and_broken(tmp_path: Path) -> None:
    schema = load_frontmatter_schema()
    _make_atom(tmp_path, slug="target", body="## Purpose\n\ntarget atom\n")
    path = _make_atom(
        tmp_path,
        slug="source",
        body="## Purpose\n\nsee [[target]] and [[nonexistent]]\n",
    )

    result = lint_atom(path, tmp_path, schema)

    assert any("nonexistent" in e for e in result.errors)
    assert not any("[[target]]" in e for e in result.errors)


@pytest.mark.parametrize(
    ("slug", "canon_filename"),
    [
        ("architecture", "ARCHITECTURE.md"),
        ("tech-stack", "TECHSTACK.md"),
        ("quality-assurance", "QUALITY.md"),
    ],
)
def test_v6_canon_single_slug_stem_divergence_is_not_an_error(
    tmp_path: Path, slug: str, canon_filename: str
) -> None:
    """v6 canon (FR1/A1.5/A1.6, T-050-06): the three top-level singles keep their
    lowercase ``slug`` while their on-disk filename is the renamed canon name — this
    is the ONE named exception to "slug == filename stem", not a general relaxation."""
    schema = load_frontmatter_schema()
    path = _make_atom(tmp_path, slug=slug, filename=canon_filename)

    result = lint_atom(path, tmp_path, schema)

    assert not any("filename stem" in e for e in result.errors), result.errors


def test_slug_stem_mismatch_still_errors_when_not_a_v6_canon_single(tmp_path: Path) -> None:
    """The v6 canon exception is narrow: an unrelated slug/stem mismatch still errors."""
    schema = load_frontmatter_schema()
    path = _make_atom(tmp_path, slug="architecture", filename="not-the-canon-name.md")

    result = lint_atom(path, tmp_path, schema)

    assert any("slug" in e and "filename stem" in e for e in result.errors)


@pytest.mark.parametrize(
    ("wikilink_slug", "canon_filename"),
    [
        ("architecture", "ARCHITECTURE.md"),
        ("tech-stack", "TECHSTACK.md"),
        ("quality-assurance", "QUALITY.md"),
    ],
)
def test_wikilink_resolves_to_renamed_v6_canon_single(
    tmp_path: Path, wikilink_slug: str, canon_filename: str
) -> None:
    """A ``[[wikilink]]`` to one of the v6 canon singles resolves to the RENAMED file,
    not to ``<slug>.md`` (which no longer exists on disk)."""
    schema = load_frontmatter_schema()
    _make_atom(tmp_path, slug=wikilink_slug, filename=canon_filename)
    path = _make_atom(
        tmp_path,
        slug="source",
        body=f"## Purpose\n\nsee [[{wikilink_slug}]]\n",
    )

    result = lint_atom(path, tmp_path, schema)

    assert not any(wikilink_slug in e for e in result.errors), result.errors


def test_lint_directory_scans_toplevel_and_product_subdir_excludes_index(
    tmp_path: Path,
) -> None:
    schema = load_frontmatter_schema()
    _make_atom(tmp_path, slug="architecture")
    product_dir = tmp_path / "product"
    product_dir.mkdir()
    _make_atom(product_dir, slug="feature-a")
    (product_dir / "index.md").write_text("# TOC\n", encoding="utf-8")  # no frontmatter, excluded

    results = lint_directory(tmp_path, schema)

    scanned = {r.path.name for r in results}
    assert scanned == {"architecture.md", "feature-a.md"}


def test_lint_directory_empty_is_a_noop(tmp_path: Path) -> None:
    schema = load_frontmatter_schema()
    assert lint_directory(tmp_path, schema) == []


@pytest.mark.parametrize(
    ("shape", "expected_exit"),
    [
        pytest.param("clean", 0, id="clean-exit-0"),
        pytest.param("error", 1, id="error-exit-1"),
    ],
)
def test_main_end_to_end_exit_codes(tmp_path: Path, shape: str, expected_exit: int) -> None:
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    if shape == "clean":
        _make_atom(mem_dir, slug="test-atom", body="## Purpose\n\nclean\n")
    else:
        _make_atom(mem_dir, slug="test-atom", body="## Changelog\n\nforbidden\n")

    assert main(["--memory-dir", str(mem_dir)]) == expected_exit


# ---------------------------------------------------------------------------
# Ported from the deleted tests/unit/scripts/test_lint_memory_atoms.py — validates a
# REAL on-disk public asset (the frontmatter schema) against this package's canon,
# never a duplicate of the behavioral tests above (see the module docstring). Its
# three siblings (scaffold-atom-headings-allowlisted, memory-feature-template-
# headings-allowlisted, allowlist-content-pins) retired with HEADING_ALLOWLIST
# itself (v0.5.0): a heading vocabulary is prose policy, not a lint.
# ---------------------------------------------------------------------------


def test_agent_tier_property_absent_from_schema() -> None:
    """The expired ``agent_tier`` property must stay out of the frontmatter schema.

    Deprecated in v0.1.53 (zero runtime consumers) and dropped in v0.1.61 (D-1; zero
    carriers among all memory atoms). With ``additionalProperties: false`` its absence
    means any atom carrying ``agent_tier`` is a hard validation error — this pin
    prevents silent re-introduction.
    """
    schema = load_frontmatter_schema()
    assert "agent_tier" not in schema["properties"]
    assert "agent_tier" not in schema.get("required", [])
