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
    content = "---\nslug: test-atom\n---\n\n## Purpose\n\nBody.\n"
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


@pytest.mark.parametrize("stem", ["ARCHITECTURE", "TECHSTACK", "QUALITY"])
def test_toplevel_trio_slug_is_its_filename_stem(tmp_path: Path, stem: str) -> None:
    """Intent: CONTRACT — 0.4.7 FR9. ONE rule, no exception table: a `slug` equals its
    filename stem, the top-level trio included. The alias table that mapped
    `architecture` -> `ARCHITECTURE.md` was a second slug-resolution mechanism whose
    third copy (panel `_md_render`) already caused `panel-wikilink-slug-hardcoded`."""
    schema = load_frontmatter_schema()
    path = _make_atom(tmp_path, slug=stem, filename=f"{stem}.md")

    result = lint_atom(path, tmp_path, schema)

    assert not any("filename stem" in e for e in result.errors), result.errors


def test_the_retired_alias_slug_is_now_a_stem_mismatch(tmp_path: Path) -> None:
    """Intent: CONTRACT — 0.4.7 FR9. `slug: architecture` on `ARCHITECTURE.md` was the
    ONE named exception; with the alias table deleted it is an ordinary mismatch."""
    schema = load_frontmatter_schema()
    path = _make_atom(tmp_path, slug="architecture", filename="ARCHITECTURE.md")

    result = lint_atom(path, tmp_path, schema)

    assert any("slug" in e and "filename stem" in e for e in result.errors), result.errors


def test_slug_stem_mismatch_errors(tmp_path: Path) -> None:
    schema = load_frontmatter_schema()
    path = _make_atom(tmp_path, slug="architecture", filename="not-the-canon-name.md")

    result = lint_atom(path, tmp_path, schema)

    assert any("slug" in e and "filename stem" in e for e in result.errors)


@pytest.mark.parametrize("stem", ["ARCHITECTURE", "TECHSTACK", "QUALITY"])
def test_wikilink_resolves_iff_the_named_file_exists(tmp_path: Path, stem: str) -> None:
    """Intent: CONTRACT — 0.4.7 FR9. `[[x]]` resolves iff `x.md` exists under memory/ —
    the trio is linkable by its stem, and by nothing else."""
    schema = load_frontmatter_schema()
    _make_atom(tmp_path, slug=stem, filename=f"{stem}.md")
    path = _make_atom(tmp_path, slug="source", body=f"## Purpose\n\nsee [[{stem}]]\n")

    result = lint_atom(path, tmp_path, schema)

    assert not any(stem in e for e in result.errors), result.errors


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


# --------------------------------------------------------------------------- #
# T-047-93 — a product atom declares the code it describes (`sources`).
# --------------------------------------------------------------------------- #


def _product_tree(tmp_path: Path) -> tuple[Path, Path]:
    """A repo with one real source file and an empty `specs/memory/product/area/`."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "code.py").write_text("x = 1\n", encoding="utf-8")
    memory_dir = tmp_path / "specs" / "memory"
    area = memory_dir / "product" / "area"
    area.mkdir(parents=True)
    return memory_dir, area


def test_a_product_atom_without_sources_is_an_error(tmp_path: Path) -> None:
    memory_dir, area = _product_tree(tmp_path)
    atom = _make_atom(area, slug="feature")

    result = lint_atom(atom, memory_dir, load_frontmatter_schema())

    assert any("sources" in error for error in result.errors), result.errors


def test_a_source_glob_that_matches_no_file_is_an_error(tmp_path: Path) -> None:
    memory_dir, area = _product_tree(tmp_path)
    atom = _make_atom(area, slug="feature", extra_fm_fields={"sources": ["src/gone/**"]})

    result = lint_atom(atom, memory_dir, load_frontmatter_schema())

    assert any("src/gone/**" in error for error in result.errors), result.errors


def test_a_product_atom_whose_sources_match_real_code_is_clean(tmp_path: Path) -> None:
    memory_dir, area = _product_tree(tmp_path)
    atom = _make_atom(area, slug="feature", extra_fm_fields={"sources": ["src/**"]})

    result = lint_atom(atom, memory_dir, load_frontmatter_schema())

    assert result.errors == []


def test_a_canonical_file_needs_no_sources(tmp_path: Path) -> None:
    memory_dir, _ = _product_tree(tmp_path)
    atom = _make_atom(memory_dir, slug="ARCHITECTURE", filename="ARCHITECTURE.md")

    result = lint_atom(atom, memory_dir, load_frontmatter_schema())

    assert result.errors == []


# ---------------------------------------------------------------------------
# MEM-NARRATIVE-1 — memory states current truth; a history line is an ERROR naming
# the line. Expected values come from the SPEC's token and phrase tables.
# ---------------------------------------------------------------------------

_SOURCES_FM: dict[str, object] = {"sources": ["pyproject.toml"]}


def _narrative(result_errors: list[str]) -> list[str]:
    return [e for e in result_errors if e.startswith("MEM-NARRATIVE-1")]


def _canonical(tmp_path: Path, body: str) -> list[str]:
    """A body line in ARCHITECTURE.md (a canonical file, not a product atom)."""
    path = _make_atom(tmp_path, slug="ARCHITECTURE", filename="ARCHITECTURE.md", body=body)
    return _narrative(lint_atom(path, tmp_path, load_frontmatter_schema()).errors)


def _product(tmp_path: Path, body: str) -> list[str]:
    """A body line in product/<area>/<slug>.md, sources resolving to a real file."""
    memory = tmp_path / "specs" / "memory"
    area = memory / "product" / "area"
    area.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    path = _make_atom(area, slug="atom", body=body, extra_fm_fields=_SOURCES_FM)
    return _narrative(lint_atom(path, memory, load_frontmatter_schema()).errors)


def _body_line(path_text: str, needle: str) -> int:
    return path_text.splitlines().index(needle) + 1


def test_narrative_exempts_the_principle_adr_line(tmp_path: Path) -> None:
    """Intent: CONTRACT — T-047-98. `ADR: NNNN (accepted)` names the decision that
    governs a principle — it is current truth, not history."""
    assert _canonical(tmp_path, "## Principles\n\nADR: 0023 (accepted)\n") == []


def test_narrative_exempts_code_fences(tmp_path: Path) -> None:
    """Intent: CONTRACT — T-047-98. A fenced example may carry any token."""
    body = "## Purpose\n\n```\nrelease 0.4.7 on 2026-09-22 for T-047-98\n```\n"
    assert _canonical(tmp_path, body) == []


@pytest.mark.parametrize(
    "line",
    [
        "Shipped on 2026-09-22.",
        "Since 0.4.7 the gate reads nothing.",
        "Candidate c11 rewrote it.",
        "Built in rc-4.",
        "Delivered by T-047-98.",
        "Covers FR4.",
    ],
    ids=["iso-date", "release-id", "candidate", "rc", "task-id", "fr-id"],
)
def test_narrative_token_in_any_memory_file_names_its_line(tmp_path: Path, line: str) -> None:
    """Intent: CONTRACT — T-047-98. Each token class is history in every memory file."""
    body = f"## Purpose\n\nCurrent truth.\n{line}\n"
    path = _make_atom(tmp_path, slug="QUALITY", filename="QUALITY.md", body=body)
    errors = _narrative(lint_atom(path, tmp_path, load_frontmatter_schema()).errors)
    expected = _body_line(path.read_text(encoding="utf-8"), line)
    assert len(errors) == 1, errors
    assert errors[0].startswith(f"MEM-NARRATIVE-1 line {expected}:"), errors


def test_narrative_ignores_versions_that_are_not_release_ids(tmp_path: Path) -> None:
    """Intent: CONTRACT — T-047-98. A loopback address or a two-part version is no release."""
    assert _canonical(tmp_path, "## Purpose\n\nBinds 127.0.0.1 on Python 3.12.\n") == []


def test_narrative_ignores_a_pinned_dependency_version(tmp_path: Path) -> None:
    """Intent: CONTRACT — T-047-98. `tool==x.y.z` is a dependency pin, a fact of the stack."""
    assert _canonical(tmp_path, "## Purpose\n\nMutation runs `mutmut==3.7.0`.\n") == []


@pytest.mark.parametrize(
    "phrase",
    [
        "operator doctrine",
        "operator decision",
        "operator ruling",
        "closed as",
        "died",
        "was deleted",
        "retired",
        "no longer",
        "formerly",
        "previously",
    ],
)
def test_narrative_history_phrase_in_a_product_atom(tmp_path: Path, phrase: str) -> None:
    """Intent: CONTRACT — T-047-98. A history phrase is an ERROR in a product atom."""
    line = f"The verb {phrase} here."
    errors = _product(tmp_path, f"## Purpose\n\nCurrent truth.\n{line}\n")
    atom = tmp_path / "specs" / "memory" / "product" / "area" / "atom.md"
    expected = _body_line(atom.read_text(encoding="utf-8"), line)
    assert len(errors) == 1, errors
    assert errors[0].startswith(f"MEM-NARRATIVE-1 line {expected}:"), errors


def test_narrative_history_phrase_outside_product_is_not_flagged(tmp_path: Path) -> None:
    """Intent: CONTRACT — T-047-98. The phrase table applies to product atoms only."""
    assert _canonical(tmp_path, "## Principles\n\nA retired path is no longer read.\n") == []
