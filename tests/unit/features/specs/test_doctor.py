"""Unit tests for SpecsDoctor — covers each of the 11 structural checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue


MINIMAL_MEMORY_PRODUCT_INDEX = """<!DOCTYPE html><html><head>
<title>Product</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head><body>
<h1>Product Memory — example</h1>
<p>Current state.</p>
<h2>Catálogo</h2>
<ol><li><a href="feature-a.html">feature-a</a></li></ol>
</body></html>"""

MINIMAL_MEMORY_PRODUCT_FEATURE = """<!DOCTYPE html><html><head>
<title>Feature A</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head><body>
<h1>Feature — A</h1>
<h2>Propósito</h2><p>It does A.</p>
<h2>Fluxo de uso</h2><ol><li>step</li></ol>
<h2>Trigger típico</h2><p>when needed.</p>
<h2>Diferencial</h2><p>solves nothing else does.</p>
</body></html>"""

MINIMAL_MEMORY_ARCHITECTURE = """<!DOCTYPE html><html><head>
<title>Architecture</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head><body>
<h1>Architecture Memory — example</h1>
<p>Layers.</p>
</body></html>"""

MINIMAL_MEMORY_TECH_STACK = """<!DOCTYPE html><html><head>
<title>Tech</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head><body>
<h1>Tech Stack Memory — example</h1>
<table><tr><th>X</th></tr></table>
</body></html>"""


def _make_clean_specs_tree(root: Path, release_id: str = "r1") -> Path:
    """Create a minimal but valid specs/ tree."""
    specs = root / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / release_id).mkdir(parents=True)
    (specs / "_archive" / "releases").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)

    (specs / "constitution.md").write_text("# Constitution\n\nThe laws.\n", encoding="utf-8")
    (specs / "memory" / "product" / "index.html").write_text(
        MINIMAL_MEMORY_PRODUCT_INDEX, encoding="utf-8"
    )
    (specs / "memory" / "product" / "feature-a.html").write_text(
        MINIMAL_MEMORY_PRODUCT_FEATURE, encoding="utf-8"
    )
    (specs / "memory" / "architecture.html").write_text(
        MINIMAL_MEMORY_ARCHITECTURE, encoding="utf-8"
    )
    (specs / "memory" / "tech-stack.html").write_text(
        MINIMAL_MEMORY_TECH_STACK, encoding="utf-8"
    )
    (specs / "releases" / "ACTIVE.md").write_text(
        f"release: {release_id}\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    spec_md = (
        "# Spec\n\n"
        "> **Status:** Aprovado\n"
        "> **Created:** 2026-04-01\n\n"
        "Content.\n"
    )
    plan_md = "# Plan\n\n> **Status:** Aprovado\n\nShort.\n"
    tasks_md = "# Tasks\n\n> **Status:** Aprovado\n\n- [-] T1 something\n"
    (specs / "releases" / release_id / "SPEC.md").write_text(spec_md, encoding="utf-8")
    (specs / "releases" / release_id / "PLAN.md").write_text(plan_md, encoding="utf-8")
    (specs / "releases" / release_id / "TASKS.md").write_text(tasks_md, encoding="utf-8")
    return specs


def _codes(issues: list[SpecsDoctorIssue]) -> set[str]:
    return {i.code for i in issues}


# ---- check 1: constitution


def test_clean_tree_has_no_errors(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    issues = SpecsDoctor(specs).check()
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == [], errors


def test_missing_constitution_reports_doc_001(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "constitution.md").unlink()
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-001" in _codes(issues)


# ---- check 2: memory files


def test_missing_product_index_reports_doc_002(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "memory" / "product" / "index.html").unlink()
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-002" in _codes(issues)


def test_missing_architecture_html_reports_doc_002(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "memory" / "architecture.html").unlink()
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-002" in _codes(issues)


def test_legacy_memory_markdown_reports_doc_002L(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "memory" / "architecture.md").write_text("# legacy", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-002L" in _codes(issues)


def test_legacy_product_html_at_root_reports_doc_002L(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "memory" / "product.html").write_text(
        "<html><body><h1>x</h1></body></html>", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    matching = [i for i in issues if i.code == "SPEC-DOC-002L" and "product.html is legacy" in i.description]
    assert matching, [i.to_dict() for i in issues]


def test_broken_anchor_in_product_index_reports_doc_002(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    bad_index = """<!DOCTYPE html><html><head>
<script src="mermaid.js"></script>
</head><body>
<h1>Product</h1>
<a href="missing-feature.html">x</a>
</body></html>"""
    (specs / "memory" / "product" / "index.html").write_text(bad_index, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    matching = [
        i for i in issues
        if i.code == "SPEC-DOC-002" and "missing-feature.html" in i.description
    ]
    assert matching, [i.to_dict() for i in issues]


# ---- check 3: ACTIVE.md


def test_missing_active_md_reports_doc_003(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "releases" / "ACTIVE.md").unlink()
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-003" in _codes(issues)


def test_non_canonical_phase_reports_doc_003(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "releases" / "ACTIVE.md").write_text(
        "release: r1\nphase: WORKING\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-003" in _codes(issues)


# ---- check 4: active release artifacts + status canonicity


def test_missing_plan_in_active_release_reports_doc_004(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "releases" / "r1" / "PLAN.md").unlink()
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-004" in _codes(issues)


def test_non_canonical_status_reports_doc_004(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "releases" / "r1" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Accepted\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-004" in _codes(issues)


# ---- check 5: PLAN line limit


def test_oversized_plan_after_cutoff_is_error(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    big = "# Plan\n\n> **Status:** Aprovado\n\n" + "\n".join(
        f"- line {i}" for i in range(400)
    )
    (specs / "releases" / "r1" / "PLAN.md").write_text(big, encoding="utf-8")
    (specs / "releases" / "r1" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-06-01\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    doc5 = [i for i in issues if i.code == "SPEC-DOC-005"]
    assert doc5 and doc5[0].severity == Severity.ERROR


def test_oversized_plan_before_cutoff_is_warning(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    big = "# Plan\n\n> **Status:** Aprovado\n\n" + "\n".join(
        f"- line {i}" for i in range(400)
    )
    (specs / "releases" / "r1" / "PLAN.md").write_text(big, encoding="utf-8")
    (specs / "releases" / "r1" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-04-01\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    doc5 = [i for i in issues if i.code == "SPEC-DOC-005"]
    assert doc5 and doc5[0].severity == Severity.WARNING


# ---- check 6: archive CLOSURE


def test_archived_release_without_closure_reports_doc_006(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    arch_dir = specs / "_archive" / "releases" / "old-release"
    arch_dir.mkdir(parents=True)
    (arch_dir / "SPEC.md").write_text("# spec", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-006" in _codes(issues)


def test_archived_release_with_valid_closure_passes(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    arch_dir = specs / "_archive" / "releases" / "old-release"
    arch_dir.mkdir(parents=True)
    closure = (
        "# Closure\n\n"
        "## Summary\n\nShipped.\n\n"
        "## Validations\n\n"
        "| Description | Command | Evidence |\n"
        "| --- | --- | --- |\n"
        "| check works | `pytest` | abc1234 |\n\n"
        "## Drifts\n\nnone\n\n"
        "## Memory updates\n\n- product.html\n"
    )
    (arch_dir / "CLOSURE.md").write_text(closure, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-006" not in _codes(issues)


# ---- check 7: orphan specs


def test_orphan_legacy_feature_spec_reports_doc_007(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    legacy = specs / "features" / "old-feature"
    legacy.mkdir(parents=True)
    (legacy / "SPEC.md").write_text("# legacy", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-007" in _codes(issues)


# ---- check 8: memory atomicity


def test_memory_with_changelog_h2_reports_doc_008(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    bad = """<!DOCTYPE html><html><head>
<script src="mermaid.js"></script>
</head><body>
<h1>Product</h1>
<h2>Catálogo</h2>
<ol><li><a href="feature-a.html">feature-a</a></li></ol>
<h2>Changelog</h2><p>v1 fix.</p>
</body></html>"""
    (specs / "memory" / "product" / "index.html").write_text(bad, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-008" in _codes(issues)


def test_memory_feature_with_changelog_h2_reports_doc_008(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    bad = """<!DOCTYPE html><html><head>
<script src="mermaid.js"></script>
</head><body>
<h1>Feature</h1>
<h2>History</h2><p>once was X.</p>
</body></html>"""
    (specs / "memory" / "product" / "feature-a.html").write_text(bad, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-008" in _codes(issues)


# ---- check 9: release id vs dir


def test_active_release_id_without_dir_reports_doc_009(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "releases" / "ACTIVE.md").write_text(
        "release: missing-id\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-009" in _codes(issues)


# ---- check 10: broken image links


def test_broken_image_link_in_memory_reports_doc_010(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    bad = """<!DOCTYPE html><html><head>
<script src="mermaid.js"></script>
</head><body>
<h1>Product</h1>
<img src="../assets/missing.png">
</body></html>"""
    (specs / "memory" / "product" / "index.html").write_text(bad, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-010" in _codes(issues)


# ---- check 11: mermaid script presence


def test_mermaid_blocks_without_script_reports_doc_011(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    bad = """<!DOCTYPE html><html><head><title>x</title></head><body>
<h1>Product</h1>
<pre class="mermaid">flowchart LR
A --> B</pre>
</body></html>"""
    (specs / "memory" / "product" / "index.html").write_text(bad, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc11 = [i for i in issues if i.code == "SPEC-DOC-011"]
    assert doc11 and doc11[0].severity == Severity.WARNING


# ---- meta: JSON output / API surface


def test_to_dict_includes_required_keys(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "constitution.md").unlink()
    issues = SpecsDoctor(specs).check()
    payload = issues[0].to_dict()
    assert set(payload.keys()) == {"code", "severity", "description", "path"}
