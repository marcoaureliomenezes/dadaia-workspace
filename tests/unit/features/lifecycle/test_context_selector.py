"""Unit tests for the dynamic context selector (WS-4 / T-24-08).

Each implemented selector is exercised against a real-but-minimal fixture specs tree,
each max-context policy is asserted to bound what is returned, and the run-record audit
seam is verified to list the injected refs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.agent_runner import record_injected_context
from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    MaxContextPolicy,
    SpecContext,
    UnknownDynamicInputError,
    UnknownPolicyError,
    known_dynamic_inputs,
)

# ---------------------------------------------------------------------------
# Fixture specs tree
# ---------------------------------------------------------------------------

_ATOM = """\
---
slug: brand-identity
title: brand-identity
category: product
tldr: visual identity atom tldr
summary: the brand identity summary body
tags: [brand]
agent_tier: self-pull
token_estimate: 100
---

# brand-identity

Body paragraph that is NOT in the frontmatter and must be excluded by summary policy.
"""

_OPEN_BUG = """\
---
name: open-bug-one
status: Open
severity: HIGH
reported: 2026-06-25
surface: gate
---

**Symptom:** something broke in the gate.
"""

_CLOSED_BUG = """\
---
name: closed-bug-one
status: Closed
severity: LOW
reported: 2026-06-01
resolved_in: v0.1.23
surface: panel
---

**Symptom:** resolved already.
"""

_CANDIDATE_BACKLOG = """\
# EPIC — Candidate item

**ID:** FEAT-CANDIDATE-01
**Status:** OPEN — candidate.

Body of the candidate backlog item.
"""

_DEFERRED_BACKLOG = """\
# Deferred item

**ID:** FEAT-DEFERRED-01
**Status:** deferred

Body of the deferred item.
"""

_AUDIT_INDEX = """\
# Audit index

Finding A1: structural drift in the gate.
"""

_SPEC = "# SPEC\n\n**Status:** Aprovado\n\nThe specification body.\n"
_PLAN = "# PLAN\n\n**Status:** Aprovado\n\nThe plan body.\n"
_TASKS = "# TASKS\n\n**Status:** Aprovado\n\n- T-1 do the thing.\n"

_HANDOFF_PM = {
    "schema_version": "handoff-v1.1",
    "agent": "project-manager",
    "context": "fixture-ctx",
    "produced_at": "2026-06-25T10:00:00Z",
    "scope": "release scope",
    "metrics": {},
    "artifact": {"type": "other"},
}
_HANDOFF_QA = {
    "schema_version": "handoff-v1.1",
    "agent": "qa-engineer",
    "context": "fixture-ctx",
    "produced_at": "2026-06-25T11:00:00Z",
    "scope": "spec review",
    "metrics": {},
    "artifact": {"type": "other"},
    "verdict": "APPROVED",
}


@pytest.fixture
def context(tmp_path: Path) -> SpecContext:
    repo = tmp_path / "fixture-ctx"
    specs = repo / "specs"
    release_id = "v9.9.9"

    # memory atoms + catalog
    product = specs / "memory" / "product"
    product.mkdir(parents=True)
    (product / "brand-identity.md").write_text(_ATOM, encoding="utf-8")
    catalog = {
        "generated_at": "2026-06-25T00:00:00Z",
        "context": "fixture-ctx",
        "features": [
            {"slug": "brand-identity", "title": "brand-identity", "tldr": "visual identity"}
        ],
    }
    (product / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text(
        "# Architecture\n\nLayer boundaries.\n", encoding="utf-8"
    )
    (specs / "memory" / "quality-assurance.md").write_text(
        "# QA\n\nTest strategy.\n", encoding="utf-8"
    )
    (specs / "constitution.md").write_text("# Constitution\n\nThe law.\n", encoding="utf-8")

    # bugs
    bugs = specs / "bugs"
    bugs.mkdir(parents=True)
    (bugs / "open-bug-one.md").write_text(_OPEN_BUG, encoding="utf-8")
    (bugs / "closed-bug-one.md").write_text(_CLOSED_BUG, encoding="utf-8")

    # backlog
    backlog = specs / "backlog"
    backlog.mkdir(parents=True)
    (backlog / "candidate.md").write_text(_CANDIDATE_BACKLOG, encoding="utf-8")
    (backlog / "deferred.md").write_text(_DEFERRED_BACKLOG, encoding="utf-8")

    # audits
    audit_dir = specs / "audits" / "2026-06-25T000000Z"
    audit_dir.mkdir(parents=True)
    (audit_dir / "index.md").write_text(_AUDIT_INDEX, encoding="utf-8")

    # release artifacts
    release = specs / "releases" / release_id
    release.mkdir(parents=True)
    (release / "SPEC.md").write_text(_SPEC, encoding="utf-8")
    (release / "PLAN.md").write_text(_PLAN, encoding="utf-8")
    (release / "TASKS.md").write_text(_TASKS, encoding="utf-8")

    # source + tests trees (for code/source/test map summaries)
    (repo / "dadaia_workspace").mkdir()
    (repo / "dadaia_workspace" / "module_a.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_a.py").write_text("def test_a(): ...\n", encoding="utf-8")

    # handoffs
    handoff = tmp_path / ".dadaia" / "handoff" / "fixture-ctx"
    handoff.mkdir(parents=True)
    (handoff / "2026-06-25T100000Z-project-manager-scope.handoff.json").write_text(
        json.dumps(_HANDOFF_PM), encoding="utf-8"
    )
    (handoff / "2026-06-25T110000Z-qa-engineer-spec.handoff.json").write_text(
        json.dumps(_HANDOFF_QA), encoding="utf-8"
    )

    return SpecContext(specs_dir=specs, release_id=release_id, handoff_dir=handoff)


# ---------------------------------------------------------------------------
# Policy parsing
# ---------------------------------------------------------------------------


def test_policy_parse_known() -> None:
    assert MaxContextPolicy.parse("exact-files-only") is MaxContextPolicy.EXACT_FILES_ONLY
    assert MaxContextPolicy.parse("summary") is MaxContextPolicy.SUMMARY
    assert MaxContextPolicy.parse("catalog-only") is MaxContextPolicy.CATALOG_ONLY
    assert MaxContextPolicy.parse("diff-only") is MaxContextPolicy.DIFF_ONLY
    assert MaxContextPolicy.parse("previous-handoff-only") is MaxContextPolicy.PREVIOUS_HANDOFF_ONLY


def test_policy_parse_unknown_raises() -> None:
    with pytest.raises(UnknownPolicyError):
        MaxContextPolicy.parse("everything")


def test_unknown_dynamic_input_raises(context: SpecContext) -> None:
    selector = ContextSelector(context)
    with pytest.raises(UnknownDynamicInputError):
        selector.select("not_a_real_input", MaxContextPolicy.SUMMARY)


def test_release_definition_inputs_all_registered() -> None:
    """Every dynamic input the release_definition fragments declare must resolve."""
    declared = {
        "plan_draft",
        "approved_spec",
        "architecture_summary",
        "quality_assurance_atom",
        "spec_draft",
        "code_map_summary",
        "release_scope_handoff",
        "selected_backlog_items",
        "selected_bugs",
        "selected_audit_findings",
        "relevant_product_atoms",
        "open_bugs",
        "open_audits",
        "candidate_backlog",
        "product_catalog_summary",
        "approved_plan",
        "repo_ownership_map",
        "write_set_guidance",
        "spec_review_handoffs",
        "test_catalog_summary",
        "tasks_draft",
        "source_map_summary",
    }
    known = set(known_dynamic_inputs())
    assert declared <= known


# ---------------------------------------------------------------------------
# Max-context policies bound what is returned
# ---------------------------------------------------------------------------


def test_exact_files_only_returns_full_body(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("relevant_product_atoms", MaxContextPolicy.EXACT_FILES_ONLY)
    assert "Body paragraph that is NOT in the frontmatter" in result.content


def test_summary_excludes_body(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("relevant_product_atoms", MaxContextPolicy.SUMMARY)
    assert "the brand identity summary body" in result.content
    assert "Body paragraph that is NOT in the frontmatter" not in result.content


def test_catalog_only_is_short(context: SpecContext) -> None:
    selector = ContextSelector(context)
    full = selector.select("relevant_product_atoms", MaxContextPolicy.EXACT_FILES_ONLY)
    cat = selector.select("relevant_product_atoms", MaxContextPolicy.CATALOG_ONLY)
    assert len(cat.content) < len(full.content)
    assert "Body paragraph" not in cat.content


def test_diff_only_policy_on_git_diff_selector(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("git_diff", MaxContextPolicy.EXACT_FILES_ONLY)
    # git_diff always returns a diff-only payload regardless of requested policy.
    assert result.policy is MaxContextPolicy.DIFF_ONLY


def test_previous_handoff_only_returns_single_latest(context: SpecContext) -> None:
    selector = ContextSelector(context)
    full = selector.select("spec_review_handoffs", MaxContextPolicy.EXACT_FILES_ONLY)
    last = selector.select("spec_review_handoffs", MaxContextPolicy.PREVIOUS_HANDOFF_ONLY)
    assert len(full.refs) == 2
    assert len(last.refs) == 1
    assert last.refs[0].endswith("qa-engineer-spec.handoff.json")


# ---------------------------------------------------------------------------
# Per-selector behavior
# ---------------------------------------------------------------------------


def test_memory_atoms_selector(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("memory_atoms", MaxContextPolicy.EXACT_FILES_ONLY)
    assert any("brand-identity.md" in ref for ref in result.refs)


def test_product_catalog_selector(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("product_catalog", MaxContextPolicy.CATALOG_ONLY)
    assert "brand-identity" in result.content
    assert result.refs and result.refs[0].endswith("catalog.json")


def test_open_bugs_excludes_closed(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("open_bugs", MaxContextPolicy.SUMMARY)
    assert any("open-bug-one.md" in ref for ref in result.refs)
    assert all("closed-bug-one.md" not in ref for ref in result.refs)


def test_selected_bugs_includes_all(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("selected_bugs", MaxContextPolicy.SUMMARY)
    assert len(result.refs) == 2


def test_candidate_backlog_excludes_deferred(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("candidate_backlog", MaxContextPolicy.SUMMARY)
    assert any("candidate.md" in ref for ref in result.refs)
    assert all("deferred.md" not in ref for ref in result.refs)


def test_selected_backlog_includes_all(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("selected_backlog_items", MaxContextPolicy.SUMMARY)
    assert len(result.refs) == 2


def test_open_audits_selector(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("open_audits", MaxContextPolicy.EXACT_FILES_ONLY)
    assert any("index.md" in ref for ref in result.refs)
    assert "Finding A1" in result.content


def test_selected_audit_findings_selector(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("selected_audit_findings", MaxContextPolicy.EXACT_FILES_ONLY)
    assert "Finding A1" in result.content


def test_release_artifact_selectors(context: SpecContext) -> None:
    selector = ContextSelector(context)
    spec = selector.select("approved_spec", MaxContextPolicy.EXACT_FILES_ONLY)
    plan = selector.select("approved_plan", MaxContextPolicy.EXACT_FILES_ONLY)
    tasks = selector.select("tasks_draft", MaxContextPolicy.EXACT_FILES_ONLY)
    assert "The specification body." in spec.content
    assert spec.refs[0].endswith("SPEC.md")
    assert "The plan body." in plan.content
    assert "T-1 do the thing." in tasks.content


def test_release_artifact_missing_returns_empty(tmp_path: Path) -> None:
    specs = tmp_path / "ctx" / "specs"
    (specs / "releases" / "v1.0.0").mkdir(parents=True)
    selector = ContextSelector(SpecContext(specs_dir=specs, release_id="v1.0.0"))
    result = selector.select("approved_spec", MaxContextPolicy.EXACT_FILES_ONLY)
    assert result.content == ""
    assert result.refs == ()


def test_constitution_and_architecture_selectors(context: SpecContext) -> None:
    selector = ContextSelector(context)
    const = selector.select("constitution.md", MaxContextPolicy.EXACT_FILES_ONLY)
    arch = selector.select("memory/architecture.md", MaxContextPolicy.SUMMARY)
    assert "The law." in const.content
    assert arch.refs[0].endswith("architecture.md")


def test_release_scope_handoff_filters_to_pm(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("release_scope_handoff", MaxContextPolicy.PREVIOUS_HANDOFF_ONLY)
    assert len(result.refs) == 1
    assert "project-manager" in result.refs[0]


def test_summary_map_selectors(context: SpecContext) -> None:
    selector = ContextSelector(context)
    code = selector.select("code_map_summary", MaxContextPolicy.SUMMARY)
    src = selector.select("source_map_summary", MaxContextPolicy.SUMMARY)
    tests = selector.select("test_catalog_summary", MaxContextPolicy.SUMMARY)
    assert "module_a.py" in code.content
    assert "module_a.py" in src.content
    assert "test_a.py" in tests.content


def test_architecture_summary_input(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("architecture_summary", MaxContextPolicy.SUMMARY)
    assert result.refs[0].endswith("architecture.md")


def test_product_catalog_summary_input(context: SpecContext) -> None:
    selector = ContextSelector(context)
    result = selector.select("product_catalog_summary", MaxContextPolicy.CATALOG_ONLY)
    assert "brand-identity" in result.content


def test_quality_assurance_and_test_output_selectors(context: SpecContext) -> None:
    selector = ContextSelector(context)
    qa = selector.select("quality_assurance_atom", MaxContextPolicy.EXACT_FILES_ONLY)
    test_out = selector.select("test_output", MaxContextPolicy.SUMMARY)
    src_sum = selector.select("source_summary", MaxContextPolicy.SUMMARY)
    assert "Test strategy." in qa.content
    assert "module_a.py" in src_sum.content
    assert test_out.name == "test_output"


def test_repo_ownership_and_write_set_selectors(context: SpecContext) -> None:
    selector = ContextSelector(context)
    ownership = selector.select("repo_ownership_map", MaxContextPolicy.SUMMARY)
    write_set = selector.select("write_set_guidance", MaxContextPolicy.SUMMARY)
    assert ownership.refs[0].endswith("architecture.md")
    assert write_set.refs[0].endswith("constitution.md")


# ---------------------------------------------------------------------------
# Batch select + audit
# ---------------------------------------------------------------------------


def test_select_all_collects_refs_and_fragment_ids(context: SpecContext) -> None:
    selector = ContextSelector(context)
    audit = selector.select_all(
        step="spec_create",
        names=("approved_spec", "memory/architecture.md", "relevant_product_atoms"),
        policy="exact-files-only",
        fragment_ids=("release_definition.spec_create",),
    )
    assert audit.step == "spec_create"
    assert audit.fragment_ids == ("release_definition.spec_create",)
    assert any(ref.endswith("SPEC.md") for ref in audit.refs)
    assert any(ref.endswith("architecture.md") for ref in audit.refs)
    assert any("brand-identity.md" in ref for ref in audit.refs)


def test_select_all_dedupes_refs(context: SpecContext) -> None:
    selector = ContextSelector(context)
    audit = selector.select_all(
        step="dup",
        names=("approved_spec", "spec_draft"),  # both resolve SPEC.md
        policy="exact-files-only",
    )
    spec_refs = [ref for ref in audit.refs if ref.endswith("SPEC.md")]
    assert len(spec_refs) == 1


# ---------------------------------------------------------------------------
# Run-record audit seam
# ---------------------------------------------------------------------------


def _run() -> LifecycleRun:
    return LifecycleRun(
        run_id="run-1",
        context="fixture-ctx",
        release_id="v9.9.9",
        command="pipeline",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.RUNNING,
        current_step="spec_create",
    )


def test_run_record_lists_injected_refs(context: SpecContext) -> None:
    selector = ContextSelector(context)
    audit = selector.select_all(
        step="spec_create",
        names=("approved_spec", "memory/architecture.md"),
        policy="exact-files-only",
        fragment_ids=("release_definition.spec_create",),
    )
    run = record_injected_context(_run(), audit)

    assert len(run.injected_context) == 1
    entry = run.injected_context[0]
    assert entry.step == "spec_create"
    assert entry.fragment_ids == ("release_definition.spec_create",)
    assert any(ref.endswith("SPEC.md") for ref in entry.refs)
    assert any(ref.endswith("architecture.md") for ref in entry.refs)
    assert "exact-files-only" in entry.policies


def test_run_record_audit_round_trips(context: SpecContext) -> None:
    selector = ContextSelector(context)
    audit = selector.select_all(
        step="release_scope",
        names=("open_bugs", "candidate_backlog"),
        policy="summary",
        fragment_ids=("release_definition.release_scope",),
    )
    run = record_injected_context(_run(), audit)
    restored = LifecycleRun.from_dict(run.to_dict())
    assert restored.injected_context == run.injected_context


def test_run_record_accumulates_multiple_steps(context: SpecContext) -> None:
    selector = ContextSelector(context)
    run = _run()
    run = record_injected_context(
        run, selector.select_all("step_a", ("approved_spec",), "exact-files-only")
    )
    run = record_injected_context(
        run, selector.select_all("step_b", ("approved_plan",), "exact-files-only")
    )
    assert [entry.step for entry in run.injected_context] == ["step_a", "step_b"]
