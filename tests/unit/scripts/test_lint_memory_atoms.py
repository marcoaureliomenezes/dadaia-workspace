"""Unit tests for dadaia_workspace/public/scripts/lint-memory-atoms.py.

Coverage:
  - Valid atom with all required fields passes lint (exit 0)
  - Missing required frontmatter field / extra field / no frontmatter / slug mismatch → ERROR
  - Forbidden headings ('## Changelog', '## Histórico', etc.) → ERROR
  - Broken / valid / product-subdir [[wikilink]] resolution
  - Duplicate ## heading → ERROR; unknown heading → WARN
  - Token estimate drift > 20% → WARN; within tolerance → OK
  - lint_directory scan scope + main() exit codes
  - Allowlist content pins (curated + workspace-extension) and the widening-does-not-
    disable-check negative guard

CRIT-adjacent: allowlist-content pins are giant string tables — one param fn keeps them
auditable without 4 bodies.
"""

from __future__ import annotations

import importlib.util
import json
import types
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Locate the script and schema
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "dadaia_workspace" / "public" / "scripts" / "lint-memory-atoms.py"
_SCHEMA_PATH = (
    _REPO_ROOT
    / "dadaia_workspace"
    / "public"
    / "schemas"
    / "memory"
    / "memory-frontmatter-v1.schema.json"
)

# ---------------------------------------------------------------------------
# Import the module (editable install makes this possible)
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location("lint_memory_atoms", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_lint_mod: types.ModuleType = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lint_mod)  # type: ignore[union-attr]

lint_atom = _lint_mod.lint_atom
lint_directory = _lint_mod.lint_directory
_load_schema = _lint_mod._load_schema
_exit_code = _lint_mod._exit_code
main = _lint_mod.main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_frontmatter(
    slug: str = "test-atom",
    overrides: dict[str, Any] | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> str:
    """Return a YAML frontmatter block string with all required fields."""
    fm: dict[str, Any] = {
        "slug": slug,
        "title": "Test Atom",
        "category": "product",
        "tldr": "A short description under 160 characters.",
        "summary": "One to two sentence summary.",
        "tags": ["test", "unit"],
        # token_estimate=0 skips drift warning (actual == 0 guard in lint_atom)
        "token_estimate": 0,
        "last_updated": "2026-06-01",
        "release_origin": "memory-markdown-source-v1",
    }
    if overrides:
        fm.update(overrides)
    if extra_fields:
        fm.update(extra_fields)

    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v!r}")
    lines.append("---")
    lines.append("")  # trailing newline before body
    return "\n".join(lines) + "\n"


def _make_atom(
    tmp_path: Path,
    slug: str = "test-atom",
    body: str = "## Propósito\n\nThis is the body.\n",
    frontmatter_overrides: dict[str, Any] | None = None,
    extra_fm_fields: dict[str, Any] | None = None,
    filename: str | None = None,
) -> Path:
    """Write a .md atom file and return its Path."""
    fm_block = _valid_frontmatter(
        slug=slug,
        overrides=frontmatter_overrides,
        extra_fields=extra_fm_fields,
    )
    content = fm_block + body
    fname = filename or f"{slug}.md"
    md_path = tmp_path / fname
    md_path.write_text(content, encoding="utf-8")
    return md_path


def _load_schema_real() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Schema contract pin: agent_tier dropped (v0.1.61 D-1; deprecated v0.1.53)
# ---------------------------------------------------------------------------


def test_agent_tier_property_absent_from_schema() -> None:
    """The expired ``agent_tier`` property must stay out of the schema.

    Deprecated in v0.1.53 (zero runtime consumers) and dropped in v0.1.61
    (D-1; zero carriers among all memory atoms). With
    ``additionalProperties: false`` its absence means any atom carrying
    ``agent_tier`` is a hard validation error — this pin prevents silent
    re-introduction.
    """
    schema = _load_schema_real()
    assert "agent_tier" not in schema["properties"]
    assert "agent_tier" not in schema.get("required", [])


# ---------------------------------------------------------------------------
# Test: valid atom passes + exit codes (0/1/2), incl. main() driving lint_atom
# ---------------------------------------------------------------------------


def test_valid_atom_passes_and_exit_codes(tmp_path: Path) -> None:
    """A valid atom with all required fields and a canonical heading passes lint
    (exit 0); warnings-only exits 2; errors exit 1 — both via _exit_code and
    end-to-end via main()."""
    schema = _load_schema_real()
    clean_path = _make_atom(tmp_path, slug="test-atom")
    clean_result = lint_atom(clean_path, tmp_path, schema)
    assert not clean_result.has_errors, f"Unexpected errors: {clean_result.errors}"
    assert not clean_result.has_warnings, f"Unexpected warnings: {clean_result.warnings}"
    assert _exit_code([clean_result]) == 0

    warn_dir = tmp_path / "warn"
    warn_dir.mkdir()
    warn_path = _make_atom(
        warn_dir,
        slug="test-atom",
        body="## Propósito\n\nBody.\n\n## ZZZ Unknown Heading\n\nContent.\n",
    )
    warn_result = lint_atom(warn_path, warn_dir, schema)
    assert _exit_code([warn_result]) == 2

    main_clean_dir = tmp_path / "main-clean"
    main_clean_dir.mkdir()
    _make_atom(main_clean_dir, slug="test-atom")
    assert main(["--memory-dir", str(main_clean_dir)]) == 0

    main_bad_dir = tmp_path / "main-bad"
    main_bad_dir.mkdir()
    _make_atom(
        main_bad_dir,
        slug="test-atom",
        body="## Propósito\n\nOK.\n\n## Changelog\n\nHistory.\n",
    )
    assert main(["--memory-dir", str(main_bad_dir)]) == 1


# ---------------------------------------------------------------------------
# Test: structural ERROR conditions (missing field / extra field / no frontmatter /
# slug mismatch)
# ---------------------------------------------------------------------------


def _missing_title_content() -> str:
    return (
        "---\n"
        "slug: test-atom\n"
        # title is missing
        "category: product\n"
        "tldr: Short description.\n"
        "summary: Two sentence summary.\n"
        "tags:\n  - foo\n"
        "token_estimate: 50\n"
        "last_updated: '2026-06-01'\n"
        "release_origin: memory-markdown-source-v1\n"
        "---\n"
        "\n"
        "## Propósito\n\nBody text.\n"
    )


@pytest.mark.parametrize(
    ("name", "build_fn", "expect_fragments"),
    [
        (
            "missing_required_field",
            lambda tp: (tp / "test-atom.md", _missing_title_content()),
            ["title", "required"],
        ),
        (
            "extra_frontmatter_field",
            lambda tp: (
                _make_atom(tp, slug="test-atom", extra_fm_fields={"unexpected_key": "some_value"}),
                None,
            ),
            ["additional", "unexpected"],
        ),
        (
            "no_frontmatter",
            lambda tp: (
                tp / "test-atom.md",
                "## Propósito\n\nJust body, no frontmatter.\n",
            ),
            ["frontmatter"],
        ),
        (
            "slug_mismatch",
            lambda tp: (
                _make_atom(tp, slug="correct-slug", filename="wrong-stem.md"),
                None,
            ),
            ["slug", "stem", "filename"],
        ),
    ],
)
def test_structural_error_table(
    tmp_path: Path, name: str, build_fn: object, expect_fragments: list[str]
) -> None:
    schema = _load_schema_real()
    path, content = build_fn(tmp_path)  # type: ignore[operator]
    if content is not None:
        path.write_text(content, encoding="utf-8")

    result = lint_atom(path, tmp_path, schema)

    assert result.has_errors, f"Expected ERROR for case {name}"
    assert any(any(frag in e.lower() for frag in expect_fragments) for e in result.errors), (
        f"Error should mention one of {expect_fragments}. Got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# Test: forbidden headings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "heading",
    ["Changelog", "Histórico", "History", "Versions", "CHANGELOG", "changelog"],
)
def test_forbidden_heading_errors(tmp_path: Path, heading: str) -> None:
    """Any forbidden heading variant produces an ERROR."""
    schema = _load_schema_real()
    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        body=f"## Propósito\n\nBody text.\n\n## {heading}\n\nSome history.\n",
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert result.has_errors, f"Expected ERROR for forbidden heading '## {heading}'"
    assert any("forbidden" in e.lower() or heading.lower() in e.lower() for e in result.errors), (
        f"Error should mention the forbidden heading. Got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# Test: wikilinks (broken / valid / product-subdir)
# ---------------------------------------------------------------------------


def test_wikilinks_broken_valid_and_product_subdir(tmp_path: Path) -> None:
    schema = _load_schema_real()

    # Broken: no matching .md file → ERROR naming the slug.
    broken_dir = tmp_path / "broken"
    broken_dir.mkdir()
    broken = _make_atom(
        broken_dir,
        slug="test-atom",
        body="## Propósito\n\nSee [[non-existent-slug]] for details.\n",
    )
    broken_result = lint_atom(broken, broken_dir, schema)
    assert broken_result.has_errors, "Expected ERROR for broken wikilink"
    assert any("non-existent-slug" in e for e in broken_result.errors)

    # Valid: resolves to a co-located .md file → no error.
    valid_dir = tmp_path / "valid"
    valid_dir.mkdir()
    (valid_dir / "other-atom.md").write_text(
        "---\nslug: other-atom\n---\n\nBody.\n", encoding="utf-8"
    )
    valid_atom = _make_atom(
        valid_dir, slug="test-atom", body="## Propósito\n\nSee [[other-atom]] for details.\n"
    )
    valid_result = lint_atom(valid_atom, valid_dir, schema)
    assert not any("other-atom" in e for e in valid_result.errors)

    # Product-subdir: resolves against a product/ subdirectory too.
    prod_dir = tmp_path / "prod"
    prod_dir.mkdir()
    (prod_dir / "product").mkdir()
    (prod_dir / "product" / "other-atom.md").write_text(
        "---\nslug: other-atom\n---\n\nBody.\n", encoding="utf-8"
    )
    prod_atom = _make_atom(prod_dir, slug="test-atom", body="## Propósito\n\nSee [[other-atom]].\n")
    prod_result = lint_atom(prod_atom, prod_dir, schema)
    assert not any("other-atom" in e for e in prod_result.errors)


# ---------------------------------------------------------------------------
# Test: duplicate heading (ERROR) + unknown heading (WARN, not ERROR)
# ---------------------------------------------------------------------------


def test_duplicate_errors_and_unknown_warns(tmp_path: Path) -> None:
    schema = _load_schema_real()

    dup_atom = _make_atom(
        tmp_path,
        slug="test-atom",
        body="## Propósito\n\nFirst section.\n\n## Propósito\n\nDuplicated.\n",
    )
    dup_result = lint_atom(dup_atom, tmp_path, schema)
    assert dup_result.has_errors, "Expected ERROR for duplicate heading"
    assert any("duplicate" in e.lower() for e in dup_result.errors)

    unknown_dir = tmp_path / "unknown"
    unknown_dir.mkdir()
    unknown_atom = _make_atom(
        unknown_dir,
        slug="test-atom",
        body="## Propósito\n\nBody.\n\n## Unknown Heading Not In Allowlist\n\nContent.\n",
    )
    unknown_result = lint_atom(unknown_atom, unknown_dir, schema)
    assert not unknown_result.has_errors, (
        f"Unknown heading should not ERROR. Got: {unknown_result.errors}"
    )
    assert unknown_result.has_warnings, "Unknown heading should produce a WARNING"
    assert any("allowlist" in w.lower() or "unknown" in w.lower() for w in unknown_result.warnings)


def test_widening_does_not_disable_heading_check(tmp_path: Path) -> None:
    """T-46-23 (DRIFT-5) NEGATIVE test: the allowlist widening for the known
    workflow/backlog headings must NOT weaken the check. A genuinely-unknown heading
    that merely *resembles* the widened ones (same version-tag style) is NOT in the
    allowlist and MUST still produce a WARN. The widening adds exactly the enumerated
    known strings — it does not turn the heading gate into a no-op.
    """
    unknown = "Totally Fabricated subsystem (v9.9.9)"
    assert unknown not in _lint_mod.HEADING_ALLOWLIST, (
        "Test precondition: the fabricated heading must not be in the allowlist."
    )

    schema = _load_schema_real()
    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        body=f"## Propósito\n\nBody.\n\n## {unknown}\n\nContent.\n",
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert not result.has_errors, f"Unknown heading should not ERROR. Got: {result.errors}"
    assert result.has_warnings, "A heading outside the widened allowlist must still WARN"
    assert any("allowlist" in w.lower() or unknown.lower() in w.lower() for w in result.warnings), (
        f"Warning should mention the allowlist / the unknown heading. Got: {result.warnings}"
    )


# ---------------------------------------------------------------------------
# Test: token_estimate drift (warn) vs within tolerance (ok)
# ---------------------------------------------------------------------------


def test_token_estimate_drift_and_tolerance(tmp_path: Path) -> None:
    schema = _load_schema_real()

    # Body with ~100 words; token_estimate set to 1 (huge drift).
    drift_body = "## Propósito\n\n" + " ".join(["word"] * 100) + "\n"
    drift_atom = _make_atom(
        tmp_path,
        slug="test-atom",
        frontmatter_overrides={"token_estimate": 1},
        body=drift_body,
    )
    drift_result = lint_atom(drift_atom, tmp_path, schema)
    assert drift_result.has_warnings, "Expected WARN for large token_estimate drift"
    assert any("drift" in w.lower() or "token" in w.lower() for w in drift_result.warnings)

    # ~100 words → estimated tokens ~135; set token_estimate to 135 (0% drift).
    ok_dir = tmp_path / "ok"
    ok_dir.mkdir()
    ok_body = "## Propósito\n\n" + " ".join(["word"] * 100) + "\n"
    ok_atom = _make_atom(
        ok_dir, slug="test-atom", frontmatter_overrides={"token_estimate": 135}, body=ok_body
    )
    ok_result = lint_atom(ok_atom, ok_dir, schema)
    assert not ok_result.has_warnings, f"Expected no token drift warning. Got: {ok_result.warnings}"


# ---------------------------------------------------------------------------
# Test: lint_directory scan scope (product subdir + empty dir)
# ---------------------------------------------------------------------------


def test_lint_directory_scans_product_subdir_and_empty_is_noop(tmp_path: Path) -> None:
    schema = _load_schema_real()

    _make_atom(tmp_path, slug="top-atom", filename="top-atom.md")
    product_dir = tmp_path / "product"
    product_dir.mkdir()
    _make_atom(product_dir, slug="prod-atom", filename="prod-atom.md")

    results = lint_directory(tmp_path, schema)
    slugs = {r.path.stem for r in results}
    assert "top-atom" in slugs
    assert "prod-atom" in slugs
    assert len(results) == 2

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert lint_directory(empty_dir, schema) == []


# ---------------------------------------------------------------------------
# v0.1.49 FR3 — workspace allowlist extension
# ---------------------------------------------------------------------------


def test_workspace_allowlist_load_and_merge(tmp_path: Path) -> None:
    """Absent -> empty; malformed lines ignored; a listed consumer heading stops
    warning; the curated check is unchanged with no extension file present."""
    absent_dir = tmp_path / "absent"
    absent_dir.mkdir()
    assert _lint_mod.load_workspace_allowlist(absent_dir) == frozenset()

    malformed_dir = tmp_path / "malformed"
    malformed_dir.mkdir()
    (malformed_dir / ".heading-allowlist").write_text(
        "\n   \n# comment only\nReal Heading\n", encoding="utf-8"
    )
    assert _lint_mod.load_workspace_allowlist(malformed_dir) == frozenset({"Real Heading"})

    merge_dir = tmp_path / "merge"
    merge_dir.mkdir()
    (merge_dir / ".heading-allowlist").write_text(
        "# consumer extensions\nMy Custom Section\n", encoding="utf-8"
    )
    schema = _load_schema_real()
    md_path = _make_atom(merge_dir, body="## My Custom Section\n\nBody.\n")
    results = lint_directory(merge_dir, schema)
    [result] = [r for r in results if r.path == md_path]
    assert not any("allowlist" in w for w in result.warnings), result.warnings

    no_ext_dir = tmp_path / "no-ext"
    no_ext_dir.mkdir()
    no_ext_atom = _make_atom(no_ext_dir, body="## Not A Canon Heading\n\nBody.\n")
    no_ext_results = lint_directory(no_ext_dir, schema)
    [no_ext_result] = [r for r in no_ext_results if r.path == no_ext_atom]
    assert any("allowlist" in w for w in no_ext_result.warnings)


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
        for heading in _lint_mod._extract_h2_headings(md.read_text(encoding="utf-8")):
            if heading not in _lint_mod.HEADING_ALLOWLIST:
                missing.append(f"{md.name}: {heading}")
    assert missing == [], f"scaffold headings missing from allowlist: {missing}"


# ---------------------------------------------------------------------------
# Allowlist content pins — kept in one param fn so the giant string tables stay
# auditable without 4 separate bodies.
# ---------------------------------------------------------------------------


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
                "Model assignments (9 core agents + 3 plugin stubs)",
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
                "Topologia de agentes (9 core + 3 plugins)",
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
    allowlist = _lint_mod.HEADING_ALLOWLIST
    missing = [h for h in required_headings if h not in allowlist]
    assert not missing, f"{name}: headings missing from allowlist: {missing}"


def test_english_and_portuguese_group_a_canon_pass(tmp_path: Path) -> None:
    """F-79 (v0.1.48 W3): the ENGLISH Group-A canon headings pass lint with no
    warnings, and PT Group-A entries are KEPT — consumer workspaces carry PT atoms."""
    schema = _load_schema_real()

    en_dir = tmp_path / "en"
    en_dir.mkdir()
    en_body = (
        "## Purpose\n\nBody.\n\n"
        "## Usage flow\n\nBody.\n\n"
        "## Typical trigger\n\nBody.\n\n"
        "## Differentiator\n\nBody.\n\n"
        "## Runtime state touched\n\nBody.\n\n"
        "## Dependencies\n\nBody.\n"
    )
    en_atom = _make_atom(en_dir, slug="test-atom", body=en_body)
    en_result = lint_atom(en_atom, en_dir, schema)
    assert not en_result.has_errors, f"EN Group-A canon must not ERROR. Got: {en_result.errors}"
    assert not en_result.has_warnings, f"EN Group-A canon must not WARN. Got: {en_result.warnings}"

    pt_dir = tmp_path / "pt"
    pt_dir.mkdir()
    pt_body = (
        "## Propósito\n\nBody.\n\n"
        "## Fluxo de uso\n\nBody.\n\n"
        "## Trigger típico\n\nBody.\n\n"
        "## Diferencial\n\nBody.\n\n"
        "## Estado runtime tocado\n\nBody.\n\n"
        "## Dependências\n\nBody.\n"
    )
    pt_atom = _make_atom(pt_dir, slug="test-atom", body=pt_body)
    pt_result = lint_atom(pt_atom, pt_dir, schema)
    assert not pt_result.has_errors, f"PT Group-A legacy must not ERROR. Got: {pt_result.errors}"
    assert not pt_result.has_warnings, f"PT Group-A legacy must not WARN. Got: {pt_result.warnings}"
