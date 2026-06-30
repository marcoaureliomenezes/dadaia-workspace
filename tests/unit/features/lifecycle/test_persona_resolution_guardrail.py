"""T-44-9 / AC-4 — persona-resolution anti-regression guardrail.

The guardrail enumerates the RESOLVED role of every model-driven catalog/pipeline step
(the SAME path ``pipeline._scope()`` uses — comma-split + persona loader; NOT a fragment
rglob) and FAILS if any role resolves to no persona atom or to ``project-manager``. It
passes on the current tree. TWO negative fixtures — built under tmp roots, never under
``public/`` — prove BOTH surfaces are covered: (a) a fragment-layer role with no persona
atom, (b) a catalog-layer worker step bound to project-manager / an unmapped role.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind, LifecyclePhase
from dadaia_workspace.features.lifecycle.fragments.loader import FragmentLoader
from dadaia_workspace.features.lifecycle.persona_doctor import (
    PersonaResolutionFindingKind,
    check_persona_resolution,
    check_step_roles,
    model_driven_step_roles,
)
from dadaia_workspace.features.lifecycle.pipeline import PipelineStep

_FRAGMENT_TEXT = """\
---
id: ghost.step
role: {role}
workflow: ghost
step: step
static_inputs: []
dynamic_inputs: []
output_schema: handoff-v1.1
max_context_policy: summary
---

# A model-driven step body whose role has no persona atom.
"""


# ---------------------------------------------------------------------------
# Passes on the current tree.
# ---------------------------------------------------------------------------


def test_guardrail_passes_on_current_tree() -> None:
    report = check_persona_resolution()
    assert report.ok, f"unexpected persona-resolution violations: {report.violations}"


def test_every_model_driven_step_role_is_enumerated() -> None:
    roles = model_driven_step_roles()
    # The enumeration is the catalog/pipeline surface, not a fragment rglob: it must include
    # the multi-role plan_review and the pipeline implement step, and exclude python gates.
    assert roles["release_definition.plan_review"] == "qa-engineer, software-architect"
    assert roles["pipeline.implement"] == "software-engineer"
    assert all(role != "python" for role in roles.values())


# ---------------------------------------------------------------------------
# (a) fragment-layer negative fixture — tmp fragment root, NOT public/.
# ---------------------------------------------------------------------------


def test_fragment_layer_role_with_no_persona_atom_fails(tmp_path: Path) -> None:
    frag_root = tmp_path / "lifecycle_fragments" / "ghost"
    frag_root.mkdir(parents=True)
    (frag_root / "step.md").write_text(_FRAGMENT_TEXT.format(role="ghost-role"), encoding="utf-8")
    # The offending role ORIGINATES from a fragment file's frontmatter (fragment-layer).
    fragment = FragmentLoader(root=tmp_path / "lifecycle_fragments").load_fragment("ghost.step")
    report = check_step_roles({"ghost.step": fragment.role})
    assert not report.ok
    assert any(
        v.role == "ghost-role" and v.kind is PersonaResolutionFindingKind.NO_PERSONA_ATOM
        for v in report.violations
    )


# ---------------------------------------------------------------------------
# (b) catalog-layer negative fixture — step bindings, NOT public/.
# ---------------------------------------------------------------------------


def _step(label: str, role: str) -> PipelineStep:
    return PipelineStep(
        label=label,
        role=role,
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        runtime_kind=AgentRuntimeKind.FAKE,
    )


def test_catalog_layer_pm_or_unmapped_step_fails() -> None:
    # A worker step bound DIRECTLY in the catalog to project-manager (D-1 violation) and one
    # bound to an unmapped role — both independent of any fragment file.
    steps = (_step("orchestrate", "project-manager"), _step("ghost", "not-a-real-persona"))
    step_roles = {f"catalog.{s.label}": s.role for s in steps}
    report = check_step_roles(step_roles)
    assert not report.ok
    found = {(v.role, v.kind) for v in report.violations}
    assert ("project-manager", PersonaResolutionFindingKind.PROJECT_MANAGER) in found
    assert ("not-a-real-persona", PersonaResolutionFindingKind.NO_PERSONA_ATOM) in found


def test_multi_role_with_one_pm_member_fails() -> None:
    # A comma-split role where ONE member is project-manager must be caught for that member.
    report = check_step_roles({"catalog.mixed": "qa-engineer, project-manager"})
    assert not report.ok
    assert [v.kind for v in report.violations] == [PersonaResolutionFindingKind.PROJECT_MANAGER]
