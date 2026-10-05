"""SpecsDoctor structural checks: one row per code (fires or silent).

A release dir's name is TREE-8's (sa-release-dir-placement-judged-by-tree8-and-spec-doc-027)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.core.workspace_layout import render_registry_tables
from dadaia_workspace.features.specs import SpecsDoctor
from dadaia_workspace.features.specs.doctor_types import finding_path
from dadaia_workspace.features.specs.memory_canon import (
    FIXED_SECTIONS,
    read_fixed_fragment,
    render_fixed_section,
)

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
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
    from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

    monkeypatch.setattr(MemoryValidator, "check_lint1_memory_atoms", lambda self: [])


def _write_release_jsonl(specs: Path, release_id: str, phase: str) -> None:
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
    specs = root / "specs"
    (specs / "memory" / "product" / "testarea").mkdir(parents=True)
    (specs / "releases" / release_id / "rc-1").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)

    (specs / "constitution.md").write_text("# Constitution\n\nThe laws.\n", encoding="utf-8")
    (specs / "memory" / "product" / "index.md").write_text(
        MINIMAL_MEMORY_PRODUCT_INDEX_MD, encoding="utf-8"
    )
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
    (specs / "releases" / release_id / "rc-1" / "SPEC.md").write_text(spec_md, encoding="utf-8")
    (specs / "releases" / release_id / "rc-1" / "PLAN.md").write_text(plan_md, encoding="utf-8")
    (specs / "releases" / release_id / "rc-1" / "TASKS.md").write_text(tasks_md, encoding="utf-8")
    for rel, section_id in FIXED_SECTIONS:
        path = specs / rel
        fragment = read_fixed_fragment(_PUBLIC_DIR, section_id)
        rendered = render_fixed_section(path.read_text(encoding="utf-8"), section_id, fragment)
        path.write_text(rendered, encoding="utf-8")
    return specs


def _codes(issues: list[SectionFinding]) -> set[str]:
    return {i.code for i in issues}


def _by_code(issues: list[SectionFinding], code: str) -> list[SectionFinding]:
    return [i for i in issues if i.code == code]


def _write_tasks(specs: Path, release_id: str, body: str) -> None:
    (specs / "releases" / release_id / "rc-1" / "TASKS.md").write_text(
        f"# Tasks\n\n**Status:** Approved\n\n{body}\n", encoding="utf-8"
    )


def test_clean_tree_has_no_errors(tmp_path: Path) -> None:
    errors = [i for i in SpecsDoctor(_make_clean_specs_tree(tmp_path)).check() if i.error]
    assert errors == [], errors


def _replace(rel: str, old: str, new: str) -> Callable[[Path], None]:
    def mutate(specs: Path) -> None:
        path = specs / rel
        path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    return mutate


def _write(rel: str, text: str) -> Callable[[Path], None]:
    def mutate(specs: Path) -> None:
        (specs / rel).parent.mkdir(parents=True, exist_ok=True)
        (specs / rel).write_text(text, encoding="utf-8")

    return mutate


def _unlink(rel: str) -> Callable[[Path], None]:
    return lambda specs: (specs / rel).unlink()


_ATOM = (
    "---\nslug: specs-doctor\ntitle: Specs Doctor\ntldr: 'Doctor checks.'\n"
    "summary: 'Doctor structural checks.'\ntags: []\nagent_tier: self-pull\n"
    "token_estimate: 100\n---\n\n## Propósito\n\nValidates specs.\n"
)


@pytest.mark.parametrize(
    ("mutate", "code", "fires"),
    [
        pytest.param(
            _unlink("constitution.md"), "SPEC-DOC-001", True, id="doc001-missing-constitution"
        ),
        pytest.param(
            _unlink("memory/product/index.md"), "TREE-3", True, id="tree3-missing-product-index"
        ),
        pytest.param(
            _unlink("memory/ARCHITECTURE.md"), "TREE-3", True, id="tree3-missing-architecture"
        ),
        pytest.param(
            _write(
                "memory/product/testarea/feature-a.md",
                "---\nslug: feature-a\ntitle: A\n---\n\nProse.\n",
            ),
            "SPEC-DOC-002",
            True,
            id="doc002-feature-without-heading",
        ),
        pytest.param(
            _write("memory/product/sdd/specs-doctor.md", _ATOM),
            "SPEC-DOC-002",
            False,
            id="doc002-subdir-atom-ok",
        ),
        pytest.param(
            _write("releases/1.2.3/rc-1/SPEC.md", "# Spec\n\n**Status:** Accepted\n"),
            "SPEC-DOC-004",
            True,
            id="doc004-non-canonical-status",
        ),
        pytest.param(
            _replace("releases/1.2.3/rc-1/SPEC.md", "Approved", "Draft"),
            "SPEC-DOC-004",
            True,
            id="doc004-draft-in-implementation",
        ),
    ],
)
def test_code_matrix(
    tmp_path: Path, mutate: Callable[[Path], None], code: str, fires: bool
) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    mutate(specs)
    assert (code in _codes(SpecsDoctor(specs).check())) is fires


def test_the_source_scaffold_carries_the_area_law_files() -> None:
    scaffold = _PUBLIC_DIR / "scaffold"
    for rel in ("audits/AGENTS.md", "memory/AGENTS.md", "memory/QUALITY.md"):
        assert (scaffold / rel).is_file(), rel


def test_tree5_drift_is_reported_never_auto_repaired(tmp_path: Path) -> None:
    specs_drift = _make_clean_specs_tree(tmp_path / "drift")
    (specs_drift / "AGENTS.md").write_text("# AGENTS\n\nCustomised.\n", encoding="utf-8")
    tree5 = _by_code(SpecsDoctor(specs_drift, templates_dir=_TEMPLATES_DIR).check(), "TREE-5")
    assert tree5 and not tree5[0].fixable and "drift" in tree5[0].message.lower()

    specs_ok = _make_clean_specs_tree(tmp_path / "ok")
    canonical = render_registry_tables((_TEMPLATES_DIR / "specs-AGENTS.md").read_text("utf-8"))
    (specs_ok / "AGENTS.md").write_text(canonical, encoding="utf-8")
    root_law = str(specs_ok / "AGENTS.md")
    issues = SpecsDoctor(specs_ok, templates_dir=_TEMPLATES_DIR).check()
    assert [i for i in _by_code(issues, "TREE-5") if finding_path(i) == root_law] == []


def test_one_defect_one_code_missing_active_artifact(tmp_path: Path) -> None:
    """F005: trio presence has ONE home, `release.py check`; the specs section reports
    nothing for a missing PLAN.md and fix never creates it."""
    specs = _make_clean_specs_tree(tmp_path)
    plan = specs / "releases" / "1.2.3" / "rc-1" / "PLAN.md"
    plan.unlink()
    doctor = SpecsDoctor(specs, templates_dir=_TEMPLATES_DIR)
    issues = doctor.check()
    assert not [i for i in issues if "PLAN.md" in i.message], issues
    doctor.fix(issues)
    assert not plan.exists()
