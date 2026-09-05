"""Unit tests for SpecsDoctor structural checks and tree invariants.

CRITICAL doctor: every invariant code keeps exactly one sad + one silent row here; the
doctor golden (test_doctor_golden.py) pins ordering/wording across the full family set.
The two negative anchors (clean-tree-no-errors, fresh-scaffold-passes-all-TREE) are kept
as named tests — they are the only assertions that the WHOLE checker set stays silent on
a genuinely valid tree, a property no single-code row can prove.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue
from dadaia_workspace.features.specs.memory_canon import (
    FIXED_SECTIONS,
    read_fixed_fragment,
    render_fixed_section,
)

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


def _write_release_jsonl(specs: Path, release_id: str, phase: str) -> None:
    """Write (overwrite) ``specs/releases/<release_id>/RELEASE.json`` with a minimal
    release-state-v1 document (v0.5.x, successor to the RELEASE.jsonl fold; v0.5.0
    FR4/T-050-21A) -- the fixture-side replacement for the retired ``ACTIVE.md``."""
    import json as _json

    rdir = specs / "releases" / release_id
    rdir.mkdir(parents=True, exist_ok=True)
    state: dict[str, object] = {
        "schema": "release-state-v1",
        "release": release_id,
        "phase": phase,
        "rc": None,
        "defined": None,
        "implemented": None,
        "shipped": None,
        "audited": None,
        "log": [],
    }
    (rdir / "RELEASE.json").write_text(_json.dumps(state) + "\n", encoding="utf-8")


def _make_clean_specs_tree(root: Path, release_id: str = "1.2.3") -> Path:
    """Create a minimal but valid specs/ tree using .md memory atoms."""
    specs = root / "specs"
    (specs / "memory" / "product" / "testarea").mkdir(parents=True)
    (specs / "releases" / release_id).mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)

    (specs / "constitution.md").write_text("# Constitution\n\nThe laws.\n", encoding="utf-8")
    (specs / "memory" / "product" / "index.md").write_text(
        MINIMAL_MEMORY_PRODUCT_INDEX_MD, encoding="utf-8"
    )
    # v6 canon (operator ruling 2026-08-28): memory/product/<area>/<slug>.md — the
    # 2-level nested shape, matching the real, live product catalog tree.
    (specs / "memory" / "product" / "testarea" / "feature-a.md").write_text(
        MINIMAL_MEMORY_PRODUCT_FEATURE_MD, encoding="utf-8"
    )
    (specs / "memory" / "ARCHITECTURE.md").write_text(
        MINIMAL_MEMORY_ARCHITECTURE_MD, encoding="utf-8"
    )
    (specs / "memory" / "TECHSTACK.md").write_text(MINIMAL_MEMORY_TECH_STACK_MD, encoding="utf-8")
    (specs / "memory" / "QUALITY.md").write_text(
        "---\nslug: quality-assurance\ntitle: Quality Assurance\ncategory: core\n"
        "tldr: 'QA standards.'\nsummary: 'QA standards and anti-slop rules.'\n"
        "tags: []\nagent_tier: self-pull\ntoken_estimate: 20\n"
        "---\n\n## Standards\n\nQA standards.\n",
        encoding="utf-8",
    )
    _write_release_jsonl(specs, release_id, "IMPLEMENTATION")
    spec_md = "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-04-01\n\nContent.\n"
    plan_md = "# Plan\n\n> **Status:** Aprovado\n\nShort.\n"
    tasks_md = "# Tasks\n\n> **Status:** Aprovado\n\n- [-] T1 something\n"
    (specs / "releases" / release_id / "SPEC.md").write_text(spec_md, encoding="utf-8")
    (specs / "releases" / release_id / "PLAN.md").write_text(plan_md, encoding="utf-8")
    (specs / "releases" / release_id / "TASKS.md").write_text(tasks_md, encoding="utf-8")
    for rel, section_id in FIXED_SECTIONS:
        path = specs / rel
        fragment = read_fixed_fragment(_PUBLIC_DIR, section_id)
        rendered = render_fixed_section(path.read_text(encoding="utf-8"), section_id, fragment)
        path.write_text(rendered, encoding="utf-8")
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
---

## Propósito

{slug} feature.
"""
    (product_dir / f"{slug}.md").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# The two negative anchors — kept named, they are the only proof the WHOLE
# checker set stays silent on a genuinely valid tree.
# ---------------------------------------------------------------------------


def test_clean_tree_has_no_errors(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    issues = SpecsDoctor(specs).check()
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == [], errors


def test_release_phase_flip_still_warns_on_draft_in_implementation(tmp_path: Path) -> None:
    """A Draft artifact is unmistakably no longer freshly-scaffolded once the release's
    phase moves to IMPLEMENTATION — SPEC-DOC-004 must still fire then (segment lane
    retired at 0.4.6, ADR 0006: the trio always sits flat at the release root)."""
    specs = _make_clean_specs_tree(tmp_path, "v0.1.0")
    spec = specs / "releases" / "v0.1.0" / "SPEC.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace("Aprovado", "Draft"), encoding="utf-8")
    _write_release_jsonl(specs, "v0.1.0", "IMPLEMENTATION")

    issues = SpecsDoctor(specs).check()
    assert any(i.code == "SPEC-DOC-004" for i in issues)


def test_scaffold_copytree_source_tree_carries_agents_md_per_area(tmp_path: Path) -> None:
    """The "scaffold() -> 0 TREE errors" half of this test is now
    ``test_canon_property.py`` (asserting the FULL doctor is clean, not just TREE-*
    codes). What survives here is independent: the canonical *source* scaffold tree
    (``public/scaffold/``, copied verbatim rather than rendered through ``scaffold()``)
    itself carries every area's AGENTS.md (v6 canon, T-021-16 (a); README.md
    retired)."""
    import shutil

    specs2_dir = tmp_path / "copytree" / "specs"
    shutil.copytree(str(_SCAFFOLD_DIR), str(specs2_dir))
    assert (specs2_dir / "audits").is_dir()
    assert (specs2_dir / "audits" / "AGENTS.md").exists()
    assert (specs2_dir / "memory" / "AGENTS.md").exists()
    assert (specs2_dir / "memory" / "QUALITY.md").exists()


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
            lambda specs: (specs / "memory" / "ARCHITECTURE.md").unlink(),
            "SPEC-DOC-002",
            id="doc002-missing-architecture",
        ),
        pytest.param(
            "product-feature-no-heading",
            lambda specs: (specs / "memory" / "product" / "testarea" / "feature-a.md").write_text(
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
            lambda specs: (specs / "memory" / "product" / "testarea" / "feature-a.md").write_text(
                "---\nslug: feature-a\ntitle: Feature A\n---\n\n## Propósito\n\nDoes A.\n\n"
                "## Changelog\n\nHistorical details.\n",
                encoding="utf-8",
            ),
            "SPEC-DOC-008",
            id="doc008-history-heading-changelog",
        ),
        pytest.param(
            "history-heading-history",
            lambda specs: (specs / "memory" / "product" / "testarea" / "feature-a.md").write_text(
                "---\nslug: feature-a\ntitle: Feature A\n---\n\n## Propósito\n\nDoes A.\n\n"
                "## History\n\nHistorical details.\n",
                encoding="utf-8",
            ),
            "SPEC-DOC-008",
            id="doc008-history-heading-history",
        ),
        pytest.param(
            "non-canonical-phase",
            lambda specs: _write_release_jsonl(specs, "1.2.3", "WORKING"),
            "SPEC-DOC-003",
            id="doc003-non-canonical-phase",
        ),
        pytest.param(
            "ambiguous-two-live-releases",
            lambda specs: _write_release_jsonl(specs, "r2", "IMPLEMENTATION"),
            "SPEC-DOC-003",
            id="doc003-ambiguous-two-live-releases",
        ),
        pytest.param(
            "release-jsonl-carries-no-phase-record",
            lambda specs: (specs / "releases" / "1.2.3" / "RELEASE.json").write_text(
                '{"schema":"release-state-v1","release":"1.2.3","phase":"",'
                '"rc":null,"defined":null,"implemented":null,"shipped":null,'
                '"audited":null,"log":[]}\n',
                encoding="utf-8",
            ),
            "SPEC-DOC-003",
            id="doc003-empty-phase-value",
        ),
        pytest.param(
            "missing-plan-in-active-release",
            lambda specs: (specs / "releases" / "1.2.3" / "PLAN.md").unlink(),
            "SPEC-DOC-004",
            id="doc004-missing-plan",
        ),
        pytest.param(
            "non-canonical-status",
            lambda specs: (specs / "releases" / "1.2.3" / "SPEC.md").write_text(
                "# Spec\n\n> **Status:** Accepted\n", encoding="utf-8"
            ),
            "SPEC-DOC-004",
            id="doc004-non-canonical-status",
        ),
        # doc006-archived-without-closure DELETED (v0.5.0 T-050-25A, A4.4): SPEC-DOC-006
        # (check_archive_closures) is deleted with CLOSURE.md itself — a checker that
        # parses a file which no longer exists is dead code behind a dead artifact.
        # Verdict: criterion (a) feature removed, dadaia_workspace/features/specs/
        # doctor_closure_audit.py (this task's commit deletes check_archive_closures).
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
        # doc009-release-id-without-dir RETIRED (v0.5.0 T-050-21A): SPEC-DOC-009 fired
        # when ACTIVE.md's `release:` field named a directory that did not exist.
        # `resolve_active_release`/`resolve_live_release_id` only ever return a
        # release_id they found BY LOCATING that exact directory (RELEASE.json
        # inside it) — this scenario is now structurally unreachable; the ERROR
        # branch in `check_active_md` is a defensive assertion, kept but untestable
        # through the public API.
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
                    "agent_tier: self-pull\ntoken_estimate: 100\n"
                    "---\n\n## Propósito\n\nValidates specs.\n",
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

    # TREE-4 fix creates backlog/, bugs/ (and audits/) with AGENTS.md
    # (v6 canon, T-050-05, FR1: README.md retired; a directory is kept by its
    # AGENTS.md, no separate .gitkeep placeholder).
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
        assert (d / "AGENTS.md").exists()
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

    # TREE-3: missing ARCHITECTURE.md never auto-created; missing QUALITY.md
    # trips both TREE-3 (WARNING, no autofix) and SPEC-DOC-002.
    specs3 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree3"))
    arch_md = specs3 / "memory" / "ARCHITECTURE.md"
    arch_md.unlink()
    doctor3 = SpecsDoctor(specs3, templates_dir=_TEMPLATES_DIR)
    issues3 = doctor3.check()
    tree3 = [i for i in issues3 if i.code == "TREE-3"]
    assert tree3 and not tree3[0].fixable
    fixed3 = doctor3.fix(issues3)
    assert [i for i in fixed3 if i.code == "TREE-3"] == []
    assert not arch_md.exists()

    specs3b = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-tree3-qa"))
    qa_md = specs3b / "memory" / "QUALITY.md"
    qa_md.unlink()
    issues3b = SpecsDoctor(specs3b).check()
    tree3_qa = [i for i in issues3b if i.code == "TREE-3" and "QUALITY.md" in (i.description or "")]
    assert tree3_qa and tree3_qa[0].severity == Severity.WARNING and not tree3_qa[0].fixable
    spec_doc_002_qa = [
        i for i in issues3b if i.code == "SPEC-DOC-002" and "QUALITY.md" in (i.description or "")
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

    # TREE-6 retired (0.5.3 T-053-04, F005): missing-artifact coverage lives in
    # SPEC-DOC-004 — see test_one_defect_one_code_missing_active_artifact.

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
    # Fix only the TREE-7 finding itself (fixable=False, so this is a no-op for it) —
    # the fuller issues7 set now ALSO carries a TREE-8 finding for this same legacy
    # per-bug .md file (non-canon under v6: bugs/ permits only AGENTS.md/BUGS.jsonl/
    # _archive/bugs_histo.jsonl), and TREE-8 IS fixable — invoking the full set would
    # correctly delete it under TREE-8, which is not what this assertion is about.
    doctor7.fix(tree7)
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
    (specs / "releases" / "1.2.3" / "PLAN.md").write_text(big, encoding="utf-8")
    (specs / "releases" / "1.2.3" / "SPEC.md").write_text(
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
    ("release_id", "created", "expect"),
    [
        # Conforming names are silent (the retired v axis still resolves read-only).
        pytest.param("v1.2.3", "2026-06-01", None, id="semver-name-ok"),
        # Live legacy name born BEFORE the canon cutoff: preserved, WARNING only.
        pytest.param("sdd-release-lifecycle-v1", "2026-05-01", Severity.WARNING, id="legacy-warns"),
        # Born ON the canon cutoff day: the canon applies — ERROR.
        pytest.param("bad-name", "2026-06-01", Severity.ERROR, id="on-cutoff-errors"),
        # Born after the cutoff: ERROR. No date.today() gating (F005: the mocked-clock
        # time-bomb class died with SPEC-DOC-016).
        pytest.param("my-feature-v1", "2026-06-10", Severity.ERROR, id="post-cutoff-errors"),
    ],
)
def test_doc027_release_naming_boundary(
    tmp_path: Path,
    release_id: str,
    created: str,
    expect: Severity | None,
) -> None:
    specs = _make_clean_specs_tree(tmp_path, release_id=release_id)
    (specs / "releases" / release_id / "SPEC.md").write_text(
        f"# Spec\n\n> **Status:** Aprovado\n> **Created:** {created}\n\nContent.\n",
        encoding="utf-8",
    )
    issues = SpecsDoctor(specs).check()
    doc27 = [i for i in issues if i.code == "SPEC-DOC-027"]
    if expect is None:
        assert doc27 == [], [i.to_dict() for i in doc27]
    else:
        assert doc27, "Expected SPEC-DOC-027 for non-conforming folder name"
        assert doc27[0].severity == expect


# ---------------------------------------------------------------------------
# (e) Segmented release pair (ADR-5) — 1 pair
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Segment lane retired at 0.4.6 (ADR 0006) — the AB.1-AB.3 segment-router tests
# died with the routing they pinned; AB.4 survives as a comment-honesty pin.
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
    (product_dir_b / "testarea" / "feature-a.md").unlink()
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
        "token_estimate: 100\n---\n\n"
        "## Vision\n\nThe vision.\n",
        encoding="utf-8",
    )
    _make_catalog_json(product_dir_g, ["feature-a", "product-vision"])
    cat1_g = [i for i in SpecsDoctor(specs_g).check() if i.code == "CAT-1"]
    assert cat1_g == []


def test_doc016_and_doc027_remedies_name_the_mintable_bare_axis(tmp_path: Path) -> None:
    """F004 (20260830 audit, bug release-new-rejects-semver-but-doctor-requires-it):
    SPEC-DOC-016/027 used to instruct a ``v<MAJOR>.<MINOR>.<PATCH>`` rename that
    ``dadaia release new`` refuses (the v axis is retired, read-only). The remedy must
    name the bare, mintable form. Intent: regression; size: unit."""
    specs = _make_clean_specs_tree(tmp_path, release_id="not-semver")
    (specs / "releases" / "not-semver" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-08-01\n\nContent.\n",
        encoding="utf-8",
    )
    issues = SpecsDoctor(specs).check()
    naming = [i for i in issues if i.code in ("SPEC-DOC-016", "SPEC-DOC-027")]
    assert naming, "Expected naming issues for a non-SemVer release dir"
    for issue in naming:
        assert "v<MAJOR" not in issue.description, issue.description
        assert "^v\\d" not in issue.description, issue.description
    assert any("<MAJOR>.<MINOR>.<PATCH>" in i.description for i in naming)


def test_one_defect_one_code_missing_active_artifact(tmp_path: Path) -> None:
    """F005 (20260830 audit): TREE-6 and SPEC-DOC-004 were ONE rule kept as two
    implementations (the segment-router-silent-skip bug had to be fixed twice, one
    ~20-line block per file). One defect now yields ONE code: SPEC-DOC-004.
    Intent: contract; size: unit."""
    specs = _make_clean_specs_tree(tmp_path)
    plan = specs / "releases" / "1.2.3" / "PLAN.md"
    plan.unlink()
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    doc004 = [i for i in issues if i.code == "SPEC-DOC-004" and "PLAN.md" in i.description]
    assert doc004 and doc004[0].severity == Severity.ERROR
    assert "TREE-6" not in _codes(issues)
    doctor.fix(issues)
    assert not plan.exists(), "a missing SDD artifact must never be auto-created"


def test_one_defect_one_code_nonconforming_release_name(tmp_path: Path) -> None:
    """F005: SPEC-DOC-016 and SPEC-DOC-027 were one naming rule as two implementations
    that stayed coherent only by docstring promise (bug
    doctor-016-errors-archived-legacy-release-027-tolerates). One defect, ONE code:
    SPEC-DOC-027 — and no ``date.today()`` gating (the mocked-clock time-bomb class).
    Intent: contract; size: unit."""
    specs = _make_clean_specs_tree(tmp_path, release_id="badname-release")
    (specs / "releases" / "badname-release" / "SPEC.md").write_text(
        "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-08-01\n\nContent.\n",
        encoding="utf-8",
    )
    issues = SpecsDoctor(specs).check()
    doc027 = [i for i in issues if i.code == "SPEC-DOC-027"]
    assert doc027 and doc027[0].severity == Severity.ERROR
    assert "SPEC-DOC-016" not in _codes(issues)
