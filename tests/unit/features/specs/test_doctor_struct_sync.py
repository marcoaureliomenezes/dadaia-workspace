"""Tests for STRUCT-1..4, YAML-absent guard, #8-retire, and SYNC-1 checks.

Release: memory-structured-source-v1 / Cluster C-3
Tasks:   T-MSS-04a (STRUCT checks + YAML-absent guard + #8 retire)
         T-MSS-04b (SYNC-1)

Coverage targets
----------------
AC-C3-1: STRUCT error on YAML atom with extra `changelog` field.
AC-C3-2: STRUCT error on YAML atom missing a required field.
AC-C3-3: SYNC-1 WARN when committed HTML diverges from renderer output for a valid YAML atom.
AC-C3-4: WARN (not error) for HTML-only atoms; doctor exits 0 (WARN-only mode).
          WARN text contains `dadaia migrate memory-yaml`.
AC-C3-5: Check #8 skipped for atoms where a valid YAML source is present.
AC-C3-6: Doctor exits 0 when all YAML atoms valid + HTML in sync.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue
from dadaia_workspace.features.specs.renderer import render_atom

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures" / "memory"
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"

# Fixture paths
_FEAT_VALID = _FIXTURES_DIR / "product-feature.valid.yaml"
_FEAT_INVALID_CHANGELOG = _FIXTURES_DIR / "product-feature.invalid-changelog.yaml"
_FEAT_INVALID_MISSING = _FIXTURES_DIR / "product-feature.invalid-missing-required.yaml"
_ARCH_VALID = _FIXTURES_DIR / "architecture.valid.yaml"
_ARCH_INVALID_CHANGELOG = _FIXTURES_DIR / "architecture.invalid-changelog.yaml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_MEMORY_ARCHITECTURE = """<!DOCTYPE html><html><head>
<title>Architecture</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head><body>
<h1>Architecture Memory</h1>
<p>Layers.</p>
</body></html>"""

MINIMAL_MEMORY_TECH_STACK = """<!DOCTYPE html><html><head>
<title>Tech</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head><body>
<h1>Tech Stack Memory</h1>
<table><tr><th>X</th></tr></table>
</body></html>"""

MINIMAL_MEMORY_PRODUCT_INDEX = """<!DOCTYPE html><html><head>
<title>Product</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head><body>
<h1>Product Memory</h1>
<p>Current state.</p>
</body></html>"""

MINIMAL_MEMORY_PRODUCT_FEATURE = """<!DOCTYPE html><html><head>
<title>Feature A</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head><body>
<h1>Feature — A</h1>
<h2>Propósito</h2><p>It does A.</p>
</body></html>"""

# HTML content with a forbidden <h2>Changelog</h2> — used in check-#8-retire tests.
HTML_WITH_CHANGELOG = """<!DOCTYPE html><html><head>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head><body>
<h1>Feature — with changelog</h1>
<h2>Changelog</h2><p>v1 fix.</p>
</body></html>"""


def _make_minimal_specs(root: Path, release_id: str = "r1") -> Path:
    """Build a minimal but valid specs/ tree for STRUCT/SYNC tests.

    Memory atoms are HTML-only (no YAML) — this represents a pre-migration
    consumer repo.
    """
    specs = root / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / release_id).mkdir(parents=True)
    (specs / "_archive" / "releases").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)

    (specs / "constitution.md").write_text("# Constitution\n\nThe laws.\n", encoding="utf-8")
    (specs / "memory" / "architecture.html").write_text(MINIMAL_MEMORY_ARCHITECTURE, encoding="utf-8")
    (specs / "memory" / "tech-stack.html").write_text(MINIMAL_MEMORY_TECH_STACK, encoding="utf-8")
    (specs / "memory" / "product" / "index.html").write_text(
        MINIMAL_MEMORY_PRODUCT_INDEX, encoding="utf-8"
    )
    (specs / "memory" / "product" / "feature-a.html").write_text(
        MINIMAL_MEMORY_PRODUCT_FEATURE, encoding="utf-8"
    )
    (specs / "releases" / "ACTIVE.md").write_text(
        f"release: {release_id}\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    spec_md = "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-04-01\n\nContent.\n"
    plan_md = "# Plan\n\n> **Status:** Aprovado\n\nShort.\n"
    tasks_md = "# Tasks\n\n> **Status:** Aprovado\n\n- [-] T1 something\n"
    (specs / "releases" / release_id / "SPEC.md").write_text(spec_md, encoding="utf-8")
    (specs / "releases" / release_id / "PLAN.md").write_text(plan_md, encoding="utf-8")
    (specs / "releases" / release_id / "TASKS.md").write_text(tasks_md, encoding="utf-8")
    return specs


def _codes(issues: list[SpecsDoctorIssue]) -> set[str]:
    return {i.code for i in issues}


def _struct_issues(issues: list[SpecsDoctorIssue]) -> list[SpecsDoctorIssue]:
    return [i for i in issues if i.code.startswith("STRUCT-")]


def _errors(issues: list[SpecsDoctorIssue]) -> list[SpecsDoctorIssue]:
    return [i for i in issues if i.severity == Severity.ERROR]


def _warnings(issues: list[SpecsDoctorIssue]) -> list[SpecsDoctorIssue]:
    return [i for i in issues if i.severity == Severity.WARNING]


# ---------------------------------------------------------------------------
# AC-C3-1: STRUCT error on YAML atom with extra `changelog` field
# ---------------------------------------------------------------------------


def test_struct_error_extra_changelog_field_feature(tmp_path: Path) -> None:
    """AC-C3-1: YAML atom with a `changelog` field triggers STRUCT-4 ERROR (feature atom)."""
    specs = _make_minimal_specs(tmp_path)
    # Place the invalid-changelog feature YAML in product/
    slug_yaml = specs / "memory" / "product" / "workspace-init.yaml"
    shutil.copy2(_FEAT_INVALID_CHANGELOG, slug_yaml)

    issues = SpecsDoctor(specs).check()
    # Filter to STRUCT-4 errors specifically (not YAML-absent WARNings)
    struct4_errors = [
        i for i in issues
        if i.code == "STRUCT-4" and i.severity == Severity.ERROR
    ]
    assert struct4_errors, (
        "Expected STRUCT-4 ERROR for feature atom with changelog field; "
        f"all STRUCT-4: {[i.to_dict() for i in issues if i.code == 'STRUCT-4']}"
    )
    # Error message must reference the atom path
    descriptions = " ".join(i.description for i in struct4_errors)
    assert "changelog" in descriptions.lower() or "additional" in descriptions.lower(), (
        f"Expected changelog/additionalProperties mention; got: {descriptions}"
    )


def test_struct_error_extra_changelog_field_architecture(tmp_path: Path) -> None:
    """AC-C3-1 (architecture): YAML atom with a `changelog` field triggers STRUCT-1 ERROR."""
    specs = _make_minimal_specs(tmp_path)
    arch_yaml = specs / "memory" / "architecture.yaml"
    shutil.copy2(_ARCH_INVALID_CHANGELOG, arch_yaml)

    issues = SpecsDoctor(specs).check()
    struct1_errors = [i for i in issues if i.code == "STRUCT-1" and i.severity == Severity.ERROR]
    assert struct1_errors, (
        "Expected STRUCT-1 ERROR for architecture atom with changelog field; "
        f"all STRUCT-1: {[i.to_dict() for i in issues if i.code == 'STRUCT-1']}"
    )


# ---------------------------------------------------------------------------
# AC-C3-2: STRUCT error on YAML atom missing a required field
# ---------------------------------------------------------------------------


def test_struct_error_missing_required_field_feature(tmp_path: Path) -> None:
    """AC-C3-2: YAML feature atom missing `purpose` triggers STRUCT-4 ERROR."""
    specs = _make_minimal_specs(tmp_path)
    slug_yaml = specs / "memory" / "product" / "workspace-init.yaml"
    shutil.copy2(_FEAT_INVALID_MISSING, slug_yaml)

    issues = SpecsDoctor(specs).check()
    struct4_errors = [
        i for i in issues
        if i.code == "STRUCT-4" and i.severity == Severity.ERROR
    ]
    assert struct4_errors, (
        "Expected STRUCT-4 ERROR for feature atom missing 'purpose'; "
        f"all STRUCT-4: {[i.to_dict() for i in issues if i.code == 'STRUCT-4']}"
    )
    descriptions = " ".join(i.description for i in struct4_errors)
    assert "purpose" in descriptions.lower() or "required" in descriptions.lower(), (
        f"Expected 'purpose'/'required' in description; got: {descriptions}"
    )


# ---------------------------------------------------------------------------
# AC-C3-4: WARN (not error) for HTML-only atoms; WARN text contains migrate hint
# ---------------------------------------------------------------------------


def test_yaml_absent_guard_emits_warn_not_error(tmp_path: Path) -> None:
    """AC-C3-4: HTML-only atom (no YAML) → WARN (not ERROR). Doctor exits 0."""
    specs = _make_minimal_specs(tmp_path)
    # No YAML files present — pure HTML-only repo (pre-migration state).

    issues = SpecsDoctor(specs).check()

    # Must have STRUCT WARNings for the HTML-only atoms.
    struct_warns = [
        i for i in issues
        if i.code.startswith("STRUCT-") and i.severity == Severity.WARNING
    ]
    assert struct_warns, (
        "Expected STRUCT WARN(s) for HTML-only atoms (YAML-absent guard)"
    )

    # No STRUCT ERRORs allowed — all atoms are HTML-only.
    struct_errors = [
        i for i in issues
        if i.code.startswith("STRUCT-") and i.severity == Severity.ERROR
    ]
    assert struct_errors == [], (
        f"Expected no STRUCT ERRORs for HTML-only repo; got: {[i.description for i in struct_errors]}"
    )

    # Doctor must exit 0 (no errors at all).
    errors = _errors(issues)
    assert errors == [], (
        f"HTML-only repo must have no ERRORs; got: {[i.to_dict() for i in errors]}"
    )


def test_yaml_absent_guard_warn_mentions_migrate_command(tmp_path: Path) -> None:
    """AC-C3-4 + AC-C7-3: WARN text must include `dadaia migrate memory-yaml`."""
    specs = _make_minimal_specs(tmp_path)

    issues = SpecsDoctor(specs).check()
    struct_warns = [
        i for i in issues
        if i.code.startswith("STRUCT-") and i.severity == Severity.WARNING
    ]
    assert struct_warns, "Pre-condition: expected STRUCT WARN(s)"

    all_descriptions = " ".join(i.description for i in struct_warns)
    assert "dadaia migrate memory-yaml" in all_descriptions, (
        f"Expected 'dadaia migrate memory-yaml' in STRUCT WARN description; "
        f"got: {all_descriptions!r}"
    )


# ---------------------------------------------------------------------------
# AC-C3-5: Check #8 skipped when valid YAML present
# ---------------------------------------------------------------------------


def test_check8_skipped_for_atom_with_valid_yaml(tmp_path: Path) -> None:
    """AC-C3-5: A feature HTML with <h2>Changelog</h2> does NOT trigger SPEC-DOC-008
    when a valid YAML source exists for that atom (D-5 redundancy elimination)."""
    specs = _make_minimal_specs(tmp_path)

    # Place an HTML with a forbidden Changelog section…
    slug = "workspace-init"
    (specs / "memory" / "product" / f"{slug}.html").write_text(
        HTML_WITH_CHANGELOG, encoding="utf-8"
    )
    # …BUT also provide a valid YAML source for the same atom.
    slug_yaml = specs / "memory" / "product" / f"{slug}.yaml"
    shutil.copy2(_FEAT_VALID, slug_yaml)
    # Rename the slug inside the YAML copy to match (not required for schema, but clean).

    issues = SpecsDoctor(specs).check()

    # No SPEC-DOC-008 should fire for this atom.
    doc8 = [i for i in issues if i.code == "SPEC-DOC-008" and slug in (i.path or "")]
    assert doc8 == [], (
        f"Expected check #8 to be skipped for {slug} (valid YAML present); "
        f"got: {[i.description for i in doc8]}"
    )


def test_check8_still_fires_for_html_only_atom_with_changelog(tmp_path: Path) -> None:
    """AC-C3-5 complement: HTML-only atom with <h2>Changelog</h2> still triggers SPEC-DOC-008."""
    specs = _make_minimal_specs(tmp_path)

    # feature-a.html already exists; overwrite with changelog content.
    (specs / "memory" / "product" / "feature-a.html").write_text(
        HTML_WITH_CHANGELOG, encoding="utf-8"
    )
    # No YAML for feature-a.

    issues = SpecsDoctor(specs).check()
    doc8 = [i for i in issues if i.code == "SPEC-DOC-008"]
    assert doc8, "Expected SPEC-DOC-008 for HTML-only atom with Changelog section"
    assert any("feature-a" in (i.path or "") for i in doc8), (
        f"Expected SPEC-DOC-008 to name feature-a.html; got: {[i.path for i in doc8]}"
    )


# ---------------------------------------------------------------------------
# AC-C3-3: SYNC-1 WARN when committed HTML diverges from renderer output
# ---------------------------------------------------------------------------


def test_sync1_warn_when_html_diverges_from_yaml(tmp_path: Path) -> None:
    """AC-C3-3: SYNC-1 WARN when committed HTML diverges from renderer output for a valid YAML atom."""
    specs = _make_minimal_specs(tmp_path)

    # Place a valid YAML source for a feature atom.
    slug = "workspace-init"
    slug_yaml = specs / "memory" / "product" / f"{slug}.yaml"
    shutil.copy2(_FEAT_VALID, slug_yaml)

    # Write a DIFFERENT HTML than what the renderer would produce.
    slug_html = specs / "memory" / "product" / f"{slug}.html"
    slug_html.write_text(
        "<html><head><title>stale</title></head><body><h1>Stale HTML</h1></body></html>",
        encoding="utf-8",
    )

    issues = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR).check()

    sync1 = [i for i in issues if i.code == "SYNC-1"]
    assert sync1, "Expected SYNC-1 WARN when committed HTML diverges from renderer output"
    assert all(i.severity == Severity.WARNING for i in sync1), (
        f"SYNC-1 must be WARNING; got: {[i.severity for i in sync1]}"
    )
    # Message must name the specific atom.
    descriptions = " ".join(i.description for i in sync1)
    assert slug in descriptions or "workspace-init" in descriptions, (
        f"Expected atom name in SYNC-1 description; got: {descriptions!r}"
    )


def test_sync1_not_emitted_when_html_matches_renderer(tmp_path: Path) -> None:
    """AC-C3-6 (partial): no SYNC-1 when committed HTML is in sync with YAML source."""
    specs = _make_minimal_specs(tmp_path)

    # Place a valid YAML source for a feature atom.
    slug = "workspace-init"
    slug_yaml = specs / "memory" / "product" / f"{slug}.yaml"
    shutil.copy2(_FEAT_VALID, slug_yaml)

    # Render the YAML to produce the expected HTML.
    rendered = render_atom(slug_yaml, atom_type="memory-product-feature-v1",
                           templates_dir=_TEMPLATES_DIR)
    slug_html = specs / "memory" / "product" / f"{slug}.html"
    slug_html.write_text(rendered, encoding="utf-8")

    issues = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR).check()

    sync1 = [i for i in issues if i.code == "SYNC-1"]
    assert sync1 == [], (
        f"Expected no SYNC-1 when HTML is in sync; got: {[i.description for i in sync1]}"
    )


# ---------------------------------------------------------------------------
# AC-C3-6: Doctor exits 0 when all YAML atoms valid + HTML in sync
# ---------------------------------------------------------------------------


def test_doctor_exits_0_all_yaml_valid_html_in_sync(tmp_path: Path) -> None:
    """AC-C3-6: doctor exits 0 when all YAML atoms are valid and all HTML is in sync."""
    specs = _make_minimal_specs(tmp_path)

    # Add valid YAML for all atom slots + render correct HTML.
    # Architecture
    arch_yaml_src = specs / "memory" / "architecture.yaml"
    shutil.copy2(_ARCH_VALID, arch_yaml_src)
    arch_rendered = render_atom(
        arch_yaml_src, atom_type="memory-architecture-v1", templates_dir=_TEMPLATES_DIR
    )
    (specs / "memory" / "architecture.html").write_text(arch_rendered, encoding="utf-8")

    # Feature atom (workspace-init)
    slug = "workspace-init"
    slug_yaml = specs / "memory" / "product" / f"{slug}.yaml"
    shutil.copy2(_FEAT_VALID, slug_yaml)
    feat_rendered = render_atom(
        slug_yaml, atom_type="memory-product-feature-v1", templates_dir=_TEMPLATES_DIR
    )
    (specs / "memory" / "product" / f"{slug}.html").write_text(feat_rendered, encoding="utf-8")

    issues = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR).check()

    # No errors and no SYNC-1 warnings.
    errors = _errors(issues)
    assert errors == [], (
        f"Expected 0 errors with valid YAML + synced HTML; got: "
        f"{[i.to_dict() for i in errors]}"
    )
    sync1 = [i for i in issues if i.code == "SYNC-1"]
    assert sync1 == [], (
        f"Expected no SYNC-1 when all HTML is in sync; got: {[i.description for i in sync1]}"
    )


# ---------------------------------------------------------------------------
# Regression: existing dadaia-workspace repo still exits 0 (HTML-only → WARN-only)
# ---------------------------------------------------------------------------


def test_dadaia_workspace_repo_still_exits_0_with_new_checks() -> None:
    """CRITICAL regression guard: the dadaia-workspace repo (HTML-only atoms,
    no YAML yet) must still produce 0 ERRORs after the STRUCT/SYNC checks ship.

    This repo's YAML migration is CLOSURE-only (T-MSS-10).  Until then, all atoms
    are HTML-only → YAML-absent guard emits WARNs only.  Doctor must exit 0.
    """
    repo_specs = _REPO_ROOT / "specs"
    if not repo_specs.exists():
        pytest.skip("specs/ not found — not running in dadaia-workspace repo context")

    doctor = SpecsDoctor(repo_specs, public_dir=_PUBLIC_DIR)
    issues = doctor.check()
    errors = _errors(issues)
    assert errors == [], (
        "dadaia-workspace repo triggered ERROR(s) after STRUCT/SYNC checks — "
        "HTML-only atoms must produce WARN-only (YAML-absent guard):\n"
        + "\n".join(f"  {i.code}: {i.description}" for i in errors)
    )


# ---------------------------------------------------------------------------
# STRUCT-1 / STRUCT-2 / STRUCT-3 slot codes
# ---------------------------------------------------------------------------


def test_struct1_architecture_invalid_raises_struct1_not_struct4(tmp_path: Path) -> None:
    """STRUCT-1 specifically for architecture.yaml invalid content."""
    specs = _make_minimal_specs(tmp_path)
    arch_yaml = specs / "memory" / "architecture.yaml"
    shutil.copy2(_ARCH_INVALID_CHANGELOG, arch_yaml)

    issues = SpecsDoctor(specs).check()
    struct1_errors = [i for i in issues if i.code == "STRUCT-1" and i.severity == Severity.ERROR]
    assert struct1_errors, (
        "Expected STRUCT-1 ERROR (not STRUCT-4) for architecture.yaml with changelog; "
        f"all STRUCT: {[i.to_dict() for i in issues if i.code.startswith('STRUCT-')]}"
    )
    # No STRUCT-4 ERROR should fire (STRUCT-4 is for feature atoms).
    # Only STRUCT-4 WARNings may appear (for HTML-only feature-a).
    struct4_errors = [
        i for i in issues if i.code == "STRUCT-4" and i.severity == Severity.ERROR
    ]
    assert struct4_errors == [], (
        f"STRUCT-4 ERROR must not fire when architecture.yaml is invalid; got: "
        f"{[i.to_dict() for i in struct4_errors]}"
    )
