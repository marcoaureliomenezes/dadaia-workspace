"""Unit tests for dadaia_workspace/public/scripts/lint-memory-atoms.py.

Coverage:
  - Valid atom with all required fields passes lint (exit 0)
  - Missing required frontmatter field → ERROR (exit 1)
  - Extra/unknown frontmatter field (additionalProperties) → ERROR (exit 1)
  - Forbidden '## Changelog' heading → ERROR (exit 1)
  - Forbidden '## Histórico' heading → ERROR (exit 1)
  - Broken [[wikilink]] → ERROR (exit 1)
  - Duplicate ## heading → ERROR (exit 1)
  - Unknown (not-in-allowlist) ## heading → WARN (exit 2)
  - Token estimate drift > 20% → WARN (exit 2)
  - Token estimate within 20% → OK
  - slug != filename stem → ERROR (exit 1)
  - No frontmatter → ERROR (exit 1)
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
        "agent_tier": "self-pull",
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
# Test: valid atom passes
# ---------------------------------------------------------------------------


def test_valid_atom_passes(tmp_path: Path) -> None:
    """A valid atom with all required fields and a canonical heading passes lint."""
    schema = _load_schema_real()
    md_path = _make_atom(tmp_path, slug="test-atom")

    result = lint_atom(md_path, tmp_path, schema)

    assert not result.has_errors, f"Unexpected errors: {result.errors}"
    assert not result.has_warnings, f"Unexpected warnings: {result.warnings}"


def test_exit_code_clean_is_zero(tmp_path: Path) -> None:
    """_exit_code returns 0 when no errors or warnings in results."""
    schema = _load_schema_real()
    md_path = _make_atom(tmp_path, slug="test-atom")
    results = [lint_atom(md_path, tmp_path, schema)]
    assert _exit_code(results) == 0


# ---------------------------------------------------------------------------
# Test: missing required frontmatter field
# ---------------------------------------------------------------------------


def test_missing_required_field_errors(tmp_path: Path) -> None:
    """Missing a required frontmatter field produces an ERROR."""
    schema = _load_schema_real()
    # Build content without 'title' field — manually
    content = (
        "---\n"
        "slug: test-atom\n"
        # title is missing
        "category: product\n"
        "tldr: Short description.\n"
        "summary: Two sentence summary.\n"
        "tags:\n  - foo\n"
        "agent_tier: self-pull\n"
        "token_estimate: 50\n"
        "last_updated: '2026-06-01'\n"
        "release_origin: memory-markdown-source-v1\n"
        "---\n"
        "\n"
        "## Propósito\n\nBody text.\n"
    )
    md_path = tmp_path / "test-atom.md"
    md_path.write_text(content, encoding="utf-8")

    result = lint_atom(md_path, tmp_path, schema)

    assert result.has_errors, "Expected ERROR for missing 'title' field"
    assert any("title" in e.lower() or "required" in e.lower() for e in result.errors), (
        f"Error message should mention missing field. Got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# Test: extra/unknown frontmatter field (additionalProperties:false)
# ---------------------------------------------------------------------------


def test_extra_frontmatter_field_errors(tmp_path: Path) -> None:
    """An extra unknown frontmatter field triggers an additionalProperties ERROR."""
    schema = _load_schema_real()
    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        extra_fm_fields={"unexpected_key": "some_value"},
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert result.has_errors, "Expected ERROR for unknown frontmatter field"
    assert any("additional" in e.lower() or "unexpected" in e.lower() for e in result.errors), (
        f"Expected additionalProperties error. Got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# Test: forbidden headings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "heading",
    [
        "Changelog",
        "Histórico",
        "History",
        "Versions",
        "CHANGELOG",
        "changelog",
    ],
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
# Test: broken wikilink
# ---------------------------------------------------------------------------


def test_broken_wikilink_errors(tmp_path: Path) -> None:
    """A [[slug]] wikilink that has no matching .md file produces an ERROR."""
    schema = _load_schema_real()
    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        body="## Propósito\n\nSee [[non-existent-slug]] for details.\n",
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert result.has_errors, "Expected ERROR for broken wikilink"
    assert any("non-existent-slug" in e for e in result.errors), (
        f"Error should name the broken slug. Got: {result.errors}"
    )


def test_valid_wikilink_passes(tmp_path: Path) -> None:
    """A [[slug]] wikilink that resolves to an existing .md file is accepted."""
    schema = _load_schema_real()

    # Create the target atom
    target = tmp_path / "other-atom.md"
    target.write_text("---\nslug: other-atom\n---\n\nBody.\n", encoding="utf-8")

    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        body="## Propósito\n\nSee [[other-atom]] for details.\n",
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert not any("other-atom" in e for e in result.errors), (
        f"Valid wikilink should not produce error. Got: {result.errors}"
    )


def test_wikilink_in_product_subdir_resolves(tmp_path: Path) -> None:
    """A [[slug]] wikilink resolves against product/ subdirectory too."""
    schema = _load_schema_real()

    product_dir = tmp_path / "product"
    product_dir.mkdir()
    target = product_dir / "other-atom.md"
    target.write_text("---\nslug: other-atom\n---\n\nBody.\n", encoding="utf-8")

    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        body="## Propósito\n\nSee [[other-atom]].\n",
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert not any("other-atom" in e for e in result.errors), (
        f"Wikilink pointing to product/ atom should resolve. Errors: {result.errors}"
    )


# ---------------------------------------------------------------------------
# Test: duplicate heading
# ---------------------------------------------------------------------------


def test_duplicate_heading_errors(tmp_path: Path) -> None:
    """Duplicate ## heading within a single atom produces an ERROR."""
    schema = _load_schema_real()
    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        body="## Propósito\n\nFirst section.\n\n## Propósito\n\nDuplicated.\n",
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert result.has_errors, "Expected ERROR for duplicate heading"
    assert any("duplicate" in e.lower() for e in result.errors), (
        f"Error should mention 'duplicate'. Got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# Test: unknown heading → WARN not ERROR
# ---------------------------------------------------------------------------


def test_unknown_heading_warns_not_errors(tmp_path: Path) -> None:
    """A ## heading not in the allowlist produces a WARN (not ERROR)."""
    schema = _load_schema_real()
    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        body="## Propósito\n\nBody.\n\n## Unknown Heading Not In Allowlist\n\nContent.\n",
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert not result.has_errors, f"Unknown heading should not ERROR. Got: {result.errors}"
    assert result.has_warnings, "Unknown heading should produce a WARNING"
    assert any("allowlist" in w.lower() or "unknown" in w.lower() for w in result.warnings), (
        f"Warning should mention allowlist. Got: {result.warnings}"
    )


def test_legitimate_canon_headings_in_allowlist() -> None:
    """T-PIO-09 (F9): legitimate current-atom headings must NOT warn.

    The drift audit flagged these real headings from architecture / lifecycle-foundation
    / spec-context-project / multi-platform-parity / agent atoms as LINT-1 WARNings even
    though they are legitimate canon. They must be in the curated allowlist so
    `specs doctor` stops emitting heading WARNs for existing atoms. No atom content
    changes — only the allowlist grows.
    """
    allowlist = _lint_mod.HEADING_ALLOWLIST
    legitimate = [
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
    ]
    missing = [h for h in legitimate if h not in allowlist]
    assert not missing, f"Legitimate headings still missing from allowlist: {missing}"


def test_group_e_workflow_headings_in_allowlist() -> None:
    """T-46-23 (DRIFT-5): the v0.1.25–v0.1.45 workflow/backlog subsystem headings
    flagged by the v0.1.46 doctor-debt sweep must be in the curated allowlist so
    `specs doctor` stops emitting heading WARNs for those legitimate current canon
    sections. No atom content changes — only the allowlist grows.
    """
    allowlist = _lint_mod.HEADING_ALLOWLIST
    widened = [
        "Backlog-consistency subsystem (`features/backlog/`, v0.1.25)",
        "Workflow control plane subsystem (v0.1.28 + v0.1.29)",
        "Workflow-step handoff data plane (v0.1.30)",
        "Workflows control plane (v0.1.28, redesenhado em v0.1.45)",
        "Workflow model governance (control plane, v0.1.28)",
        "Harness as a governed dimension (v0.1.29)",
        "Gating note (review-only typed gate + coherent worker-output contract)",
    ]
    missing = [h for h in widened if h not in allowlist]
    assert not missing, f"Widened workflow headings still missing from allowlist: {missing}"


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


def test_exit_code_warn_only_is_two(tmp_path: Path) -> None:
    """_exit_code returns 2 when only warnings exist."""
    schema = _load_schema_real()
    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        body="## Propósito\n\nBody.\n\n## ZZZ Unknown Heading\n\nContent.\n",
    )
    results = [lint_atom(md_path, tmp_path, schema)]
    assert _exit_code(results) == 2


# ---------------------------------------------------------------------------
# Test: token_estimate drift
# ---------------------------------------------------------------------------


def test_token_estimate_drift_warns(tmp_path: Path) -> None:
    """token_estimate that is off by > 20% produces a WARN."""
    schema = _load_schema_real()
    # Body with ~100 words; token_estimate set to 1 (huge drift)
    body = "## Propósito\n\n" + " ".join(["word"] * 100) + "\n"
    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        frontmatter_overrides={"token_estimate": 1},
        body=body,
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert result.has_warnings, "Expected WARN for large token_estimate drift"
    assert any("drift" in w.lower() or "token" in w.lower() for w in result.warnings), (
        f"Warning should mention token drift. Got: {result.warnings}"
    )


def test_token_estimate_within_tolerance_no_warn(tmp_path: Path) -> None:
    """token_estimate within 20% of actual does not produce a warning."""
    schema = _load_schema_real()
    # ~100 words → estimated tokens ~135; set token_estimate to 135 (0% drift)
    body = "## Propósito\n\n" + " ".join(["word"] * 100) + "\n"
    md_path = _make_atom(
        tmp_path,
        slug="test-atom",
        frontmatter_overrides={"token_estimate": 135},
        body=body,
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert not result.has_warnings, f"Expected no token drift warning. Got: {result.warnings}"


# ---------------------------------------------------------------------------
# Test: slug != filename stem
# ---------------------------------------------------------------------------


def test_slug_mismatch_errors(tmp_path: Path) -> None:
    """Frontmatter slug that does not match the filename stem produces ERROR."""
    schema = _load_schema_real()
    # slug = "correct-slug" but file named "wrong-stem.md"
    md_path = _make_atom(
        tmp_path,
        slug="correct-slug",
        filename="wrong-stem.md",
    )

    result = lint_atom(md_path, tmp_path, schema)

    assert result.has_errors, "Expected ERROR when slug != filename stem"
    assert any(
        "slug" in e.lower() or "stem" in e.lower() or "filename" in e.lower() for e in result.errors
    ), f"Error should mention slug mismatch. Got: {result.errors}"


# ---------------------------------------------------------------------------
# Test: no frontmatter
# ---------------------------------------------------------------------------


def test_no_frontmatter_errors(tmp_path: Path) -> None:
    """A .md file with no frontmatter block produces an ERROR."""
    schema = _load_schema_real()
    md_path = tmp_path / "test-atom.md"
    md_path.write_text("## Propósito\n\nJust body, no frontmatter.\n", encoding="utf-8")

    result = lint_atom(md_path, tmp_path, schema)

    assert result.has_errors, "Expected ERROR when frontmatter is absent"
    assert any("frontmatter" in e.lower() for e in result.errors), (
        f"Error should mention frontmatter. Got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# Test: lint_directory
# ---------------------------------------------------------------------------


def test_lint_directory_scans_product_subdir(tmp_path: Path) -> None:
    """lint_directory finds atoms in both top-level and product/ subdirectory."""
    schema = _load_schema_real()

    # Top-level atom
    _make_atom(tmp_path, slug="top-atom", filename="top-atom.md")

    # Product atom
    product_dir = tmp_path / "product"
    product_dir.mkdir()
    _make_atom(product_dir, slug="prod-atom", filename="prod-atom.md")

    results = lint_directory(tmp_path, schema)

    slugs = {r.path.stem for r in results}
    assert "top-atom" in slugs
    assert "prod-atom" in slugs
    assert len(results) == 2


def test_lint_directory_empty_returns_no_results(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """lint_directory on an empty dir returns an empty list (not an error)."""
    schema = _load_schema_real()
    results = lint_directory(tmp_path, schema)
    assert results == []


# ---------------------------------------------------------------------------
# Test: main() function exit codes
# ---------------------------------------------------------------------------


def test_main_clean_atom_exit_zero(tmp_path: Path) -> None:
    """main() returns 0 for a directory with a valid atom."""
    _make_atom(tmp_path, slug="test-atom")
    code = main(["--memory-dir", str(tmp_path)])
    assert code == 0, f"Expected exit 0, got {code}"


def test_main_bad_atom_exit_one(tmp_path: Path) -> None:
    """main() returns 1 when an atom has errors."""
    # Atom with forbidden heading
    _make_atom(
        tmp_path,
        slug="test-atom",
        body="## Propósito\n\nOK.\n\n## Changelog\n\nHistory.\n",
    )
    code = main(["--memory-dir", str(tmp_path)])
    assert code == 1, f"Expected exit 1, got {code}"
