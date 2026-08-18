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
script. Its behavioral coverage (lint_atom/lint_directory scenarios, workspace-allowlist
merge, main() exit codes) was already a byte-identical port of what this file covers — see
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
    HEADING_ALLOWLIST,
    _extract_h2_headings,
    lint_atom,
    lint_directory,
    load_frontmatter_schema,
    load_workspace_allowlist,
    main,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

_REQUIRED_FM = {
    "title": "Fixture atom",
    "category": "core",
    "tldr": "fixture atom for memory_lint tests",
    "summary": "fixture atom for memory_lint tests, exercising the ported package module",
    "tags": ["fixture"],
    "last_updated": "2026-08-17",
    "release_origin": "v0.4.3",
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


def test_valid_atom_with_allowlisted_heading_has_no_errors_or_warnings(tmp_path: Path) -> None:
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


def test_unknown_heading_is_a_warning_not_an_error(tmp_path: Path) -> None:
    schema = load_frontmatter_schema()
    path = _make_atom(
        tmp_path, slug="test-atom", body="## A Brand New Never Allowlisted Heading\n\nx\n"
    )

    result = lint_atom(path, tmp_path, schema)

    assert not result.has_errors
    assert result.has_warnings
    assert any("not in the curated allowlist" in w for w in result.warnings)


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
        'last_updated: "2026-08-17"\n'
        'release_origin: "v0.4.3"\n'
        "---\n\n## Purpose\n\nBody.\n"
    )
    path = tmp_path / "test-atom.md"
    path.write_text(content, encoding="utf-8")

    result = lint_atom(path, tmp_path, schema)

    assert result.has_errors
    assert any("title" in e for e in result.errors)


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


def test_workspace_allowlist_extends_the_curated_set(tmp_path: Path) -> None:
    (tmp_path / ".heading-allowlist").write_text(
        "# comment\nA Workspace-Specific Heading\n\nAnother One\n", encoding="utf-8"
    )

    loaded = load_workspace_allowlist(tmp_path)

    assert loaded == frozenset({"A Workspace-Specific Heading", "Another One"})
    assert "A Workspace-Specific Heading" not in HEADING_ALLOWLIST  # curated set untouched


def test_workspace_allowlist_absent_file_is_empty(tmp_path: Path) -> None:
    assert load_workspace_allowlist(tmp_path) == frozenset()


@pytest.mark.parametrize(
    ("shape", "expected_exit"),
    [
        pytest.param("clean", 0, id="clean-exit-0"),
        pytest.param("warn", 2, id="warn-only-exit-2"),
        pytest.param("error", 1, id="error-exit-1"),
    ],
)
def test_main_end_to_end_exit_codes(tmp_path: Path, shape: str, expected_exit: int) -> None:
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    if shape == "clean":
        _make_atom(mem_dir, slug="test-atom", body="## Purpose\n\nclean\n")
    elif shape == "warn":
        _make_atom(mem_dir, slug="test-atom", body="## Never Allowlisted\n\nwarn only\n")
    else:
        _make_atom(mem_dir, slug="test-atom", body="## Changelog\n\nforbidden\n")

    assert main(["--memory-dir", str(mem_dir)]) == expected_exit


# ---------------------------------------------------------------------------
# Ported from the deleted tests/unit/scripts/test_lint_memory_atoms.py — these four
# checks validate REAL on-disk public assets against this package's canon and were
# never duplicates of the behavioral tests above (see the module docstring).
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


def test_scaffold_atom_headings_are_allowlisted() -> None:
    """Every ``##`` heading of the LINTED scaffold atoms is curated-allowlisted.

    Scope mirrors ``lint_directory``'s exclusions: ``public/scaffold/memory/**/*.md``
    minus ``AGENTS.md`` (a directory contract, never linted) and ``index.md`` (a
    generated TOC). AGENTS.md governance headings must never enter the allowlist
    (v0.1.49 FR3) — a fresh scaffold must lint clean with NO workspace file.
    """
    scaffold_memory = _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold" / "memory"
    assert scaffold_memory.is_dir()
    missing: list[str] = []
    for md in sorted(scaffold_memory.glob("**/*.md")):
        if md.name in {"AGENTS.md", "index.md"}:
            continue
        for heading in _extract_h2_headings(md.read_text(encoding="utf-8")):
            if heading not in HEADING_ALLOWLIST:
                missing.append(f"{md.name}: {heading}")
    assert missing == [], f"scaffold headings missing from allowlist: {missing}"


def test_memory_feature_template_headings_are_allowlisted() -> None:
    """Bug: `dadaia memory product add` emits an atom from
    ``public/templates/memory-feature.md``; every ``##`` heading it writes must be
    curated-allowlisted, or the supported "add a feature" path yields an atom that
    ``specs doctor`` immediately flags LINT-1 (unknown heading) — the product's own
    template contradicting its own linter, so a context can never reach 0 warnings."""
    template = _REPO_ROOT / "dadaia_workspace" / "public" / "templates" / "memory-feature.md"
    assert template.is_file()
    missing = [
        heading
        for heading in _extract_h2_headings(template.read_text(encoding="utf-8"))
        if heading not in HEADING_ALLOWLIST
    ]
    assert missing == [], f"memory-feature template headings missing from allowlist: {missing}"


@pytest.mark.parametrize(
    ("name", "required_headings"),
    [
        (
            # T-PIO-09 (F9): legitimate current-atom headings must NOT warn.
            "legitimate_canon_headings",
            [
                "Acquire do lease (O_EXCL CAS + stable-session-identity)",
                "Adoção (9 agentes core)",
                "Agent roster and phase ownership (constitution §14 + §7)",
                "Blocking and resume",
                "CI matrix 3-OS (graduated — hard-gated)",
                "Contrato de resiliência — 3 tiers",
                "Core services",
                "Current limits",
                "Dispatcher purity (constitution §9)",
                "Fluxo de dados — gate v3 SDD (v0.1.14: entrypoint merged pre_gate)",
                "Gating note (current behavior)",
                "Harness runtime boundary",
                "Hygiene and anti-slop behavior",
                "Model assignments (9 core agents)",
                "Modelo de concorrência e lease (v0.1.14)",
                "Multi-harness runtime parity (constitution §4)",
                "Os 3 canais de reporte/comunicação (constitution §11)",
                "O Spec Context Project (conceito central)",
                "Plataforma seam — `core/platform.py`",
                "Portos e adapters (4 + 9)",
                "Public surface counts (v0.2.0)",
                "Purpose",
                "Python governance hooks package",
                "Structured-memory-source subsystem (memory-markdown-source-v1)",
                "Sub-agent model (constitution §9)",
                "Topologia de agentes (9 core)",
            ],
        ),
        (
            # T-46-23 (DRIFT-5): v0.1.25-v0.1.45 workflow/backlog subsystem headings.
            "group_e_workflow_headings",
            [
                "Backlog-consistency subsystem (`features/backlog/`, v0.1.25)",
                "Workflow control plane subsystem (v0.1.28 + v0.1.29)",
                "Workflow-step handoff data plane (v0.1.30)",
                "Workflows control plane (v0.1.28, redesenhado em v0.1.45)",
                "Workflow model governance (control plane, v0.1.28)",
                "Harness as a governed dimension (v0.1.29)",
                "Gating note (review-only typed gate + coherent worker-output contract)",
            ],
        ),
        (
            # v0.1.48 W3 (F-79): the 4 post-W2 architecture.md headings + EN canon
            # forms pre-added for the W4 rename.
            "architecture_current_and_english_forms",
            [
                "Modelo de concorrência e lease",
                "Backlog-consistency subsystem (`features/backlog/`)",
                "Workflow control plane subsystem",
                "Workflow-step handoff data plane",
                "Concurrency and lease model",
            ],
        ),
    ],
)
def test_allowlist_content_pins(name: str, required_headings: list[str]) -> None:
    missing = [h for h in required_headings if h not in HEADING_ALLOWLIST]
    assert not missing, f"{name}: headings missing from allowlist: {missing}"
