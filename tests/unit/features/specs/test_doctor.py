"""Unit tests for SpecsDoctor structural checks and tree invariants.

CRITICAL doctor: every invariant code keeps exactly one sad + one silent row here; the
doctor golden (test_doctor_golden.py) pins ordering/wording across the full family set.
The two negative anchors (clean-tree-no-errors, fresh-scaffold-passes-all-TREE) are kept
as named tests — they are the only assertions that the WHOLE checker set stays silent on
a genuinely valid tree, a property no single-code row can prove.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
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
    """Keep SpecsDoctor unit tests focused on in-process structural checks.

    v0.1.55 FR1: LINT-1 moved off the coordinator into ``doctor_memory.MemoryValidator``;
    stub its public method so the coordinator's ``check()`` never shells out.
    """
    from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

    monkeypatch.setattr(MemoryValidator, "check_lint1_memory_atoms", lambda self: [])


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


def _make_catalog_json(product_dir: Path, slugs: list[str]) -> None:
    """Write a minimal but valid catalog.json with the given slugs (paths use .md)."""
    import json as _json

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


# ---------------------------------------------------------------------------
# The two negative anchors — kept named, they are the only proof the WHOLE
# checker set stays silent on a genuinely valid tree.
# ---------------------------------------------------------------------------


def test_clean_tree_has_no_errors(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    issues = SpecsDoctor(specs).check()
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == [], errors


def test_freshly_opened_release_segment_is_doctor_clean(tmp_path: Path) -> None:
    """Bug fresh-release-scaffold-emits-spec-doctor-warnings-042 (Consumer R1-A): the
    canonical 'specs release open' output — Draft SPEC/PLAN/TASKS with ACTIVE.md
    phase SPEC — instantly drew three SPEC-DOC-004 warnings. Draft IS the legitimate
    state of an authoring-phase release; the scaffolder and the doctor must agree on
    the fresh state (0 errors, 0 warnings)."""
    from dadaia_workspace.features.specs.scaffolder import scaffold_release_segment

    specs = _make_clean_specs_tree(tmp_path, "v0.1.0")
    # Re-open as the real scaffolder does: scaffold the segment + phase SPEC.
    for fname in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (specs / "releases" / "v0.1.0" / fname).unlink()
    result = scaffold_release_segment(specs, "v0.1.0", "alpha-1")
    assert not result.errors, result.errors
    (specs / "releases" / "ACTIVE.md").write_text(
        "release: v0.1.0\nsegment: alpha-1\nphase: SPEC\n", encoding="utf-8"
    )

    issues = SpecsDoctor(specs).check()
    doc004 = [i for i in issues if i.code == "SPEC-DOC-004"]
    assert doc004 == [], [i.to_dict() for i in doc004]

    # The warning is NOT lost where it matters: a Draft artifact in an
    # implementation-bound phase still warns.
    (specs / "releases" / "ACTIVE.md").write_text(
        "release: v0.1.0\nsegment: alpha-1\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    issues_impl = SpecsDoctor(specs).check()
    assert any(i.code == "SPEC-DOC-004" for i in issues_impl)


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

    bugs_dir = specs / "bugs"
    bugs_dir.mkdir(exist_ok=True)
    src_readme = _SCAFFOLD_DIR / "bugs" / "README.md"
    if src_readme.exists():
        (bugs_dir / "README.md").write_text(
            src_readme.read_text(encoding="utf-8"), encoding="utf-8"
        )
    (bugs_dir / ".gitkeep").write_text("", encoding="utf-8")

    agents_template = _TEMPLATES_DIR / "specs-AGENTS.md"
    if agents_template.exists():
        (specs / "AGENTS.md").write_text(
            agents_template.read_text(encoding="utf-8"), encoding="utf-8"
        )

    doctor = SpecsDoctor(specs, public_dir=_PUBLIC_DIR)
    issues = doctor.check()

    tree_errors = [i for i in issues if i.code.startswith("TREE-") and i.severity == Severity.ERROR]
    assert tree_errors == [], (
        f"Unexpected TREE errors on fresh scaffold: {[i.to_dict() for i in tree_errors]}"
    )

    # Also assert the canonical scaffold copytree route (T-021-16 (a)) yields the same
    # full tree independent of the scaffold() function's own file list.
    import shutil

    specs2_dir = tmp_path.parent / (tmp_path.name + "-copytree") / "specs"
    shutil.copytree(str(_SCAFFOLD_DIR), str(specs2_dir))
    assert (specs2_dir / "audits").is_dir()
    assert (specs2_dir / "audits" / "README.md").exists()
    assert (specs2_dir / "memory" / "AGENTS.md").exists()
    assert (specs2_dir / "memory" / "quality-assurance.md").exists()


# ---------------------------------------------------------------------------
# (a) Sad matrix: each SPEC-DOC/TREE/CAT code fires on its minimal broken fixture
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "mutate", "expected_code"),
    [
        pytest.param(
            "missing-constitution",
            lambda specs: (specs / "constitution.md").unlink(),
            "SPEC-DOC-001",
            id="doc001-missing-constitution",
        ),
        pytest.param(
            "missing-product-index",
            lambda specs: (specs / "memory" / "product" / "index.md").unlink(),
            "SPEC-DOC-002",
            id="doc002-missing-product-index",
        ),
        pytest.param(
            "missing-architecture",
            lambda specs: (specs / "memory" / "architecture.md").unlink(),
            "SPEC-DOC-002",
            id="doc002-missing-architecture",
        ),
        pytest.param(
            "product-feature-no-heading",
            lambda specs: (specs / "memory" / "product" / "feature-a.md").write_text(
                "---\nslug: feature-a\ntitle: Feature A\n---\n\nNo heading here, only prose.\n",
                encoding="utf-8",
            ),
            "SPEC-DOC-002",
            id="doc002-feature-without-heading",
        ),
        pytest.param(
            "legacy-md-at-memory-root",
            lambda specs: (specs / "memory" / "legacy-notes.md").write_text(
                "# legacy", encoding="utf-8"
            ),
            "SPEC-DOC-002L",
            id="doc002l-legacy-markdown",
        ),
        pytest.param(
            "legacy-html-at-memory-root",
            lambda specs: (specs / "memory" / "product.html").write_text(
                "<html><body><h1>x</h1></body></html>", encoding="utf-8"
            ),
            "SPEC-DOC-002L",
            id="doc002l-legacy-html",
        ),
        pytest.param(
            "history-heading-changelog",
            lambda specs: (specs / "memory" / "product" / "feature-a.md").write_text(
                "---\nslug: feature-a\ntitle: Feature A\n---\n\n## Propósito\n\nDoes A.\n\n"
                "## Changelog\n\nHistorical details.\n",
                encoding="utf-8",
            ),
            "SPEC-DOC-008",
            id="doc008-history-heading-changelog",
        ),
        pytest.param(
            "history-heading-history",
            lambda specs: (specs / "memory" / "product" / "feature-a.md").write_text(
                "---\nslug: feature-a\ntitle: Feature A\n---\n\n## Propósito\n\nDoes A.\n\n"
                "## History\n\nHistorical details.\n",
                encoding="utf-8",
            ),
            "SPEC-DOC-008",
            id="doc008-history-heading-history",
        ),
        pytest.param(
            "missing-active-md",
            lambda specs: (specs / "releases" / "ACTIVE.md").unlink(),
            "SPEC-DOC-003",
            id="doc003-missing-active-md",
        ),
        pytest.param(
            "non-canonical-phase",
            lambda specs: (specs / "releases" / "ACTIVE.md").write_text(
                "release: r1\nphase: WORKING\n", encoding="utf-8"
            ),
            "SPEC-DOC-003",
            id="doc003-non-canonical-phase",
        ),
        pytest.param(
            "empty-release-value",
            lambda specs: (specs / "releases" / "ACTIVE.md").write_text(
                "release:   \nphase: TASKS\n", encoding="utf-8"
            ),
            "SPEC-DOC-003",
            id="doc003-empty-release-value",
        ),
        pytest.param(
            "empty-phase-value",
            lambda specs: (specs / "releases" / "ACTIVE.md").write_text(
                "release: r1\nphase:   \n", encoding="utf-8"
            ),
            "SPEC-DOC-003",
            id="doc003-empty-phase-value",
        ),
        pytest.param(
            "missing-plan-in-active-release",
            lambda specs: (specs / "releases" / "r1" / "PLAN.md").unlink(),
            "SPEC-DOC-004",
            id="doc004-missing-plan",
        ),
        pytest.param(
            "non-canonical-status",
            lambda specs: (specs / "releases" / "r1" / "SPEC.md").write_text(
                "# Spec\n\n> **Status:** Accepted\n", encoding="utf-8"
            ),
            "SPEC-DOC-004",
            id="doc004-non-canonical-status",
        ),
        pytest.param(
            "archived-release-no-closure",
            lambda specs: (
                (specs / "_archive" / "releases" / "old-release").mkdir(parents=True),
                (specs / "_archive" / "releases" / "old-release" / "SPEC.md").write_text(
                    "# spec", encoding="utf-8"
                ),
            ),
            "SPEC-DOC-006",
            id="doc006-archived-without-closure",
        ),
        pytest.param(
            "orphan-legacy-feature",
            lambda specs: (
                (specs / "features" / "old-feature").mkdir(parents=True),
                (specs / "features" / "old-feature" / "SPEC.md").write_text(
                    "# legacy", encoding="utf-8"
                ),
            ),
            "SPEC-DOC-007",
            id="doc007-orphan-legacy-feature",
        ),
        pytest.param(
            "active-release-id-without-dir",
            lambda specs: (specs / "releases" / "ACTIVE.md").write_text(
                "release: missing-id\nphase: IMPLEMENTATION\n", encoding="utf-8"
            ),
            "SPEC-DOC-009",
            id="doc009-release-id-without-dir",
        ),
    ],
)
def test_sad_matrix(tmp_path: Path, case: str, mutate, expected_code: str) -> None:  # type: ignore[no-untyped-def]
    specs = _make_clean_specs_tree(tmp_path)
    mutate(specs)
    issues = SpecsDoctor(specs).check()
    assert expected_code in _codes(issues), f"{case}: expected {expected_code} in {_codes(issues)}"
    if case == "missing-constitution":
        # to_dict() shape check, folded onto this row's issue payload.
        matching = next(i for i in issues if i.code == "SPEC-DOC-001")
        payload = matching.to_dict()
        assert set(payload.keys()) == {"code", "severity", "description", "path"}


# ---------------------------------------------------------------------------
# (b) Silent matrix: each code's negative/exempt fixture stays clean
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "mutate", "code"),
    [
        pytest.param(
            "agents-md-exempt-from-doc002l",
            lambda specs: (specs / "memory" / "AGENTS.md").write_text(
                "# Memory contract\n", encoding="utf-8"
            ),
            "SPEC-DOC-002L",
            id="agents-md-exempt-doc002l",
        ),
        pytest.param(
            "quality-assurance-not-legacy",
            lambda specs: None,  # already present in the clean tree
            "SPEC-DOC-002L",
            id="quality-assurance-not-legacy",
        ),
        pytest.param(
            "agents-md-present-does-not-suppress-other-legacy-md",
            lambda specs: (
                (specs / "memory" / "AGENTS.md").write_text(
                    "# Memory contract\n", encoding="utf-8"
                ),
                (specs / "memory" / "old-note.md").write_text("# legacy note\n", encoding="utf-8"),
            ),
            None,  # positive-side assertion handled below, not a silent row
            id="agents-md-does-not-blanket-exempt",
        ),
        pytest.param(
            "subdir-atom-parses-cleanly",
            lambda specs: (
                (specs / "memory" / "product" / "sdd").mkdir(parents=True, exist_ok=True),
                (specs / "memory" / "product" / "sdd" / "specs-doctor.md").write_text(
                    "---\nslug: specs-doctor\ntitle: Specs Doctor\ncategory: product\n"
                    "tldr: 'Doctor checks.'\nsummary: 'Doctor structural checks.'\ntags: []\n"
                    "agent_tier: self-pull\ntoken_estimate: 100\nlast_updated: '2026-06-07'\n"
                    "release_origin: test-release\n---\n\n## Propósito\n\nValidates specs.\n",
                    encoding="utf-8",
                ),
            ),
            "SPEC-DOC-002",
            id="doc002-subdir-atom-parsed-without-error",
        ),
    ],
)
def test_silent_matrix(tmp_path: Path, case: str, mutate, code: str | None) -> None:  # type: ignore[no-untyped-def]
    specs = _make_clean_specs_tree(tmp_path)
    mutate(specs)
    issues = SpecsDoctor(specs).check()
    if case == "agents-md-does-not-blanket-exempt":
        doc_002l = [
            i for i in issues if i.code == "SPEC-DOC-002L" and "old-note.md" in (i.path or "")
        ]
        assert doc_002l, "Expected SPEC-DOC-002L for old-note.md but got none"
        return
    matching = [i for i in issues if i.code == code]
    assert matching == [], f"{case}: unexpected {code}: {[m.description for m in matching]}"


# ---------------------------------------------------------------------------
# (c) TREE fix-behavior: TREE-4 creates dirs; TREE-1/2/3/5/5M/6/7 have NO auto-fix
# ---------------------------------------------------------------------------


def test_tree4_creates_missing_dirs_others_have_no_autofix(tmp_path: Path) -> None:
    import shutil

    # TREE-4 fix creates backlog/, bugs/ (and audits/) with README.md + .gitkeep.
    specs = _make_clean_specs_tree(tmp_path)
    for dirname in ("backlog", "bugs", "audits"):
        d = specs / dirname
        if d.exists():
            shutil.rmtree(d)
    doctor = SpecsDoctor(specs, public_dir=_PUBLIC_DIR)
    issues = doctor.check()
    tree4 = [i for i in issues if i.code == "TREE-4"]
    assert tree4, "Pre-condition: TREE-4 issues must exist"
    fixed = doctor.fix(issues)
    assert len(fixed) >= 2
    for dirname in ("backlog", "bugs", "audits"):
        d = specs / dirname
        assert d.exists(), f"specs/{dirname}/ must be created by fix()"
        assert (d / "README.md").exists()
        assert (d / ".gitkeep").exists()
    residual = [i for i in doctor.check() if i.code == "TREE-4"]
    assert residual == [], f"Residual TREE-4 after fix: {[i.description for i in residual]}"

    # TREE-1: foundation/ is never auto-removed.
    specs1 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree1"))
    foundation = specs1 / "foundation"
    foundation.mkdir()
    (foundation / "content.md").write_text("# Protected", encoding="utf-8")
    doctor1 = SpecsDoctor(specs1, templates_dir=_TEMPLATES_DIR)
    issues1 = doctor1.check()
    tree1 = [i for i in issues1 if i.code == "TREE-1"]
    assert tree1 and not tree1[0].fixable
    doctor1.fix(issues1)
    assert foundation.exists()

    # TREE-2: root SPEC.md is never auto-moved.
    specs2 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree2"))
    root_spec = specs2 / "SPEC.md"
    root_spec.write_text("# Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")
    doctor2 = SpecsDoctor(specs2, templates_dir=_TEMPLATES_DIR)
    issues2 = doctor2.check()
    tree2 = [i for i in issues2 if i.code == "TREE-2"]
    assert tree2 and not tree2[0].fixable
    doctor2.fix(issues2)
    assert root_spec.exists()

    # TREE-3: missing architecture.md never auto-created; missing quality-assurance.md
    # trips both TREE-3 (WARNING, no autofix) and SPEC-DOC-002.
    specs3 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree3"))
    arch_md = specs3 / "memory" / "architecture.md"
    arch_md.unlink()
    doctor3 = SpecsDoctor(specs3, templates_dir=_TEMPLATES_DIR)
    issues3 = doctor3.check()
    tree3 = [i for i in issues3 if i.code == "TREE-3"]
    assert tree3 and not tree3[0].fixable
    fixed3 = doctor3.fix(issues3)
    assert [i for i in fixed3 if i.code == "TREE-3"] == []
    assert not arch_md.exists()

    specs3b = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree3-qa"))
    qa_md = specs3b / "memory" / "quality-assurance.md"
    qa_md.unlink()
    issues3b = SpecsDoctor(specs3b).check()
    tree3_qa = [
        i
        for i in issues3b
        if i.code == "TREE-3" and "quality-assurance.md" in (i.description or "")
    ]
    assert tree3_qa and tree3_qa[0].severity == Severity.WARNING and not tree3_qa[0].fixable
    spec_doc_002_qa = [
        i
        for i in issues3b
        if i.code == "SPEC-DOC-002" and "quality-assurance.md" in (i.description or "")
    ]
    assert spec_doc_002_qa

    # TREE-5: missing / drifted / canonical AGENTS.md.
    specs_missing = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree5-missing"))
    agents_md = specs_missing / "AGENTS.md"
    if agents_md.exists():
        agents_md.unlink()
    doctor_missing = SpecsDoctor(specs_missing, templates_dir=_TEMPLATES_DIR)
    tree5_missing = [i for i in doctor_missing.check() if i.code == "TREE-5"]
    assert tree5_missing and tree5_missing[0].severity == Severity.WARNING
    assert not tree5_missing[0].fixable

    specs_drift = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree5-drift"))
    (specs_drift / "AGENTS.md").write_text(
        "# AGENTS\n\nCustomised content that differs from the canonical template.\n",
        encoding="utf-8",
    )
    doctor_drift = SpecsDoctor(specs_drift, templates_dir=_TEMPLATES_DIR)
    tree5_drift = [i for i in doctor_drift.check() if i.code == "TREE-5"]
    assert tree5_drift and not tree5_drift[0].fixable
    assert "drift" in tree5_drift[0].description.lower()

    specs_ok = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree5-ok"))
    canonical = (_TEMPLATES_DIR / "specs-AGENTS.md").read_text(encoding="utf-8")
    (specs_ok / "AGENTS.md").write_text(canonical, encoding="utf-8")
    doctor_ok = SpecsDoctor(specs_ok, templates_dir=_TEMPLATES_DIR)
    tree5_ok = [i for i in doctor_ok.check() if i.code == "TREE-5"]
    assert tree5_ok == []

    # TREE-5M: absence emits WARNING (never ERROR) with the real-repair remediation
    # text; presence suppresses it entirely.
    specs_5m_absent = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree5m-absent"))
    memory_agents = specs_5m_absent / "memory" / "AGENTS.md"
    if memory_agents.exists():
        memory_agents.unlink()
    issues_5m = SpecsDoctor(specs_5m_absent).check()
    tree5m = [i for i in issues_5m if i.code == "TREE-5M"]
    assert tree5m and tree5m[0].severity == Severity.WARNING and not tree5m[0].fixable
    description = tree5m[0].description
    assert "public/data/memory-AGENTS.md" in description
    assert "does NOT project" in description
    assert "Project it by running" not in description
    errors_5m = [i for i in issues_5m if i.severity == Severity.ERROR]
    assert errors_5m == []

    specs_5m_present = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree5m-present"))
    (specs_5m_present / "memory" / "AGENTS.md").write_text(
        "# Memory Ownership Contract\n\nWrite-locked to product-engineer during CLOSURE.\n",
        encoding="utf-8",
    )
    tree5m_present = [i for i in SpecsDoctor(specs_5m_present).check() if i.code == "TREE-5M"]
    assert tree5m_present == []

    # TREE-6: missing PLAN.md in IMPLEMENTATION phase never auto-created.
    specs6 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree6"))
    plan = specs6 / "releases" / "r1" / "PLAN.md"
    plan.unlink()
    doctor6 = SpecsDoctor(specs6, templates_dir=_TEMPLATES_DIR)
    issues6 = doctor6.check()
    tree6 = [i for i in issues6 if i.code == "TREE-6"]
    assert tree6 and tree6[0].severity == Severity.ERROR and not tree6[0].fixable
    doctor6.fix(issues6)
    assert not plan.exists()

    # TREE-7: bug missing session_id is never auto-repaired; session_id: null passes.
    specs7 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree7"))
    bugs_dir7 = specs7 / "bugs"
    bugs_dir7.mkdir(exist_ok=True)
    bug_path = bugs_dir7 / "missing-session.md"
    original = "title: test\nseverity: low\nopened: 2026-05-30\n"
    bug_path.write_text(original, encoding="utf-8")
    doctor7 = SpecsDoctor(specs7, templates_dir=_TEMPLATES_DIR)
    issues7 = doctor7.check()
    tree7 = [i for i in issues7 if i.code == "TREE-7"]
    assert tree7 and tree7[0].severity == Severity.ERROR and not tree7[0].fixable
    doctor7.fix(issues7)
    assert bug_path.read_text(encoding="utf-8") == original

    specs7b = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree7-ok"))
    bugs_dir7b = specs7b / "bugs"
    bugs_dir7b.mkdir(exist_ok=True)
    (bugs_dir7b / "some-bug.md").write_text(
        "title: Something broke\nseverity: high\nopened: 2026-05-30\nsession_id: null\n\n"
        "## Description\n\nBroken.",
        encoding="utf-8",
    )
    tree7b = [i for i in SpecsDoctor(specs7b).check() if i.code == "TREE-7"]
    assert tree7b == [], f"Unexpected TREE-7: {[i.description for i in tree7b]}"


# ---------------------------------------------------------------------------
# (d) Boundary/cutoff rows: oversized-plan, hotfix staleness, SemVer folder naming
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("created", "expected_severity"),
    [
        pytest.param("2026-06-01", Severity.ERROR, id="oversized-plan-after-cutoff-error"),
        pytest.param("2026-04-01", Severity.WARNING, id="oversized-plan-before-cutoff-warning"),
    ],
)
def test_doc005_plan_line_limit_cutoff_boundary(
    tmp_path: Path, created: str, expected_severity: Severity
) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    big = "# Plan\n\n> **Status:** Aprovado\n\n" + "\n".join(f"- line {i}" for i in range(400))
    (specs / "releases" / "r1" / "PLAN.md").write_text(big, encoding="utf-8")
    (specs / "releases" / "r1" / "SPEC.md").write_text(
        f"# Spec\n\n> **Status:** Aprovado\n> **Created:** {created}\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    doc5 = [i for i in issues if i.code == "SPEC-DOC-005"]
    assert doc5 and doc5[0].severity == expected_severity


def test_doc012_retired_never_fires_on_a_planted_candidates_md(tmp_path: Path) -> None:
    """SPEC v0.12.0 T-120-08 (ADR D10): SPEC-DOC-012 (candidates.md bullet-format check)
    is retired with candidates.md itself. A malformed candidates.md left on disk (e.g. a
    stray, not-yet-archived leftover) never fires SPEC-DOC-012 again — the archived-only
    single-source doctor has no check left that reads that file's bullet grammar. It is
    still flagged, but as SPEC-DOC-035 (the loose-file single-source invariant): a
    recorded supersession, replacing the deleted `test_doc012_bullet_format_matrix`
    (11 parametrized cases; subject retired, TASKS T-120-08, A5.4)."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "backlog" / "candidates.md").write_text(
        "# Backlog\n\n## Candidatas ativas\n\n- bad-feature — Missing the owner field\n",
        encoding="utf-8",
    )
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-012" not in {i.code for i in issues}
    doc035 = [i for i in issues if i.code == "SPEC-DOC-035"]
    assert any("candidates.md" in (i.path or "") for i in doc035)


@pytest.mark.parametrize(
    ("release_id", "created", "today", "expect_doc016"),
    [
        pytest.param("v1.2.3", "2026-06-01", (2026, 6, 15), False, id="semver-name-ok"),
        pytest.param(
            "sdd-release-lifecycle-v1",
            "2026-05-01",
            (2026, 6, 15),
            False,
            id="vintage-grandfathered",
        ),
        pytest.param(
            "bad-name", "2026-06-01", (2026, 5, 20), False, id="before-cutoff-not-checked"
        ),
        pytest.param(
            "my-feature-v1", "2026-06-10", (2026, 6, 15), True, id="non-semver-new-release-warns"
        ),
    ],
)
def test_doc016_semver_folder_naming_boundary(
    tmp_path: Path,
    release_id: str,
    created: str,
    today: tuple[int, int, int],
    expect_doc016: bool,
) -> None:
    specs = _make_clean_specs_tree(tmp_path, release_id=release_id)
    (specs / "releases" / release_id / "SPEC.md").write_text(
        f"# Spec\n\n> **Status:** Aprovado\n> **Created:** {created}\n\nContent.\n",
        encoding="utf-8",
    )
    with patch("dadaia_workspace.features.specs.doctor_release.date") as mock_date:
        mock_date.today.return_value = date(*today)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        issues = SpecsDoctor(specs).check()
    doc16 = [i for i in issues if i.code == "SPEC-DOC-016"]
    if expect_doc016:
        assert doc16, "Expected SPEC-DOC-016 for non-SemVer folder name"
    else:
        assert doc16 == [], [i.to_dict() for i in doc16]


# ---------------------------------------------------------------------------
# (e) Segmented release pair (ADR-5) — 1 pair
# ---------------------------------------------------------------------------


def test_segmented_active_release_artifacts_matrix(tmp_path: Path) -> None:
    specs_ok = _make_clean_specs_tree(tmp_path, "v0.1.6")
    _segment_active(specs_ok, "v0.1.6", "alpha-1")
    issues_ok = SpecsDoctor(specs_ok).check()
    assert "SPEC-DOC-004" not in _codes(issues_ok)

    specs_bad = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-seg-bad"), "v0.1.6")
    _segment_active(specs_bad, "v0.1.6", "alpha-1")
    (specs_bad / "releases" / "v0.1.6" / "alpha-1" / "TASKS.md").unlink()
    issues_bad = SpecsDoctor(specs_bad).check()
    assert "SPEC-DOC-004" in _codes(issues_bad)


# ---------------------------------------------------------------------------
# v0.4.3 T-043-22 [Arm-B rider] bug specs-doctor-segment-router-silent-skip —
# AB.1-AB.4. Intent: BUG — a live segment pointer at a MISSING directory must
# produce an explicit ERROR from BOTH SPEC-DOC-004 and TREE-6, never a silent
# early return. The stale "already reported by check 9" comment was wrong:
# check 9 (SPEC-DOC-009) validates only the RELEASE directory
# (releases/<release>/), never the SEGMENT subdirectory
# (releases/<release>/<segment>/) — so a live segment pointer at a missing
# segment dir was invisible to every downstream check.
# ---------------------------------------------------------------------------


def test_missing_segment_directory_is_an_explicit_error_not_a_silent_skip(
    tmp_path: Path,
) -> None:
    """AB.1: an ACTIVE.md whose segment: names a non-existent directory produces an
    explicit ERROR (from BOTH SPEC-DOC-004 and TREE-6) naming the missing segment
    directory — never a silent pass. Pre-fix, this fixture produced ZERO findings
    from either check."""
    specs = _make_clean_specs_tree(tmp_path, "v0.1.6")
    _segment_active(specs, "v0.1.6", "alpha-1")
    # The segment directory existed after _segment_active; now remove it entirely —
    # the EXACT repro: a live segment pointer at a directory that does not exist.
    import shutil as _shutil

    _shutil.rmtree(specs / "releases" / "v0.1.6" / "alpha-1")

    issues = SpecsDoctor(specs).check()

    doc004 = [i for i in issues if i.code == "SPEC-DOC-004"]
    tree6 = [i for i in issues if i.code == "TREE-6"]
    assert doc004, "SPEC-DOC-004 must report the missing segment directory, never stay silent"
    assert tree6, "TREE-6 must report the missing segment directory, never stay silent"
    missing_segment_dir = str(specs / "releases" / "v0.1.6" / "alpha-1")
    assert any(
        missing_segment_dir in i.description or missing_segment_dir in (i.path or "")
        for i in doc004
    )
    assert any(
        missing_segment_dir in i.description or missing_segment_dir in (i.path or "") for i in tree6
    )


def test_healthy_segmented_release_is_unaffected_by_the_missing_segment_check(
    tmp_path: Path,
) -> None:
    """AB.2: a segmented release WITH its directory keeps validating exactly as
    today — no behaviour change on the healthy path."""
    specs = _make_clean_specs_tree(tmp_path, "v0.1.6")
    _segment_active(specs, "v0.1.6", "alpha-1")

    issues = SpecsDoctor(specs).check()

    assert "SPEC-DOC-004" not in _codes(issues)
    assert "TREE-6" not in _codes(issues)


def test_flat_release_is_unaffected_by_the_missing_segment_check(tmp_path: Path) -> None:
    """AB.3: a flat release (segment: none / no segment line) is unaffected — the
    missing-segment-directory check only ever activates when ACTIVE.md actually
    carries a live segment: value."""
    specs = _make_clean_specs_tree(tmp_path, "v0.1.6")

    issues = SpecsDoctor(specs).check()

    assert "SPEC-DOC-004" not in _codes(issues)
    assert "TREE-6" not in _codes(issues)


def test_stale_check_9_comment_no_longer_claims_coverage_it_does_not_provide() -> None:
    """AB.4: the stale 'already reported by check 9' comment (SPEC-DOC-009 only
    validates the RELEASE directory, never the segment subdirectory) is corrected
    or deleted from both source files."""
    import inspect

    from dadaia_workspace.features.specs import doctor_release, doctor_structural

    release_src = inspect.getsource(doctor_release)
    structural_src = inspect.getsource(doctor_structural)
    assert "already reported by check 9" not in release_src
    assert "already reported by SPEC-DOC-009" not in structural_src


# ---------------------------------------------------------------------------
# CAT-1: catalog.json <-> feature atom sync — merged sad+silent matrix
# ---------------------------------------------------------------------------


def test_cat1_sync_matrix(tmp_path: Path) -> None:
    # absent catalog + feature atoms present -> one warning.
    specs_a = _make_clean_specs_tree(tmp_path)
    product_dir_a = specs_a / "memory" / "product"
    _write_feature_md(product_dir_a, "feature-b")
    _write_feature_md(product_dir_a, "feature-c")
    assert not (product_dir_a / "catalog.json").exists()
    cat1_a = [i for i in SpecsDoctor(specs_a).check() if i.code == "CAT-1"]
    assert cat1_a and cat1_a[0].severity == Severity.WARNING
    assert len(cat1_a) == 1

    # absent catalog, NO feature atoms (only index.md) -> silent.
    specs_b = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-b"))
    product_dir_b = specs_b / "memory" / "product"
    (product_dir_b / "feature-a.md").unlink()
    cat1_b = [i for i in SpecsDoctor(specs_b).check() if i.code == "CAT-1"]
    assert cat1_b == []

    # in-sync catalog -> silent.
    specs_c = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-c"))
    product_dir_c = specs_c / "memory" / "product"
    _make_catalog_json(product_dir_c, ["feature-a"])
    cat1_c = [i for i in SpecsDoctor(specs_c).check() if i.code == "CAT-1"]
    assert cat1_c == []

    # stale slug -> warning names the slug.
    specs_d = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-d"))
    product_dir_d = specs_d / "memory" / "product"
    _make_catalog_json(product_dir_d, ["feature-a", "stale-feature"])
    cat1_d = [i for i in SpecsDoctor(specs_d).check() if i.code == "CAT-1"]
    assert cat1_d
    assert "stale-feature" in " ".join(i.description for i in cat1_d)
    assert all(i.severity == Severity.WARNING for i in cat1_d)

    # extra .md not in catalog -> warning names the slug.
    specs_e = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-e"))
    product_dir_e = specs_e / "memory" / "product"
    _write_feature_md(product_dir_e, "new-feature")
    _make_catalog_json(product_dir_e, ["feature-a"])
    cat1_e = [i for i in SpecsDoctor(specs_e).check() if i.code == "CAT-1"]
    assert cat1_e
    assert "new-feature" in " ".join(i.description for i in cat1_e)

    # both stale and extra -> at least 2 separate warnings.
    specs_f = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-f"))
    product_dir_f = specs_f / "memory" / "product"
    _write_feature_md(product_dir_f, "new-feature")
    _make_catalog_json(product_dir_f, ["stale-slug"])
    cat1_f = [i for i in SpecsDoctor(specs_f).check() if i.code == "CAT-1"]
    assert len(cat1_f) >= 2

    # subdir atom in sync -> silent (rglob fix, T-021-01).
    specs_g = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-g"))
    product_dir_g = specs_g / "memory" / "product"
    subdir_g = product_dir_g / "philosophy"
    subdir_g.mkdir(parents=True, exist_ok=True)
    (subdir_g / "product-vision.md").write_text(
        "---\nslug: product-vision\ntitle: Product Vision\ncategory: product\n"
        "tldr: 'Vision.'\nsummary: 'Vision summary.'\ntags: []\nagent_tier: self-pull\n"
        "token_estimate: 100\nlast_updated: '2026-06-07'\nrelease_origin: test-release\n---\n\n"
        "## Vision\n\nThe vision.\n",
        encoding="utf-8",
    )
    _make_catalog_json(product_dir_g, ["feature-a", "product-vision"])
    cat1_g = [i for i in SpecsDoctor(specs_g).check() if i.code == "CAT-1"]
    assert cat1_g == []
