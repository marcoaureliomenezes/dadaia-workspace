"""Unit tests for SpecsDoctor — covers each of the 11 structural checks + TREE-1..7."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue

# Repo root: tests/unit/features/specs/test_doctor.py → 5 levels up = repo root
# Path(__file__).parent = tests/unit/features/specs/
# .parent.parent = tests/unit/features/
# .parent.parent.parent = tests/unit/
# .parent.parent.parent.parent = tests/
# .parent.parent.parent.parent.parent = repo root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent

# Canonical templates directory — same as the CLI uses
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_SCAFFOLD_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold"
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"

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
    (specs / "memory" / "tech-stack.html").write_text(MINIMAL_MEMORY_TECH_STACK, encoding="utf-8")
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
    matching = [
        i for i in issues if i.code == "SPEC-DOC-002L" and "product.html is legacy" in i.description
    ]
    assert matching, [i.to_dict() for i in issues]


def test_memory_agents_md_is_exempt_from_doc_002L(tmp_path: Path) -> None:
    """AGENTS.md in memory/ is a directory contract, NOT a legacy atom — must be exempt."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "memory" / "AGENTS.md").write_text("# Memory contract\n", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc_002l = [i for i in issues if i.code == "SPEC-DOC-002L" and "AGENTS.md" in i.path]
    assert doc_002l == [], doc_002l


def test_genuine_legacy_markdown_still_reports_doc_002L_when_agents_md_present(
    tmp_path: Path,
) -> None:
    """Presence of AGENTS.md must not suppress errors for other .md files in memory/."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "memory" / "AGENTS.md").write_text("# Memory contract\n", encoding="utf-8")
    (specs / "memory" / "old-note.md").write_text("# legacy note\n", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc_002l = [i for i in issues if i.code == "SPEC-DOC-002L" and "old-note.md" in i.path]
    assert doc_002l, "Expected SPEC-DOC-002L for old-note.md but got none"


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
        i for i in issues if i.code == "SPEC-DOC-002" and "missing-feature.html" in i.description
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
    (specs / "releases" / "ACTIVE.md").write_text("release: r1\nphase: WORKING\n", encoding="utf-8")
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
    big = "# Plan\n\n> **Status:** Aprovado\n\n" + "\n".join(f"- line {i}" for i in range(400))
    (specs / "releases" / "r1" / "PLAN.md").write_text(big, encoding="utf-8")
    (specs / "releases" / "r1" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-06-01\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    doc5 = [i for i in issues if i.code == "SPEC-DOC-005"]
    assert doc5 and doc5[0].severity == Severity.ERROR


def test_oversized_plan_before_cutoff_is_warning(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    big = "# Plan\n\n> **Status:** Aprovado\n\n" + "\n".join(f"- line {i}" for i in range(400))
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


# ---- check 3 hardening: whitespace-only values in ACTIVE.md


def test_active_md_empty_release_value_is_error(tmp_path: Path) -> None:
    """release: with whitespace-only value must be treated as missing (SPEC-DOC-003 ERROR)."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "releases" / "ACTIVE.md").write_text("release:   \nphase: TASKS\n", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc3_errors = [i for i in issues if i.code == "SPEC-DOC-003" and i.severity == Severity.ERROR]
    assert doc3_errors, [i.to_dict() for i in issues]


def test_active_md_empty_phase_value_is_error(tmp_path: Path) -> None:
    """phase: with whitespace-only value must be treated as missing (SPEC-DOC-003 ERROR)."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "releases" / "ACTIVE.md").write_text("release: r1\nphase:   \n", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc3_errors = [i for i in issues if i.code == "SPEC-DOC-003" and i.severity == Severity.ERROR]
    assert doc3_errors, [i.to_dict() for i in issues]


# ---- check 12: backlog schema (SPEC-DOC-012)


def test_backlog_well_formed_passes(tmp_path: Path) -> None:
    """A correctly formatted candidates.md produces no SPEC-DOC-012 issues."""
    specs = _make_clean_specs_tree(tmp_path)
    candidates = (
        "# Backlog\n\n"
        "## Candidatas ativas\n\n"
        "- my-feature — Does something useful (owner: software-engineer, contexto: `_archive/legacy-features/my-feature/SPEC.md`)\n"
    )
    (specs / "backlog" / "candidates.md").write_text(candidates, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc12 = [i for i in issues if i.code == "SPEC-DOC-012"]
    assert doc12 == [], doc12


def test_backlog_historico_section_skipped(tmp_path: Path) -> None:
    """Bullets under '## Histórico' are free-form and must not trigger SPEC-DOC-012."""
    specs = _make_clean_specs_tree(tmp_path)
    candidates = (
        "# Backlog\n\n"
        "## Candidatas ativas\n\n"
        "- good-feature — Does something (owner: devops-engineer, contexto: `_archive/legacy-features/good-feature/SPEC.md`)\n\n"
        "## Histórico (candidatas promovidas a release)\n\n"
        "- this bullet has free-form text without the expected schema\n"
        "- another free-form line (released on 2026-01-01)\n"
    )
    (specs / "backlog" / "candidates.md").write_text(candidates, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc12 = [i for i in issues if i.code == "SPEC-DOC-012"]
    assert doc12 == [], doc12


def test_backlog_malformed_bullet_warns(tmp_path: Path) -> None:
    """A bullet in '## Candidatas ativas' missing '(owner: ...)' raises SPEC-DOC-012 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    candidates = (
        "# Backlog\n\n## Candidatas ativas\n\n- bad-feature — Missing the owner field entirely\n"
    )
    (specs / "backlog" / "candidates.md").write_text(candidates, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc12 = [i for i in issues if i.code == "SPEC-DOC-012"]
    assert doc12 and doc12[0].severity == Severity.WARNING, [i.to_dict() for i in issues]


# ---- SPEC-DOC-012 extended: ## Hotfixes pendentes section


def test_hotfix_bullet_well_formed_passes(tmp_path: Path) -> None:
    """A correctly formatted bullet in '## Hotfixes pendentes' produces no SPEC-DOC-012 issues."""
    specs = _make_clean_specs_tree(tmp_path)
    # Timestamp fresh (1 hour ago) so no staleness warning
    ts = (datetime.now(tz=UTC) - timedelta(hours=1)).strftime("%Y-%m-%dT%H%M%SZ")
    candidates = (
        "# Backlog\n\n"
        "## Candidatas ativas\n\n"
        "(Sem candidatas)\n\n"
        "## Hotfixes pendentes\n\n"
        f"- {ts} HIGH specs/doctor — Check fails on empty backlog (post-mortem: https://example.com/pm-1)\n"
    )
    (specs / "backlog" / "candidates.md").write_text(candidates, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc12 = [i for i in issues if i.code == "SPEC-DOC-012"]
    assert doc12 == [], [i.to_dict() for i in doc12]


def test_hotfix_bullet_idempotent_with_historico(tmp_path: Path) -> None:
    """Bullets under ## Histórico are skipped even if they would fail the hotfix regex."""
    specs = _make_clean_specs_tree(tmp_path)
    candidates = (
        "# Backlog\n\n"
        "## Candidatas ativas\n\n"
        "- good-feature — Does something (owner: devops-engineer, contexto: `_archive/legacy-features/good-feature/SPEC.md`)\n\n"
        "## Hotfixes pendentes\n\n"
        "(Nenhum hotfix pendente.)\n\n"
        "## Histórico\n\n"
        "- this free-form line should not trigger SPEC-DOC-012\n"
    )
    (specs / "backlog" / "candidates.md").write_text(candidates, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc12 = [i for i in issues if i.code == "SPEC-DOC-012"]
    assert doc12 == [], [i.to_dict() for i in doc12]


def test_hotfix_bullet_malformed_warns(tmp_path: Path) -> None:
    """A malformed bullet in '## Hotfixes pendentes' raises SPEC-DOC-012 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    candidates = "# Backlog\n\n## Hotfixes pendentes\n\n- fix this bug (no proper format at all)\n"
    (specs / "backlog" / "candidates.md").write_text(candidates, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc12 = [i for i in issues if i.code == "SPEC-DOC-012"]
    assert doc12, "Expected SPEC-DOC-012 warning for malformed hotfix bullet"
    assert doc12[0].severity == Severity.WARNING


def test_hotfix_bullet_stale_75h_warns(tmp_path: Path) -> None:
    """A hotfix bullet with a timestamp older than 72h raises SPEC-DOC-012 WARNING (D23)."""
    specs = _make_clean_specs_tree(tmp_path)
    stale_ts = (datetime.now(tz=UTC) - timedelta(hours=75)).strftime("%Y-%m-%dT%H%M%SZ")
    candidates = (
        "# Backlog\n\n"
        "## Hotfixes pendentes\n\n"
        f"- {stale_ts} LOW specs/doctor — Stale bug unfixed (post-mortem: https://example.com/pm-2)\n"
    )
    (specs / "backlog" / "candidates.md").write_text(candidates, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc12 = [i for i in issues if i.code == "SPEC-DOC-012" and "stale" in i.description]
    assert doc12, "Expected staleness warning for 75h-old hotfix bullet"
    assert doc12[0].severity == Severity.WARNING


def test_hotfix_bullet_fresh_10h_no_stale_warning(tmp_path: Path) -> None:
    """A hotfix bullet with a timestamp only 10h old does NOT trigger a staleness warning."""
    specs = _make_clean_specs_tree(tmp_path)
    fresh_ts = (datetime.now(tz=UTC) - timedelta(hours=10)).strftime("%Y-%m-%dT%H%M%SZ")
    candidates = (
        "# Backlog\n\n"
        "## Hotfixes pendentes\n\n"
        f"- {fresh_ts} MEDIUM specs/doctor — Fresh bug (post-mortem: https://example.com/pm-3)\n"
    )
    (specs / "backlog" / "candidates.md").write_text(candidates, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    stale_issues = [i for i in issues if i.code == "SPEC-DOC-012" and "stale" in i.description]
    assert stale_issues == [], [i.to_dict() for i in stale_issues]


# ---- SPEC-DOC-016: SemVer folder naming for releases


def test_semver_folder_name_new_release_passes(tmp_path: Path) -> None:
    """A release folder named v1.2.3 with Created: >= cutoff produces no SPEC-DOC-016 issues."""
    specs = _make_clean_specs_tree(tmp_path, release_id="v1.2.3")
    # Overwrite SPEC.md with Created date on/after cutoff
    (specs / "releases" / "v1.2.3" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-06-01\n\nContent.\n",
        encoding="utf-8",
    )
    from datetime import date as _date

    with patch("dadaia_workspace.features.specs.doctor.date") as mock_date:
        mock_date.today.return_value = _date(2026, 6, 15)
        mock_date.side_effect = lambda *a, **kw: _date(*a, **kw)
        issues = SpecsDoctor(specs).check()
    doc16 = [i for i in issues if i.code == "SPEC-DOC-016"]
    assert doc16 == [], [i.to_dict() for i in doc16]


def test_semver_folder_name_non_semver_new_release_warns(tmp_path: Path) -> None:
    """A release folder named 'my-feature-v1' with Created: >= cutoff raises SPEC-DOC-016."""
    specs = _make_clean_specs_tree(tmp_path, release_id="my-feature-v1")
    (specs / "releases" / "my-feature-v1" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-06-01\n\nContent.\n",
        encoding="utf-8",
    )
    from datetime import date as _date

    with patch("dadaia_workspace.features.specs.doctor.date") as mock_date:
        mock_date.today.return_value = _date(2026, 6, 15)
        mock_date.side_effect = lambda *a, **kw: _date(*a, **kw)
        issues = SpecsDoctor(specs).check()
    doc16 = [i for i in issues if i.code == "SPEC-DOC-016"]
    assert doc16, "Expected SPEC-DOC-016 for non-SemVer folder name"


def test_semver_folder_name_vintage_release_excluded(tmp_path: Path) -> None:
    """A legacy release folder named 'sdd-release-lifecycle-v1' with Created: <= 2026-05-17
    is excluded from SPEC-DOC-016 (vintage bucket, D14)."""
    specs = _make_clean_specs_tree(tmp_path, release_id="sdd-release-lifecycle-v1")
    (specs / "releases" / "sdd-release-lifecycle-v1" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-05-01\n\nContent.\n",
        encoding="utf-8",
    )
    from datetime import date as _date

    with patch("dadaia_workspace.features.specs.doctor.date") as mock_date:
        mock_date.today.return_value = _date(2026, 6, 15)
        mock_date.side_effect = lambda *a, **kw: _date(*a, **kw)
        issues = SpecsDoctor(specs).check()
    doc16 = [i for i in issues if i.code == "SPEC-DOC-016"]
    assert doc16 == [], [i.to_dict() for i in doc16]


def test_semver_folder_name_before_cutoff_not_checked(tmp_path: Path) -> None:
    """SPEC-DOC-016 is not run at all when today < RELEASE_SEMVER_CUTOFF (2026-06-01)."""
    specs = _make_clean_specs_tree(tmp_path, release_id="bad-name")
    (specs / "releases" / "bad-name" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-06-01\n\nContent.\n",
        encoding="utf-8",
    )
    from datetime import date as _date

    with patch("dadaia_workspace.features.specs.doctor.date") as mock_date:
        mock_date.today.return_value = _date(2026, 5, 20)
        mock_date.side_effect = lambda *a, **kw: _date(*a, **kw)
        issues = SpecsDoctor(specs).check()
    doc16 = [i for i in issues if i.code == "SPEC-DOC-016"]
    assert doc16 == [], "SPEC-DOC-016 should not run before RELEASE_SEMVER_CUTOFF"


# ============================================================================
# TREE invariants (spec-context-tree-v2)
# ============================================================================


def _make_full_tree(root: Path) -> Path:
    """Like _make_clean_specs_tree but also adds backlog/, bugs/, releases/ dirs,
    and specs/AGENTS.md from the canonical template so TREE invariants pass."""
    specs = _make_clean_specs_tree(root)
    # TREE-4: ensure all required dirs exist
    for dirname in ("backlog", "bugs", "releases"):
        d = specs / dirname
        d.mkdir(exist_ok=True)
        (d / ".gitkeep").write_text("", encoding="utf-8")
        src_readme = _SCAFFOLD_DIR / dirname / "README.md"
        if src_readme.exists():
            (d / "README.md").write_text(src_readme.read_text(encoding="utf-8"), encoding="utf-8")
    # TREE-5: add AGENTS.md matching canonical template
    agents_template = _TEMPLATES_DIR / "specs-AGENTS.md"
    if agents_template.exists():
        (specs / "AGENTS.md").write_text(
            agents_template.read_text(encoding="utf-8"), encoding="utf-8"
        )
    return specs


# ---- TREE-1: foundation/ must not exist

def test_tree1_foundation_dir_triggers_warning(tmp_path: Path) -> None:
    """TREE-1: specs/foundation/ present emits a TREE-1 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    foundation = specs / "foundation"
    foundation.mkdir()
    (foundation / "something.md").write_text("# Old", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    tree1 = [i for i in issues if i.code == "TREE-1"]
    assert tree1, "Expected TREE-1 WARNING when foundation/ exists"
    assert tree1[0].severity == Severity.WARNING
    assert not tree1[0].fixable


def test_tree1_fix_does_not_delete_foundation(tmp_path: Path) -> None:
    """TREE-1 is fixable=False: calling fix() must NOT remove foundation/."""
    specs = _make_clean_specs_tree(tmp_path)
    foundation = specs / "foundation"
    foundation.mkdir()
    (foundation / "content.md").write_text("# Protected", encoding="utf-8")
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree1 = [i for i in issues if i.code == "TREE-1"]
    assert tree1, "Pre-condition: TREE-1 must be found"
    doctor.fix(issues)
    # foundation must still be intact
    assert foundation.exists(), "fix() must NOT remove specs/foundation/"
    assert (foundation / "content.md").exists()
    # TREE-1 still appears after fix (warn-only)
    residual = doctor.check()
    assert any(i.code == "TREE-1" for i in residual)


# ---- TREE-2: root SPEC.md must not exist

def test_tree2_root_spec_md_triggers_warning(tmp_path: Path) -> None:
    """TREE-2: specs/SPEC.md at tree root emits a TREE-2 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "SPEC.md").write_text("# Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    tree2 = [i for i in issues if i.code == "TREE-2"]
    assert tree2, "Expected TREE-2 WARNING when specs/SPEC.md exists at root"
    assert tree2[0].severity == Severity.WARNING
    assert not tree2[0].fixable


def test_tree2_fix_does_not_move_root_spec_md(tmp_path: Path) -> None:
    """TREE-2 is fixable=False: calling fix() must NOT move specs/SPEC.md."""
    specs = _make_clean_specs_tree(tmp_path)
    root_spec = specs / "SPEC.md"
    root_spec.write_text("# Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree2 = [i for i in issues if i.code == "TREE-2"]
    assert tree2, "Pre-condition: TREE-2 must be found"
    doctor.fix(issues)
    # root SPEC.md must still be intact
    assert root_spec.exists(), "fix() must NOT move specs/SPEC.md"
    # TREE-2 still appears after fix (warn-only)
    residual = doctor.check()
    assert any(i.code == "TREE-2" for i in residual)


# ---- TREE-3: required memory HTML files must exist

def test_tree3_missing_architecture_html_triggers_warning(tmp_path: Path) -> None:
    """TREE-3: memory/architecture.html absent emits a TREE-3 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "memory" / "architecture.html").unlink()
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree3 = [i for i in issues if i.code == "TREE-3"]
    assert tree3, "Expected TREE-3 WARNING for missing architecture.html"
    assert tree3[0].severity == Severity.WARNING


def test_tree3_fix_renders_missing_memory_html(tmp_path: Path) -> None:
    """TREE-3 auto-fix: calling fix() renders missing memory files from Jinja templates."""
    specs = _make_clean_specs_tree(tmp_path)
    arch = specs / "memory" / "architecture.html"
    tech = specs / "memory" / "tech-stack.html"
    arch.unlink()
    tech.unlink()
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree3 = [i for i in issues if i.code == "TREE-3"]
    assert tree3, "Pre-condition: TREE-3 issues must exist"
    fixed = doctor.fix(issues)
    # Both files must now exist
    assert arch.exists(), "architecture.html must be created by fix()"
    assert tech.exists(), "tech-stack.html must be created by fix()"
    assert len(fixed) == 2
    # Rendered HTML must contain an <h1>
    content = arch.read_text(encoding="utf-8")
    assert "<h1>" in content, "Rendered architecture.html must contain <h1>"
    # After fix, TREE-3 should no longer appear
    residual = [i for i in doctor.check() if i.code == "TREE-3"]
    assert residual == [], f"Residual TREE-3 after fix: {[i.description for i in residual]}"


# ---- TREE-4: backlog/, bugs/, releases/ must exist

def test_tree4_missing_backlog_triggers_warning(tmp_path: Path) -> None:
    """TREE-4: specs/backlog/ absent emits a TREE-4 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    # Remove backlog dir if present (clean tree doesn't have it)
    import shutil
    backlog = specs / "backlog"
    if backlog.exists():
        shutil.rmtree(backlog)
    doctor = SpecsDoctor(specs, public_dir=_PUBLIC_DIR)
    issues = doctor.check()
    tree4 = [i for i in issues if i.code == "TREE-4"]
    assert any("backlog" in i.description for i in tree4), (
        f"Expected TREE-4 for missing backlog/; got {[i.description for i in tree4]}"
    )
    assert tree4[0].severity == Severity.WARNING


def test_tree4_fix_creates_missing_dirs(tmp_path: Path) -> None:
    """TREE-4 auto-fix: calling fix() creates the missing directory with README.md + .gitkeep."""
    specs = _make_clean_specs_tree(tmp_path)
    import shutil
    for dirname in ("backlog", "bugs"):
        d = specs / dirname
        if d.exists():
            shutil.rmtree(d)
    doctor = SpecsDoctor(specs, public_dir=_PUBLIC_DIR)
    issues = doctor.check()
    tree4 = [i for i in issues if i.code == "TREE-4"]
    assert tree4, "Pre-condition: TREE-4 issues must exist"
    fixed = doctor.fix(issues)
    assert len(fixed) >= 2
    # Dirs must now exist with README.md and .gitkeep
    for dirname in ("backlog", "bugs"):
        d = specs / dirname
        assert d.exists(), f"specs/{dirname}/ must be created by fix()"
        assert (d / "README.md").exists(), f"specs/{dirname}/README.md must be created"
        assert (d / ".gitkeep").exists(), f"specs/{dirname}/.gitkeep must be created"
    # After fix, TREE-4 should no longer appear for fixed dirs
    residual = [i for i in doctor.check() if i.code == "TREE-4"]
    assert residual == [], f"Residual TREE-4 after fix: {[i.description for i in residual]}"


# ---- TREE-5: specs/AGENTS.md must exist and match canonical template

def test_tree5_missing_agents_md_triggers_warning(tmp_path: Path) -> None:
    """TREE-5: specs/AGENTS.md absent emits a TREE-5 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    agents_md = specs / "AGENTS.md"
    if agents_md.exists():
        agents_md.unlink()
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree5 = [i for i in issues if i.code == "TREE-5"]
    assert tree5, "Expected TREE-5 WARNING for missing specs/AGENTS.md"
    assert tree5[0].severity == Severity.WARNING
    assert not tree5[0].fixable


def test_tree5_drifted_agents_md_triggers_warning(tmp_path: Path) -> None:
    """TREE-5: specs/AGENTS.md with modified content emits a drift TREE-5 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "AGENTS.md").write_text(
        "# AGENTS\n\nCustomised content that differs from the canonical template.\n",
        encoding="utf-8",
    )
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree5 = [i for i in issues if i.code == "TREE-5"]
    assert tree5, "Expected TREE-5 WARNING for drifted specs/AGENTS.md"
    assert tree5[0].severity == Severity.WARNING
    assert not tree5[0].fixable
    assert "drifted" in tree5[0].description.lower() or "drift" in tree5[0].description.lower()


def test_tree5_canonical_agents_md_passes(tmp_path: Path) -> None:
    """TREE-5: specs/AGENTS.md matching the canonical template produces no TREE-5 issue."""
    specs = _make_clean_specs_tree(tmp_path)
    canonical = (_TEMPLATES_DIR / "specs-AGENTS.md").read_text(encoding="utf-8")
    (specs / "AGENTS.md").write_text(canonical, encoding="utf-8")
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree5 = [i for i in issues if i.code == "TREE-5"]
    assert tree5 == [], f"Unexpected TREE-5 issue: {[i.description for i in tree5]}"


# ---- TREE-6: active release must have mandatory artifacts for its phase

def test_tree6_missing_plan_in_impl_phase_triggers_error(tmp_path: Path) -> None:
    """TREE-6: active release in IMPLEMENTATION phase missing PLAN.md emits TREE-6 ERROR."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "releases" / "r1" / "PLAN.md").unlink()
    issues = SpecsDoctor(specs).check()
    tree6 = [i for i in issues if i.code == "TREE-6"]
    assert tree6, "Expected TREE-6 ERROR for missing PLAN.md in IMPLEMENTATION phase"
    assert tree6[0].severity == Severity.ERROR
    assert not tree6[0].fixable


def test_tree6_no_autofix_leaves_file_absent(tmp_path: Path) -> None:
    """TREE-6 has no auto-fix: calling fix() must NOT create PLAN.md."""
    specs = _make_clean_specs_tree(tmp_path)
    plan = specs / "releases" / "r1" / "PLAN.md"
    plan.unlink()
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree6 = [i for i in issues if i.code == "TREE-6"]
    assert tree6, "Pre-condition: TREE-6 must be found"
    doctor.fix(issues)
    # PLAN.md must still be absent
    assert not plan.exists(), "fix() must NOT create PLAN.md for TREE-6"
    # TREE-6 still appears after fix
    residual = doctor.check()
    assert any(i.code == "TREE-6" for i in residual)


# ---- TREE-7: bugs/<slug>.md must have session_id frontmatter field

def test_tree7_bug_missing_session_id_triggers_error(tmp_path: Path) -> None:
    """TREE-7: a bugs/<slug>.md without session_id: frontmatter emits TREE-7 ERROR."""
    specs = _make_clean_specs_tree(tmp_path)
    bugs_dir = specs / "bugs"
    bugs_dir.mkdir(exist_ok=True)
    (bugs_dir / "some-bug.md").write_text(
        "title: Something broke\nseverity: high\nopened: 2026-05-30\n\n## Description\n\nBroken.",
        encoding="utf-8",
    )
    issues = SpecsDoctor(specs).check()
    tree7 = [i for i in issues if i.code == "TREE-7"]
    assert tree7, "Expected TREE-7 ERROR for bug missing session_id"
    assert tree7[0].severity == Severity.ERROR
    assert not tree7[0].fixable


def test_tree7_bug_with_session_id_passes(tmp_path: Path) -> None:
    """TREE-7: a bugs/<slug>.md with session_id: null produces no TREE-7 issue."""
    specs = _make_clean_specs_tree(tmp_path)
    bugs_dir = specs / "bugs"
    bugs_dir.mkdir(exist_ok=True)
    (bugs_dir / "some-bug.md").write_text(
        "title: Something broke\nseverity: high\nopened: 2026-05-30\nsession_id: null\n\n## Description\n\nBroken.",
        encoding="utf-8",
    )
    issues = SpecsDoctor(specs).check()
    tree7 = [i for i in issues if i.code == "TREE-7"]
    assert tree7 == [], f"Unexpected TREE-7: {[i.description for i in tree7]}"


def test_tree7_no_autofix_leaves_bug_unchanged(tmp_path: Path) -> None:
    """TREE-7 has no auto-fix: calling fix() must NOT inject session_id into bug files."""
    specs = _make_clean_specs_tree(tmp_path)
    bugs_dir = specs / "bugs"
    bugs_dir.mkdir(exist_ok=True)
    bug_path = bugs_dir / "missing-session.md"
    original = "title: test\nseverity: low\nopened: 2026-05-30\n"
    bug_path.write_text(original, encoding="utf-8")
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree7 = [i for i in issues if i.code == "TREE-7"]
    assert tree7, "Pre-condition: TREE-7 must be found"
    doctor.fix(issues)
    # File must be unchanged
    assert bug_path.read_text(encoding="utf-8") == original, (
        "fix() must NOT modify bugs/<slug>.md for TREE-7"
    )
    # TREE-7 still appears after fix
    residual = doctor.check()
    assert any(i.code == "TREE-7" for i in residual)


# ---- AC-T9-15: fresh scaffold passes all TREE invariants

def test_fresh_scaffold_passes_all_tree_invariants(tmp_path: Path) -> None:
    """AC-T9-15: a freshly scaffolded workspace produces 0 TREE errors and 0 TREE-* issues
    that would break a gate (TREE-1/2/3/4/5 are warnings; 6/7 require violating content).
    """
    from dadaia_workspace.features.specs.scaffolder import scaffold

    specs = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs,
        project_name="test-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], f"Scaffold errors: {result.errors}"

    # Also add bugs/ dir (T-4 scaffold delivers it; add it here to satisfy TREE-4)
    bugs_dir = specs / "bugs"
    bugs_dir.mkdir(exist_ok=True)
    src_readme = _SCAFFOLD_DIR / "bugs" / "README.md"
    if src_readme.exists():
        (bugs_dir / "README.md").write_text(src_readme.read_text(encoding="utf-8"), encoding="utf-8")
    (bugs_dir / ".gitkeep").write_text("", encoding="utf-8")

    # Add AGENTS.md from canonical template
    agents_template = _TEMPLATES_DIR / "specs-AGENTS.md"
    if agents_template.exists():
        (specs / "AGENTS.md").write_text(
            agents_template.read_text(encoding="utf-8"), encoding="utf-8"
        )

    doctor = SpecsDoctor(specs, public_dir=_PUBLIC_DIR)
    issues = doctor.check()

    # No TREE-* errors (TREE-6 and TREE-7 would be errors)
    tree_errors = [i for i in issues if i.code.startswith("TREE-") and i.severity == Severity.ERROR]
    assert tree_errors == [], f"Unexpected TREE errors on fresh scaffold: {[i.to_dict() for i in tree_errors]}"


# ---- CAT-1: catalog.json ↔ feature HTML sync check (memory-context-enforcement-v1)


def _make_catalog_json(product_dir: Path, slugs: list[str]) -> None:
    """Write a minimal but valid catalog.json with the given slugs."""
    import json as _json
    from datetime import UTC, datetime

    features = [
        {
            "rank": i + 1,
            "slug": slug,
            "title": slug,
            "summary": "",
            "path": f"specs/memory/product/{slug}.html",
            "tags": [],
            "depends_on": [],
        }
        for i, slug in enumerate(slugs)
    ]
    catalog = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "context": "test",
        "features": features,
    }
    (product_dir / "catalog.json").write_text(
        _json.dumps(catalog, indent=2) + "\n", encoding="utf-8"
    )


def test_cat1_absent_catalog_with_feature_htmls_triggers_warning(tmp_path: Path) -> None:
    """CAT-1: catalog.json absent + 3 feature HTMLs → one CAT-1 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    # Add two more feature HTMLs (feature-a is already in the clean tree)
    (product_dir / "feature-b.html").write_text(
        MINIMAL_MEMORY_PRODUCT_FEATURE, encoding="utf-8"
    )
    (product_dir / "feature-c.html").write_text(
        MINIMAL_MEMORY_PRODUCT_FEATURE, encoding="utf-8"
    )
    # No catalog.json
    assert not (product_dir / "catalog.json").exists()

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1, "Expected CAT-1 WARNING when catalog.json is absent and HTMLs exist"
    assert cat1[0].severity == Severity.WARNING
    # Single warning (not one per file)
    assert len(cat1) == 1


def test_cat1_absent_catalog_no_feature_htmls_no_warning(tmp_path: Path) -> None:
    """CAT-1: catalog.json absent but no feature HTMLs (only index.html) → no CAT-1."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    # Remove the feature-a.html so no feature HTMLs remain
    (product_dir / "feature-a.html").unlink()
    # Also remove the broken anchor from index.html to avoid SPEC-DOC-002 cascade
    # We only need to verify no CAT-1 fires
    assert not (product_dir / "catalog.json").exists()

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1 == [], f"Unexpected CAT-1 when no feature HTMLs present: {[i.description for i in cat1]}"


def test_cat1_in_sync_catalog_no_warning(tmp_path: Path) -> None:
    """CAT-1: catalog.json present and in sync with HTML files → no CAT-1."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    # feature-a.html already exists in clean tree; create matching catalog
    _make_catalog_json(product_dir, ["feature-a"])

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1 == [], f"Unexpected CAT-1 when catalog is in sync: {[i.description for i in cat1]}"


def test_cat1_stale_slug_warns_with_slug_name(tmp_path: Path) -> None:
    """CAT-1: catalog.json has slug 'stale-feature' but no stale-feature.html → WARNING names slug."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    # catalog lists feature-a (which exists) and stale-feature (which does not)
    _make_catalog_json(product_dir, ["feature-a", "stale-feature"])

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1, "Expected CAT-1 WARNING for stale slug 'stale-feature'"
    # The warning must name the missing slug
    descriptions = " ".join(i.description for i in cat1)
    assert "stale-feature" in descriptions, (
        f"Expected 'stale-feature' to be named in CAT-1 description; got: {descriptions}"
    )
    assert all(i.severity == Severity.WARNING for i in cat1)


def test_cat1_extra_html_warns_with_file_name(tmp_path: Path) -> None:
    """CAT-1: extra HTML file on disk not in catalog → WARNING names the file."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    # Add an extra HTML file that is NOT in the catalog
    (product_dir / "new-feature.html").write_text(
        MINIMAL_MEMORY_PRODUCT_FEATURE, encoding="utf-8"
    )
    # Catalog lists only feature-a (not new-feature)
    _make_catalog_json(product_dir, ["feature-a"])

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1, "Expected CAT-1 WARNING for extra HTML file 'new-feature.html'"
    descriptions = " ".join(i.description for i in cat1)
    assert "new-feature" in descriptions, (
        f"Expected 'new-feature' to be named in CAT-1 description; got: {descriptions}"
    )
    assert all(i.severity == Severity.WARNING for i in cat1)


def test_cat1_both_stale_and_extra_emit_separate_warnings(tmp_path: Path) -> None:
    """CAT-1: one stale slug + one extra HTML → two separate CAT-1 WARNINGs."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    (product_dir / "new-feature.html").write_text(
        MINIMAL_MEMORY_PRODUCT_FEATURE, encoding="utf-8"
    )
    # Catalog has stale-slug (no file) but not new-feature or feature-a (extra files)
    _make_catalog_json(product_dir, ["stale-slug"])

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    # At minimum: one for stale-slug, one for feature-a, one for new-feature
    assert len(cat1) >= 2, (
        f"Expected at least 2 CAT-1 WARNINGs; got {len(cat1)}: "
        f"{[i.description for i in cat1]}"
    )


def test_cat1_is_always_warning_never_error(tmp_path: Path) -> None:
    """CAT-1 must never be ERROR severity."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    # Maximally broken: catalog with wrong slug and extra file
    _make_catalog_json(product_dir, ["wrong-slug"])

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1, "Pre-condition: CAT-1 issues must be present"
    for issue in cat1:
        assert issue.severity == Severity.WARNING, (
            f"CAT-1 must be WARNING, got ERROR: {issue.description}"
        )


def test_cat1_absent_catalog_warning_mentions_count(tmp_path: Path) -> None:
    """CAT-1: the absent-catalog WARNING message includes the HTML file count."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    (product_dir / "feature-b.html").write_text(
        MINIMAL_MEMORY_PRODUCT_FEATURE, encoding="utf-8"
    )
    (product_dir / "feature-c.html").write_text(
        MINIMAL_MEMORY_PRODUCT_FEATURE, encoding="utf-8"
    )
    # 3 feature HTMLs: feature-a, feature-b, feature-c

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1
    assert "3" in cat1[0].description, (
        f"Expected '3' in absent-catalog CAT-1 description; got: {cat1[0].description}"
    )


# ---- AC-T9-16: dadaia-workspace repo itself passes (regression guard)

def test_dadaia_workspace_repo_passes_tree_invariants() -> None:
    """AC-T9-16: the dadaia-workspace repo's own specs/ must produce 0 TREE-* errors.

    This is the critical regression guard: if any new ERROR-severity TREE invariant
    fires against this repo's own tree, the severity mapping or trigger logic is wrong.
    """
    repo_specs = _REPO_ROOT / "specs"
    if not repo_specs.exists():
        import pytest
        pytest.skip("specs/ not found — not running in dadaia-workspace repo context")

    doctor = SpecsDoctor(repo_specs, public_dir=_PUBLIC_DIR)
    issues = doctor.check()
    tree_errors = [i for i in issues if i.code.startswith("TREE-") and i.severity == Severity.ERROR]
    assert tree_errors == [], (
        "dadaia-workspace repo triggered TREE ERROR invariants — severity mapping is wrong:\n"
        + "\n".join(f"  {i.code}: {i.description}" for i in tree_errors)
    )
