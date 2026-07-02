"""Unit tests for SpecsDoctor structural checks and tree invariants."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_SCAFFOLD_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold"
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"

MINIMAL_MEMORY_PRODUCT_INDEX_MD = """\
---
slug: index
title: Product Index
category: product
tldr: 'Product catalog entry point.'
summary: 'Product catalog entry point.'
tags: []
agent_tier: self-pull
token_estimate: 20
last_updated: '2026-06-01'
release_origin: test-release
---

## Catálogo de features

Feature atoms.
"""

MINIMAL_MEMORY_PRODUCT_FEATURE_MD = """\
---
slug: feature-a
title: Feature A
category: product
tldr: 'Does A.'
summary: 'Does A.'
tags: []
agent_tier: self-pull
token_estimate: 20
last_updated: '2026-06-01'
release_origin: test-release
---

## Propósito

It does A.
"""

MINIMAL_MEMORY_ARCHITECTURE_MD = """\
---
slug: architecture
title: Architecture Memory
category: core
tldr: 'System architecture layers.'
summary: 'System architecture layers and dependency contracts.'
tags: []
agent_tier: self-pull
token_estimate: 20
last_updated: '2026-06-01'
release_origin: test-release
---

## Visão geral

Layers.
"""

MINIMAL_MEMORY_TECH_STACK_MD = """\
---
slug: tech-stack
title: Tech Stack Memory
category: core
tldr: 'Technology stack.'
summary: 'Technology stack and approved dependencies.'
tags: []
agent_tier: self-pull
token_estimate: 20
last_updated: '2026-06-01'
release_origin: test-release
---

## Linguagens

Python, Go.
"""


@pytest.fixture(autouse=True)
def _skip_memory_lint_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep SpecsDoctor unit tests focused on in-process structural checks."""
    monkeypatch.setattr(SpecsDoctor, "_check_lint1_memory_atoms", lambda self: [])


def _make_clean_specs_tree(root: Path, release_id: str = "r1") -> Path:
    """Create a minimal but valid specs/ tree using .md memory atoms."""
    specs = root / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / release_id).mkdir(parents=True)
    (specs / "_archive" / "releases").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)

    (specs / "constitution.md").write_text("# Constitution\n\nThe laws.\n", encoding="utf-8")
    (specs / "memory" / "product" / "index.md").write_text(
        MINIMAL_MEMORY_PRODUCT_INDEX_MD, encoding="utf-8"
    )
    (specs / "memory" / "product" / "feature-a.md").write_text(
        MINIMAL_MEMORY_PRODUCT_FEATURE_MD, encoding="utf-8"
    )
    (specs / "memory" / "architecture.md").write_text(
        MINIMAL_MEMORY_ARCHITECTURE_MD, encoding="utf-8"
    )
    (specs / "memory" / "tech-stack.md").write_text(MINIMAL_MEMORY_TECH_STACK_MD, encoding="utf-8")
    (specs / "memory" / "quality-assurance.md").write_text(
        "---\nslug: quality-assurance\ntitle: Quality Assurance\ncategory: core\n"
        "tldr: 'QA standards.'\nsummary: 'QA standards and anti-slop rules.'\n"
        "tags: []\nagent_tier: self-pull\ntoken_estimate: 20\nlast_updated: '2026-06-07'\n"
        "release_origin: test-release\n---\n\n## Standards\n\nQA standards.\n",
        encoding="utf-8",
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
    (specs / "memory" / "product" / "index.md").unlink()
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-002" in _codes(issues)


def test_missing_architecture_md_reports_doc_002(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "memory" / "architecture.md").unlink()
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-002" in _codes(issues)


def test_legacy_memory_markdown_reports_doc_002L(tmp_path: Path) -> None:
    """A non-canonical .md at memory/ root (not architecture.md or tech-stack.md)
    is flagged as legacy (SPEC-DOC-002L).
    """
    specs = _make_clean_specs_tree(tmp_path)
    # Write a non-canonical .md at memory/ root — should be flagged.
    (specs / "memory" / "legacy-notes.md").write_text("# legacy", encoding="utf-8")
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


def test_product_feature_md_without_heading_reports_doc_002(tmp_path: Path) -> None:
    """SPEC-DOC-002: a feature .md atom with no heading (empty body after frontmatter)
    is flagged — memory atoms must have at least one ATX heading.
    """
    specs = _make_clean_specs_tree(tmp_path)
    # Overwrite feature-a.md with content that has frontmatter but NO heading in body
    bad_feature = """\
---
slug: feature-a
title: Feature A
---

No heading here, only prose.
"""
    (specs / "memory" / "product" / "feature-a.md").write_text(bad_feature, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    matching = [i for i in issues if i.code == "SPEC-DOC-002" and "feature-a.md" in (i.path or "")]
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


@pytest.mark.parametrize("heading", ["Changelog", "History"])
def test_memory_md_with_history_heading_reports_doc_008(tmp_path: Path, heading: str) -> None:
    """Memory atoms cannot contain changelog/history sections."""
    specs = _make_clean_specs_tree(tmp_path)
    bad = f"""\
---
slug: feature-a
title: Feature A
---

## Propósito

Does A.

## {heading}

Historical details.
"""
    (specs / "memory" / "product" / "feature-a.md").write_text(bad, encoding="utf-8")
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


@pytest.mark.parametrize(
    "candidates",
    [
        pytest.param(
            "# Backlog\n\n"
            "## Candidatas ativas\n\n"
            "- my-feature — Does something useful (owner: software-engineer, contexto: `_archive/legacy-features/my-feature/SPEC.md`)\n",
            id="well-formed-candidate",
        ),
        pytest.param(
            "# Backlog\n\n"
            "## Candidatas ativas\n\n"
            "- good-feature — Does something (owner: devops-engineer, contexto: `_archive/legacy-features/good-feature/SPEC.md`)\n\n"
            "## Histórico (candidatas promovidas a release)\n\n"
            "- this bullet has free-form text without the expected schema\n"
            "- another free-form line (released on 2026-01-01)\n",
            id="historico-section-skipped",
        ),
    ],
)
def test_valid_candidates_content_produces_no_doc_012(tmp_path: Path, candidates: str) -> None:
    """A well-formed '## Candidatas ativas' bullet and free-form '## Histórico' bullets
    both produce no SPEC-DOC-012 issues."""
    specs = _make_clean_specs_tree(tmp_path)
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


def _hotfix_well_formed_candidates() -> str:
    # Timestamp fresh (1 hour ago) so no staleness warning.
    ts = (datetime.now(tz=UTC) - timedelta(hours=1)).strftime("%Y-%m-%dT%H%M%SZ")
    return (
        "# Backlog\n\n"
        "## Candidatas ativas\n\n"
        "(Sem candidatas)\n\n"
        "## Hotfixes pendentes\n\n"
        f"- {ts} HIGH specs/doctor — Check fails on empty backlog (post-mortem: https://example.com/pm-1)\n"
    )


def _hotfix_idempotent_with_historico_candidates() -> str:
    return (
        "# Backlog\n\n"
        "## Candidatas ativas\n\n"
        "- good-feature — Does something (owner: devops-engineer, contexto: `_archive/legacy-features/good-feature/SPEC.md`)\n\n"
        "## Hotfixes pendentes\n\n"
        "(Nenhum hotfix pendente.)\n\n"
        "## Histórico\n\n"
        "- this free-form line should not trigger SPEC-DOC-012\n"
    )


@pytest.mark.parametrize(
    "candidates_factory",
    [
        pytest.param(_hotfix_well_formed_candidates, id="hotfix-well-formed"),
        pytest.param(
            _hotfix_idempotent_with_historico_candidates,
            id="hotfix-idempotent-with-historico",
        ),
    ],
)
def test_valid_hotfix_content_produces_no_doc_012(
    tmp_path: Path, candidates_factory: Callable[[], str]
) -> None:
    """A well-formed '## Hotfixes pendentes' bullet and a hotfix section combined with
    free-form '## Histórico' bullets both produce no SPEC-DOC-012 issues."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "backlog" / "candidates.md").write_text(candidates_factory(), encoding="utf-8")
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


@pytest.mark.parametrize(
    ("release_id", "created", "today"),
    [
        pytest.param("v1.2.3", "2026-06-01", (2026, 6, 15), id="semver-name-new-release"),
        pytest.param(
            "sdd-release-lifecycle-v1",
            "2026-05-01",
            (2026, 6, 15),
            id="vintage-release-excluded",
        ),
        pytest.param(
            "bad-name", "2026-06-01", (2026, 5, 20), id="before-semver-cutoff-not-checked"
        ),
    ],
)
def test_semver_folder_name_produces_no_doc_016(
    tmp_path: Path, release_id: str, created: str, today: tuple[int, int, int]
) -> None:
    """SPEC-DOC-016 stays silent for: a SemVer-named new release, a grandfathered vintage
    release (Created <= 2026-05-17, D14), and any release when today is before
    RELEASE_SEMVER_CUTOFF (2026-06-01)."""
    specs = _make_clean_specs_tree(tmp_path, release_id=release_id)
    (specs / "releases" / release_id / "SPEC.md").write_text(
        f"# Spec\n\n> **Status:** Aprovado\n> **Created:** {created}\n\nContent.\n",
        encoding="utf-8",
    )
    from datetime import date as _date

    with patch("dadaia_workspace.features.specs.doctor.date") as mock_date:
        mock_date.today.return_value = _date(*today)
        mock_date.side_effect = lambda *a, **kw: _date(*a, **kw)
        issues = SpecsDoctor(specs).check()
    doc16 = [i for i in issues if i.code == "SPEC-DOC-016"]
    assert doc16 == [], [i.to_dict() for i in doc16]


def test_semver_folder_name_non_semver_new_release_warns(tmp_path: Path) -> None:
    """A release folder named 'my-feature-v1' with Created: >= cutoff raises SPEC-DOC-016."""
    specs = _make_clean_specs_tree(tmp_path, release_id="my-feature-v1")
    # Created after RELEASE_VINTAGE_CUTOFF (2026-06-04) so it is enforced, not grandfathered.
    (specs / "releases" / "my-feature-v1" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-06-10\n\nContent.\n",
        encoding="utf-8",
    )
    from datetime import date as _date

    with patch("dadaia_workspace.features.specs.doctor.date") as mock_date:
        mock_date.today.return_value = _date(2026, 6, 15)
        mock_date.side_effect = lambda *a, **kw: _date(*a, **kw)
        issues = SpecsDoctor(specs).check()
    doc16 = [i for i in issues if i.code == "SPEC-DOC-016"]
    assert doc16, "Expected SPEC-DOC-016 for non-SemVer folder name"


# ============================================================================
# TREE invariants (spec-context-tree-v2)
# ============================================================================


def _make_full_tree(root: Path) -> Path:
    """Like _make_clean_specs_tree but also adds audits/, backlog/, bugs/, releases/ dirs,
    and specs/AGENTS.md from the canonical template so TREE invariants pass."""
    specs = _make_clean_specs_tree(root)
    # TREE-4: ensure all required dirs exist (including audits/ added in T-021-16)
    for dirname in ("audits", "backlog", "bugs", "releases"):
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


def test_tree3_missing_architecture_md_triggers_warning(tmp_path: Path) -> None:
    """TREE-3: memory/architecture.md absent emits a warn-only TREE-3 issue."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "memory" / "architecture.md").unlink()
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree3 = [i for i in issues if i.code == "TREE-3"]
    assert tree3, "Expected TREE-3 WARNING for missing architecture.md"
    assert tree3[0].severity == Severity.WARNING
    assert not tree3[0].fixable


def test_tree3_has_no_autofix(tmp_path: Path) -> None:
    """TREE-3 fix() must not create operator-authored memory atoms."""
    specs = _make_clean_specs_tree(tmp_path)
    arch_md = specs / "memory" / "architecture.md"
    arch_md.unlink()
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    tree3 = [i for i in issues if i.code == "TREE-3"]
    assert tree3, "Pre-condition: TREE-3 must be found"
    fixed = doctor.fix(issues)
    # No TREE-3 issues should have been fixed
    tree3_fixed = [i for i in fixed if i.code == "TREE-3"]
    assert tree3_fixed == [], "fix() must NOT fix TREE-3 (no auto-fix for .md atoms)"
    # architecture.md must still be absent
    assert not arch_md.exists(), "fix() must NOT create architecture.md for TREE-3"
    # TREE-3 still appears after fix
    residual = doctor.check()
    assert any(i.code == "TREE-3" for i in residual)


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


def test_fresh_scaffold_passes_all_tree_invariants(tmp_path: Path) -> None:
    """A freshly scaffolded workspace produces no TREE errors."""
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
        (bugs_dir / "README.md").write_text(
            src_readme.read_text(encoding="utf-8"), encoding="utf-8"
        )
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
    assert tree_errors == [], (
        f"Unexpected TREE errors on fresh scaffold: {[i.to_dict() for i in tree_errors]}"
    )


# ---- CAT-1: catalog.json ↔ feature atom sync check


def _make_catalog_json(product_dir: Path, slugs: list[str]) -> None:
    """Write a minimal but valid catalog.json with the given slugs (paths use .md)."""
    import json as _json
    from datetime import UTC, datetime

    features = [
        {
            "rank": i + 1,
            "slug": slug,
            "title": slug,
            "summary": "",
            "path": f"specs/memory/product/{slug}.md",
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


def _write_feature_md(product_dir: Path, slug: str) -> None:
    """Write a minimal valid feature .md atom for the given slug."""
    content = f"""\
---
slug: {slug}
title: {slug}
category: product
tldr: 'Does {slug}.'
summary: 'Does {slug}.'
tags: []
agent_tier: self-pull
token_estimate: 100
last_updated: '2026-06-01'
release_origin: test-release
---

## Propósito

{slug} feature.
"""
    (product_dir / f"{slug}.md").write_text(content, encoding="utf-8")


def test_cat1_absent_catalog_with_feature_mds_triggers_warning(tmp_path: Path) -> None:
    """CAT-1: catalog.json absent + 3 feature .md atoms → one CAT-1 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    # Add two more feature .md atoms (feature-a.md is already in the clean tree)
    _write_feature_md(product_dir, "feature-b")
    _write_feature_md(product_dir, "feature-c")
    # No catalog.json
    assert not (product_dir / "catalog.json").exists()

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1, "Expected CAT-1 WARNING when catalog.json is absent and .md atoms exist"
    assert cat1[0].severity == Severity.WARNING
    # Single warning (not one per file)
    assert len(cat1) == 1


def test_cat1_absent_catalog_no_feature_mds_no_warning(tmp_path: Path) -> None:
    """CAT-1: catalog.json absent but no feature .md atoms (only index.md) → no CAT-1."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    # Remove the feature-a.md so no feature atoms remain
    (product_dir / "feature-a.md").unlink()
    assert not (product_dir / "catalog.json").exists()

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1 == [], (
        f"Unexpected CAT-1 when no feature .md atoms present: {[i.description for i in cat1]}"
    )


def test_cat1_in_sync_catalog_no_warning(tmp_path: Path) -> None:
    """CAT-1: catalog.json present and in sync with .md feature atoms → no CAT-1."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    # feature-a.md already exists in clean tree; create matching catalog
    _make_catalog_json(product_dir, ["feature-a"])

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1 == [], f"Unexpected CAT-1 when catalog is in sync: {[i.description for i in cat1]}"


def test_cat1_stale_slug_warns_with_slug_name(tmp_path: Path) -> None:
    """CAT-1: catalog.json lists slug 'stale-feature' but no stale-feature.md → WARNING names slug."""
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


def test_cat1_extra_md_warns_with_slug_name(tmp_path: Path) -> None:
    """CAT-1: extra .md atom on disk not in catalog → WARNING names the slug."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    # Add a new .md atom that is NOT in the catalog
    _write_feature_md(product_dir, "new-feature")
    # Catalog lists only feature-a (not new-feature)
    _make_catalog_json(product_dir, ["feature-a"])

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1, "Expected CAT-1 WARNING for extra .md atom 'new-feature'"
    descriptions = " ".join(i.description for i in cat1)
    assert "new-feature" in descriptions, (
        f"Expected 'new-feature' to be named in CAT-1 description; got: {descriptions}"
    )
    assert all(i.severity == Severity.WARNING for i in cat1)


def test_cat1_both_stale_and_extra_emit_separate_warnings(tmp_path: Path) -> None:
    """CAT-1: one stale slug + one extra .md atom → two separate CAT-1 WARNINGs."""
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    _write_feature_md(product_dir, "new-feature")
    # Catalog has stale-slug (no .md file) but not new-feature or feature-a (extra atoms)
    _make_catalog_json(product_dir, ["stale-slug"])

    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    # At minimum: one for stale-slug, one for feature-a, one for new-feature
    assert len(cat1) >= 2, (
        f"Expected at least 2 CAT-1 WARNINGs; got {len(cat1)}: {[i.description for i in cat1]}"
    )


# ---- T-ENG-05: segment-aware active-release artifact checks (ADR-5) ----


def _segment_active(specs: Path, release_id: str, segment: str) -> None:
    """Convert a flat clean tree into a segmented one (move SPEC/PLAN/TASKS)."""
    rel = specs / "releases" / release_id
    seg = rel / segment
    seg.mkdir(parents=True, exist_ok=True)
    for fname in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (seg / fname).write_text((rel / fname).read_text(encoding="utf-8"), encoding="utf-8")
        (rel / fname).unlink()
    (specs / "releases" / "ACTIVE.md").write_text(
        f"release: {release_id}\nsegment: {segment}\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )


def test_segmented_active_release_artifacts_ok(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path, "v0.1.6")
    _segment_active(specs, "v0.1.6", "alpha-1")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-004" not in _codes(issues)


def test_segmented_active_release_missing_tasks_reports_doc_004(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path, "v0.1.6")
    _segment_active(specs, "v0.1.6", "alpha-1")
    (specs / "releases" / "v0.1.6" / "alpha-1" / "TASKS.md").unlink()
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-004" in _codes(issues)


# ---- T-021-01: flat-glob fix — subdir atom discovery in CAT-1 and SPEC-DOC-002 ----


def test_cat1_subdir_atom_is_found_no_phantom_warning(tmp_path: Path) -> None:
    """CAT-1 T-021-01: a product/<subdir>/atom.md is discovered by rglob.

    A catalog listing the slug and a matching .md in a subdirectory must produce
    zero CAT-1 warnings (the flat-glob bug would emit a phantom warning because
    it missed the nested atom).
    """
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    subdir = product_dir / "philosophy"
    subdir.mkdir(parents=True, exist_ok=True)
    (subdir / "product-vision.md").write_text(
        "---\nslug: product-vision\ntitle: Product Vision\ncategory: product\n"
        "tldr: 'Vision.'\nsummary: 'Vision summary.'\ntags: []\nagent_tier: self-pull\n"
        "token_estimate: 100\nlast_updated: '2026-06-07'\nrelease_origin: test-release\n---\n\n"
        "## Vision\n\nThe vision.\n",
        encoding="utf-8",
    )
    # catalog lists feature-a (flat) and product-vision (nested)
    _make_catalog_json(product_dir, ["feature-a", "product-vision"])
    issues = SpecsDoctor(specs).check()
    cat1 = [i for i in issues if i.code == "CAT-1"]
    assert cat1 == [], (
        f"Expected 0 CAT-1 warnings with subdir atom in sync; got: {[i.description for i in cat1]}"
    )


def test_spec_doc_002_subdir_atom_parsed_without_error(tmp_path: Path) -> None:
    """SPEC-DOC-002 T-021-01: a product/<subdir>/atom.md with a valid heading must parse cleanly.

    The rglob fix ensures nested atoms are validated; this test confirms a valid
    nested atom produces no SPEC-DOC-002 error.
    """
    specs = _make_clean_specs_tree(tmp_path)
    product_dir = specs / "memory" / "product"
    subdir = product_dir / "sdd"
    subdir.mkdir(parents=True, exist_ok=True)
    (subdir / "specs-doctor.md").write_text(
        "---\nslug: specs-doctor\ntitle: Specs Doctor\ncategory: product\n"
        "tldr: 'Doctor checks.'\nsummary: 'Doctor structural checks.'\ntags: []\n"
        "agent_tier: self-pull\ntoken_estimate: 100\nlast_updated: '2026-06-07'\n"
        "release_origin: test-release\n---\n\n## Propósito\n\nValidates specs.\n",
        encoding="utf-8",
    )
    issues = SpecsDoctor(specs).check()
    spec_doc_002 = [
        i for i in issues if i.code == "SPEC-DOC-002" and "specs-doctor.md" in (i.path or "")
    ]
    assert spec_doc_002 == [], (
        f"Expected no SPEC-DOC-002 for valid subdir atom; got: {[i.description for i in spec_doc_002]}"
    )


# ---- T-021-02: quality-assurance.md is canonical top-level + required by TREE-3 ----


def test_quality_assurance_md_not_flagged_as_legacy(tmp_path: Path) -> None:
    """T-021-02: specs/memory/quality-assurance.md must NOT be flagged as SPEC-DOC-002L.

    It is a canonical top-level memory atom (added to TOPLEVEL_MEMORY_FILES), so the
    legacy-orphan check must exempt it — identical to how architecture.md and tech-stack.md
    are exempted.
    """
    specs = _make_clean_specs_tree(tmp_path)
    # quality-assurance.md is already in the clean tree; doctor must not flag it
    issues = SpecsDoctor(specs).check()
    doc_002l = [
        i for i in issues if i.code == "SPEC-DOC-002L" and "quality-assurance.md" in (i.path or "")
    ]
    assert doc_002l == [], (
        f"quality-assurance.md must not be flagged as legacy: {[i.description for i in doc_002l]}"
    )


def test_tree3_missing_quality_assurance_md_triggers_warning(tmp_path: Path) -> None:
    """TREE-3 T-021-02: absence of top-level quality-assurance.md emits a TREE-3 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    qa_md = specs / "memory" / "quality-assurance.md"
    qa_md.unlink()
    issues = SpecsDoctor(specs).check()
    tree3 = [
        i for i in issues if i.code == "TREE-3" and "quality-assurance.md" in (i.description or "")
    ]
    assert tree3, "Expected TREE-3 WARNING for missing quality-assurance.md"
    assert tree3[0].severity == Severity.WARNING
    assert not tree3[0].fixable


def test_quality_assurance_md_required_by_tree3_validated_by_spec_doc_002(tmp_path: Path) -> None:
    """T-021-02: quality-assurance.md is also checked by SPEC-DOC-002 (required top-level check).

    SPEC-DOC-002 must flag absence of quality-assurance.md as a missing required atom.
    """
    specs = _make_clean_specs_tree(tmp_path)
    qa_md = specs / "memory" / "quality-assurance.md"
    qa_md.unlink()
    issues = SpecsDoctor(specs).check()
    # SPEC-DOC-002 covers required top-level files → must fire for missing quality-assurance.md
    spec_doc_002 = [
        i
        for i in issues
        if i.code == "SPEC-DOC-002" and "quality-assurance.md" in (i.description or "")
    ]
    assert spec_doc_002, (
        "Expected SPEC-DOC-002 for missing quality-assurance.md; "
        f"got: {[i.to_dict() for i in issues if 'quality' in str(i)]}"
    )


# ---- T-021-03: specs/memory/AGENTS.md check is WARN-level (TREE-5M) ----


def test_memory_agents_md_absent_emits_tree5m_warning(tmp_path: Path) -> None:
    """T-021-03: absence of specs/memory/AGENTS.md emits a TREE-5M WARNING (never ERROR)."""
    specs = _make_clean_specs_tree(tmp_path)
    # Ensure memory/AGENTS.md is absent
    memory_agents = specs / "memory" / "AGENTS.md"
    if memory_agents.exists():
        memory_agents.unlink()
    issues = SpecsDoctor(specs).check()
    tree5m = [i for i in issues if i.code == "TREE-5M"]
    assert tree5m, "Expected TREE-5M WARNING for missing specs/memory/AGENTS.md"
    assert tree5m[0].severity == Severity.WARNING, (
        f"TREE-5M must be WARNING, got: {tree5m[0].severity}"
    )
    assert not tree5m[0].fixable
    # Bug specs-doctor-tree5m-remediation-wrong (v0.1.48 W3): the remediation must
    # state the REAL repair — restore/edit the specs-tree copy directly from the
    # public/data source — and must not prescribe `public install` as a projection
    # mechanism (install only scaffolds the file when missing; it never updates it).
    description = tree5m[0].description
    assert "public/data/memory-AGENTS.md" in description, (
        f"TREE-5M remediation must name the canonical source. Got: {description}"
    )
    assert "does NOT project" in description, (
        f"TREE-5M remediation must state install does not project the file. Got: {description}"
    )
    assert "Project it by running" not in description, (
        f"TREE-5M remediation must not prescribe install as projection. Got: {description}"
    )


def test_memory_agents_md_absent_does_not_cause_errors(tmp_path: Path) -> None:
    """T-021-03: absence of specs/memory/AGENTS.md must NOT make doctor exit non-zero.

    TREE-5M is always WARNING-level; the doctor exit code is driven by ERROR severity.
    """
    specs = _make_clean_specs_tree(tmp_path)
    memory_agents = specs / "memory" / "AGENTS.md"
    if memory_agents.exists():
        memory_agents.unlink()
    issues = SpecsDoctor(specs).check()
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == [], (
        f"No errors expected when memory/AGENTS.md is absent; got: {[i.to_dict() for i in errors]}"
    )


def test_memory_agents_md_present_suppresses_tree5m(tmp_path: Path) -> None:
    """T-021-03: when specs/memory/AGENTS.md exists, TREE-5M must not fire."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "memory" / "AGENTS.md").write_text(
        "# Memory Ownership Contract\n\nWrite-locked to product-engineer during CLOSURE.\n",
        encoding="utf-8",
    )
    issues = SpecsDoctor(specs).check()
    tree5m = [i for i in issues if i.code == "TREE-5M"]
    assert tree5m == [], f"Unexpected TREE-5M when memory/AGENTS.md is present: {tree5m}"


# ============================================================================
# T-021-16: TREE-4 covers audits/ + scaffold regression tests
# ============================================================================


def test_tree4_missing_audits_triggers_warning(tmp_path: Path) -> None:
    """T-021-16 (i): specs/audits/ absent emits a TREE-4 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    # Ensure audits/ is absent
    audits = specs / "audits"
    if audits.exists():
        import shutil

        shutil.rmtree(audits)
    doctor = SpecsDoctor(specs, public_dir=_PUBLIC_DIR)
    issues = doctor.check()
    tree4 = [i for i in issues if i.code == "TREE-4"]
    assert any("audits" in i.description for i in tree4), (
        f"Expected TREE-4 for missing audits/; got {[i.description for i in tree4]}"
    )
    assert all(i.severity == Severity.WARNING for i in tree4)


def test_tree4_fix_creates_audits_dir(tmp_path: Path) -> None:
    """T-021-16 (i): TREE-4 auto-fix creates audits/ with README.md and .gitkeep."""
    specs = _make_clean_specs_tree(tmp_path)
    audits = specs / "audits"
    if audits.exists():
        import shutil

        shutil.rmtree(audits)
    doctor = SpecsDoctor(specs, public_dir=_PUBLIC_DIR)
    issues = doctor.check()
    tree4_audits = [i for i in issues if i.code == "TREE-4" and "audits" in i.description]
    assert tree4_audits, "Pre-condition: TREE-4 for audits/ must be present"
    doctor.fix(issues)
    assert audits.exists(), "specs/audits/ must be created by fix()"
    assert (audits / "README.md").exists(), "specs/audits/README.md must be created"
    assert (audits / ".gitkeep").exists(), "specs/audits/.gitkeep must be created"
    # No residual TREE-4 for audits after fix
    residual = [i for i in doctor.check() if i.code == "TREE-4" and "audits" in i.description]
    assert residual == [], f"Residual TREE-4 for audits/ after fix: {residual}"


def test_scaffold_canonical_tree_includes_audits_and_memory_agents(tmp_path: Path) -> None:
    """T-021-16 (a): fresh scaffold via shutil.copytree from scaffold source yields full
    canonical tree: audits/, memory/AGENTS.md, and memory/quality-assurance.md."""
    import shutil

    specs_dir = tmp_path / "specs"
    shutil.copytree(str(_SCAFFOLD_DIR), str(specs_dir))

    assert (specs_dir / "audits").is_dir(), "audits/ must exist in scaffolded tree"
    assert (specs_dir / "audits" / "README.md").exists(), "audits/README.md must exist"
    assert (specs_dir / "memory" / "AGENTS.md").exists(), "memory/AGENTS.md must exist"
    assert (specs_dir / "memory" / "quality-assurance.md").exists(), (
        "memory/quality-assurance.md must exist"
    )
