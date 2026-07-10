"""Unit tests for D-OC-1 bidirectional orchestration-registry coherence invariant.

Four cases per AC-OC-10:
  1. All references correct → D-OC-1 reports no errors.
  2. A Tier-1 workflow file is missing → forward error (Tier-1 direction).
  3. A Tier-2 playbook heading is missing from SKILL.md → forward error (Tier-2 direction).
  4. An orphan ``### Playbook — <name>`` heading exists in SKILL.md without a Tier-2
     router row → reverse error.

All fixtures use ``tmp_path`` (stdlib ``pathlib``) and inline text strings.
No new third-party dependencies; only stdlib ``re`` + ``pathlib`` + ``pytest``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue

# A minimal project-manager.md with one Tier-1 entry and two Tier-2 entries.
_PM_MD_TEMPLATE = """\
---
name: project-manager
---

# Project Manager

### Step 3 — Classify the demand (Two-Tier Router)

#### Tier-1 — Engine-backed workflows (call `dadaia orchestrate run <name> --input ...`)

| Demand pattern | Workflow name | Workflow file |
|---|---|---|
| New feature | `spec-refinement` | `public/workflows/spec-refinement.workflow.md` |
| Hotfix patch | `hotfix-release` | `public/workflows/hotfix-release.workflow.md` |

#### Tier-2 — PM Playbooks (compose inline from `project-orchestration` skill)

| Demand pattern | Playbook name |
|---|---|
| Architecture spike | `architecture-review` |
| TDD feature | `tdd-cycle` |

### Step 4 — Prepare the route
"""

# A minimal SKILL.md with playbook headings for the two Tier-2 entries.
_SKILL_MD_TEMPLATE = """\
---
name: project-orchestration
---

# project-orchestration — Agent Dispatch & Mediation

### Playbook — architecture-review

**Trigger:** ADR proposal.
**Entry:** `software-architect`.
**Input contract:** `context`, `question`.
**Steps:** 1. PM dispatches architect.
**Stop conditions:** none.
**Done when:** ADR report exists.

### Playbook — tdd-cycle

**Trigger:** TDD feature task.
**Entry:** `software-engineer-python`.
**Input contract:** `context`, `task_id`.
**Steps:** 1. Write red test.
**Stop conditions:** none.
**Done when:** `qa-engineer` green report exists.
"""


def _make_public_dir(root: Path) -> Path:
    """Create a minimal ``dadaia_workspace/public/`` tree under *root*."""
    pub = root / "dadaia_workspace" / "public"
    (pub / "agents").mkdir(parents=True)
    (pub / "skills" / "project-orchestration").mkdir(parents=True)
    (pub / "workflows").mkdir(parents=True)

    (pub / "agents" / "project-manager.md").write_text(_PM_MD_TEMPLATE, encoding="utf-8")
    (pub / "skills" / "project-orchestration" / "SKILL.md").write_text(
        _SKILL_MD_TEMPLATE, encoding="utf-8"
    )
    (pub / "workflows" / "spec-refinement.workflow.md").write_text(
        "# spec-refinement workflow\n", encoding="utf-8"
    )
    (pub / "workflows" / "hotfix-release.workflow.md").write_text(
        "# hotfix-release workflow\n", encoding="utf-8"
    )
    return pub


def _make_minimal_specs(root: Path) -> Path:
    """Create a minimal (but valid-enough) specs/ tree so that SpecsDoctor can be
    instantiated. Only D-OC-1 errors are expected in these tests; other checks are
    satisfied by the minimal tree."""
    specs = root / "specs"
    mem = specs / "memory" / "product"
    mem.mkdir(parents=True)
    (specs / "releases").mkdir(parents=True)
    (specs / "_archive" / "releases").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)
    (specs / "constitution.md").write_text("# Constitution\n", encoding="utf-8")

    def _html(title: str) -> str:
        return (
            f"<!DOCTYPE html><html><head><title>{title}</title></head>"
            f"<body><h1>{title}</h1></body></html>"
        )

    (specs / "memory" / "architecture.html").write_text(_html("Arch"), encoding="utf-8")
    (specs / "memory" / "tech-stack.html").write_text(_html("Tech"), encoding="utf-8")
    (mem / "index.html").write_text(_html("Product"), encoding="utf-8")

    release_id = "test-release"
    (specs / "releases" / release_id).mkdir(parents=True)
    (specs / "releases" / "ACTIVE.md").write_text(
        f"release: {release_id}\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    _spec_content = "# Spec\n\n**Status:** Aprovado\n**Created:** 2026-01-01\n\n"
    (specs / "releases" / release_id / "SPEC.md").write_text(_spec_content, encoding="utf-8")
    (specs / "releases" / release_id / "PLAN.md").write_text(
        "# Plan\n\n**Status:** Aprovado\n\n", encoding="utf-8"
    )
    (specs / "releases" / release_id / "TASKS.md").write_text(
        "# Tasks\n\n**Status:** Aprovado\n\n- [-] T1 something\n", encoding="utf-8"
    )
    return specs


def _doc1_errors(issues: list[SpecsDoctorIssue]) -> list[SpecsDoctorIssue]:
    return [i for i in issues if i.code == "D-OC-1" and i.severity == Severity.ERROR]


def test_doc1_all_correct_no_errors(tmp_path: Path) -> None:
    """Case 1 of AC-OC-10: all references correct → D-OC-1 emits zero errors."""
    specs = _make_minimal_specs(tmp_path)
    pub = _make_public_dir(tmp_path)

    issues = SpecsDoctor(specs, public_dir=pub).check()
    doc1 = _doc1_errors(issues)
    assert doc1 == [], f"Expected 0 D-OC-1 errors, got: {[i.description for i in doc1]}"


@pytest.mark.parametrize(
    ("mutate", "expect_substrings"),
    [
        pytest.param(
            lambda pub: (pub / "workflows" / "hotfix-release.workflow.md").unlink(),
            ("hotfix-release", "Tier-1"),
            id="missing-tier1-workflow-file-is-forward-error",
        ),
        pytest.param(
            lambda pub: (pub / "skills" / "project-orchestration" / "SKILL.md").write_text(
                (pub / "skills" / "project-orchestration" / "SKILL.md")
                .read_text(encoding="utf-8")
                .replace("### Playbook — tdd-cycle", "### Removed heading tdd-cycle"),
                encoding="utf-8",
            ),
            ("tdd-cycle", "Tier-2"),
            id="missing-playbook-heading-is-forward-error",
        ),
        pytest.param(
            lambda pub: (pub / "skills" / "project-orchestration" / "SKILL.md").write_text(
                (pub / "skills" / "project-orchestration" / "SKILL.md").read_text(encoding="utf-8")
                + (
                    "\n### Playbook — orphan-playbook\n\n"
                    "**Trigger:** test only.\n"
                    "**Entry:** `qa-engineer`.\n"
                    "**Input contract:** `context`.\n"
                    "**Steps:** 1. nothing.\n"
                    "**Stop conditions:** always.\n"
                    "**Done when:** never.\n"
                ),
                encoding="utf-8",
            ),
            ("orphan-playbook", "Tier-2 router"),
            id="orphan-playbook-heading-is-reverse-error",
        ),
    ],
)
def test_doc1_error_matrix(  # type: ignore[no-untyped-def]
    tmp_path: Path, mutate, expect_substrings: tuple[str, str]
) -> None:
    """Cases 2-4 of AC-OC-10: forward Tier-1, forward Tier-2, and reverse orphan errors."""
    specs = _make_minimal_specs(tmp_path)
    pub = _make_public_dir(tmp_path)

    mutate(pub)

    issues = SpecsDoctor(specs, public_dir=pub).check()
    doc1 = _doc1_errors(issues)
    assert doc1, "Expected at least one D-OC-1 error"
    messages = [i.description for i in doc1]
    for substring in expect_substrings:
        assert any(substring in msg for msg in messages), (
            f"Expected {substring!r} in error message, got: {messages}"
        )
