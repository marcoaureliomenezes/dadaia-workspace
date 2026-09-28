"""Unit tests for SpecsDoctor structural checks and tree invariants.

CRITICAL doctor: every invariant code keeps exactly one sad + one silent row here.
The two negative anchors (clean-tree-no-errors, fresh-scaffold-passes-all-TREE) are kept
as named tests — they are the only assertions that the WHOLE checker set stays silent on
a genuinely valid tree, a property no single-code row can prove.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.workspace_layout import render_registry_tables
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
tldr: 'Product catalog entry point.'
summary: 'Product catalog entry point.'
tags: []
agent_tier: self-pull
token_estimate: 20
---

## Feature catalog

Feature atoms.
"""

MINIMAL_MEMORY_PRODUCT_FEATURE_MD = """\
---
slug: feature-a
title: Feature A
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
tldr: 'System architecture layers.'
summary: 'System architecture layers and dependency contracts.'
tags: []
agent_tier: self-pull
token_estimate: 20
---

## Visão geral

Layers.
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
        "defined": None,
        "implemented": None,
        "shipped": None,
        "log": [],
    }
    (rdir / "_RELEASE.json").write_text(_json.dumps(state) + "\n", encoding="utf-8")


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
    (specs / "memory" / "QUALITY.md").write_text(
        "---\nslug: quality-assurance\ntitle: Quality Assurance\n"
        "tldr: 'QA standards.'\nsummary: 'QA standards and anti-slop rules.'\n"
        "tags: []\nagent_tier: self-pull\ntoken_estimate: 20\n"
        "---\n\n## Standards\n\nQA standards.\n",
        encoding="utf-8",
    )
    _write_release_jsonl(specs, release_id, "IMPLEMENTATION")
    spec_md = (
        "# Spec\n\n**Status:** Approved\n> **Created:** 2026-04-01\n"
        "**Origin:** operator-demand\n\nContent.\n"
    )
    plan_md = "# Plan\n\n**Status:** Approved\n\nShort.\n"
    tasks_md = "# Tasks\n\n**Status:** Approved\n\n- [-] T1 something\n"
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


def test_clean_tree_has_no_errors(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    issues = SpecsDoctor(specs).check()
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == [], errors


def test_release_phase_flip_still_warns_on_draft_in_implementation(tmp_path: Path) -> None:
    """A Draft artifact is unmistakably no longer freshly-scaffolded once the release's
    phase moves to IMPLEMENTATION — SPEC-DOC-004 must still fire then (segment lane
    retired at 0.4.6, ADR 0006: the trio always sits flat at the release root)."""
    specs = _make_clean_specs_tree(tmp_path, "0.1.0")
    spec = specs / "releases" / "0.1.0" / "SPEC.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace("Approved", "Draft"), encoding="utf-8")
    _write_release_jsonl(specs, "0.1.0", "IMPLEMENTATION")

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
            "TREE-3",
            id="tree3-missing-product-index",
        ),
        pytest.param(
            "missing-architecture",
            lambda specs: (specs / "memory" / "ARCHITECTURE.md").unlink(),
            "TREE-3",
            id="tree3-missing-architecture",
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
            "non-canonical-status",
            lambda specs: (specs / "releases" / "1.2.3" / "SPEC.md").write_text(
                "# Spec\n\n**Status:** Accepted\n", encoding="utf-8"
            ),
            "SPEC-DOC-004",
            id="doc004-non-canonical-status",
        ),
        # doc006-archived-without-closure DELETED (v0.5.0 T-050-25A, A4.4): SPEC-DOC-006
        # (check_archive_closures) is deleted with CLOSURE.md itself — a checker that
        # parses a file which no longer exists is dead code behind a dead artifact.
        # Verdict: criterion (a) feature removed, dadaia_workspace/features/specs/
        # doctor_closure_audit.py (this task's commit deletes check_archive_closures).
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
            "subdir-atom-parses-cleanly",
            lambda specs: (
                (specs / "memory" / "product" / "sdd").mkdir(parents=True, exist_ok=True),
                (specs / "memory" / "product" / "sdd" / "specs-doctor.md").write_text(
                    "---\nslug: specs-doctor\ntitle: Specs Doctor\n"
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
def test_silent_matrix(tmp_path: Path, case: str, mutate, code: str) -> None:  # type: ignore[no-untyped-def]
    specs = _make_clean_specs_tree(tmp_path)
    mutate(specs)
    issues = SpecsDoctor(specs).check()
    matching = [i for i in issues if i.code == code]
    assert matching == [], f"{case}: unexpected {code}: {[m.description for m in matching]}"


# ---------------------------------------------------------------------------
# (c) TREE fix-behavior: TREE-5 drift has NO auto-fix
# ---------------------------------------------------------------------------


def test_tree5_drift_is_never_auto_repaired(tmp_path: Path) -> None:
    # TREE-3/4/5 repairs: the fix-clears PLANTS and REPORT tables of
    # tests/integration/test_doctor_fix_lines_clear_their_finding.py (sa-unfixable-doctor-
    # findings-say-doctor-fix; the per-rule copies here were deleted as duplicates).
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
    canonical = render_registry_tables((_TEMPLATES_DIR / "specs-AGENTS.md").read_text("utf-8"))
    (specs_ok / "AGENTS.md").write_text(canonical, encoding="utf-8")
    doctor_ok = SpecsDoctor(specs_ok, templates_dir=_TEMPLATES_DIR)
    root_law = str(specs_ok / "AGENTS.md")  # the scoped law files are not planted here
    tree5_ok = [i for i in doctor_ok.check() if i.code == "TREE-5" and i.path == root_law]
    assert tree5_ok == []


# ---------------------------------------------------------------------------
# (d) Boundary/cutoff rows: oversized-plan, hotfix staleness, SemVer folder naming
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("created", ["2026-06-01", "2026-04-01"])
def test_doc005_oversized_plan_warns_whatever_the_spec_creation_date(
    tmp_path: Path, created: str
) -> None:
    """0.4.7 c2: an over-long PLAN is SPLIT — judgment, with no command to hand back, so
    the finding can never be error-class (which would exit 1 with no fix). The date-based
    hard-limit cutoff that used to raise it to ERROR is gone with the constant."""
    specs = _make_clean_specs_tree(tmp_path)
    big = "# Plan\n\n**Status:** Approved\n\n" + "\n".join(f"- line {i}" for i in range(400))
    (specs / "releases" / "1.2.3" / "PLAN.md").write_text(big, encoding="utf-8")
    (specs / "releases" / "1.2.3" / "SPEC.md").write_text(
        f"# Spec\n\n**Status:** Approved\n> **Created:** {created}\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    doc5 = [i for i in issues if i.code == "SPEC-DOC-005"]
    assert doc5 and doc5[0].severity is Severity.WARNING


@pytest.mark.parametrize(
    ("release_id", "created", "expect"),
    [
        # Conforming names are silent; a `v` name is not conforming (one grammar).
        pytest.param("1.2.3", "2026-06-01", None, id="semver-name-ok"),
        pytest.param("v1.2.3", "2026-06-01", Severity.ERROR, id="v-name-errors"),
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
        f"# Spec\n\n**Status:** Approved\n> **Created:** {created}\n\nContent.\n",
        encoding="utf-8",
    )
    issues = SpecsDoctor(specs).check()
    doc27 = [i for i in issues if i.code == "SPEC-DOC-027"]
    if expect is None:
        assert doc27 == [], [i.to_dict() for i in doc27]
    else:
        assert doc27, "Expected SPEC-DOC-027 for non-conforming folder name"
        assert doc27[0].severity == expect


def test_doc016_and_doc027_remedies_name_the_mintable_bare_axis(tmp_path: Path) -> None:
    """F004 (20260830 audit, bug release-new-rejects-semver-but-doctor-requires-it):
    SPEC-DOC-016/027 used to instruct a ``v<MAJOR>.<MINOR>.<PATCH>`` rename that
    ``dadaia release new`` refuses (the v axis is retired, read-only). The remedy must
    name the bare, mintable form. Intent: regression; size: unit."""
    specs = _make_clean_specs_tree(tmp_path, release_id="not-semver")
    (specs / "releases" / "not-semver" / "SPEC.md").write_text(
        "# Spec\n\n**Status:** Approved\n> **Created:** 2026-08-01\n\nContent.\n",
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
    """F005: trio presence has ONE home, `release.py check` (the ledgers section); the
    specs section reports nothing for a missing PLAN.md and never creates it.
    Intent: contract; size: unit."""
    specs = _make_clean_specs_tree(tmp_path)
    plan = specs / "releases" / "1.2.3" / "PLAN.md"
    plan.unlink()
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    assert not [i for i in issues if "PLAN.md" in i.description], issues
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
        "# Spec\n\n**Status:** Approved\n> **Created:** 2026-08-01\n\nContent.\n",
        encoding="utf-8",
    )
    issues = SpecsDoctor(specs).check()
    doc027 = [i for i in issues if i.code == "SPEC-DOC-027"]
    assert doc027 and doc027[0].severity == Severity.ERROR
    assert "SPEC-DOC-016" not in _codes(issues)
