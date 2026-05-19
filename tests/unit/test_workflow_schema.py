"""Schema validation for MarkdownWorkflowStore."""

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import (
    WorkflowCycleError,
    WorkflowNotFoundError,
    WorkflowSchemaError,
)
from dadaia_workspace.infrastructure.markdown_workflow_store import MarkdownWorkflowStore

_VALID = """---
name: demo
description: Demo workflow.
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
stages:
  - id: discover
    agent: product-engineer
    expected_output:
      path: out/{run_id}/discover.md
  - id: review
    agent: software-architect
    needs: [discover]
    expected_output:
      path: out/{run_id}/review.md
---
# demo
"""


def _write(tmp_path: Path, filename: str, content: str) -> Path:
    path = tmp_path / filename
    path.write_text(content)
    return path


def test_loads_valid_workflow(tmp_path: Path) -> None:
    _write(tmp_path, "demo.workflow.md", _VALID)
    store = MarkdownWorkflowStore(
        tmp_path, agent_catalog=["product-engineer", "software-architect"]
    )
    workflows = store.list()
    assert len(workflows) == 1
    assert workflows[0].name == "demo"
    assert workflows[0].stages[1].needs == ("discover",)


def test_missing_name_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "demo.workflow.md", _VALID.replace("name: demo", 'name: ""'))
    store = MarkdownWorkflowStore(tmp_path)
    with pytest.raises(WorkflowSchemaError):
        store.list()


def test_filename_must_match_name(tmp_path: Path) -> None:
    _write(tmp_path, "other.workflow.md", _VALID)
    store = MarkdownWorkflowStore(tmp_path)
    with pytest.raises(WorkflowSchemaError):
        store.list()


def test_unknown_agent_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "demo.workflow.md", _VALID)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=["product-engineer"])
    with pytest.raises(WorkflowSchemaError):
        store.list()


def test_cycle_rejected(tmp_path: Path) -> None:
    cyclic = _VALID.replace(
        "  - id: discover\n    agent: product-engineer\n    expected_output:\n      path: out/{run_id}/discover.md",
        "  - id: discover\n    agent: product-engineer\n    needs: [review]\n    expected_output:\n      path: out/{run_id}/discover.md",
    )
    _write(tmp_path, "demo.workflow.md", cyclic)
    store = MarkdownWorkflowStore(
        tmp_path, agent_catalog=["product-engineer", "software-architect"]
    )
    with pytest.raises(WorkflowCycleError):
        store.list()


def test_parallel_group_member_with_internal_dep_rejected(tmp_path: Path) -> None:
    text = """---
name: pg
description: ""
version: 0.1.0
schema_version: "1"
stages:
  - id: a
    agent: product-engineer
    parallel_group: g
    expected_output: {path: out/a.md}
  - id: b
    agent: product-engineer
    parallel_group: g
    needs: [a]
    expected_output: {path: out/b.md}
---
"""
    _write(tmp_path, "pg.workflow.md", text)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=["product-engineer"])
    with pytest.raises(WorkflowSchemaError):
        store.list()


def test_get_unknown_workflow_raises(tmp_path: Path) -> None:
    _write(tmp_path, "demo.workflow.md", _VALID)
    store = MarkdownWorkflowStore(
        tmp_path, agent_catalog=["product-engineer", "software-architect"]
    )
    with pytest.raises(WorkflowNotFoundError):
        store.get("ghost")


_VALID_PLACEHOLDER = """---
name: param
description: Parameterized implementer.
version: 0.1.0
schema_version: "1"
inputs:
  implementer_agent:
    type: string
    required: false
    default: software-engineer
    description: Which engineer runs the stage.
stages:
  - id: discover
    agent: product-engineer
    expected_output:
      path: out/{run_id}/discover.md
  - id: implement
    agent: "{{implementer_agent}}"
    needs: [discover]
    expected_output:
      path: out/{run_id}/implement.md
---
# param
"""


def test_agent_placeholder_resolved_from_inputs(tmp_path: Path) -> None:
    """Stage 'agent' may use {{<input_name>}} when the input is declared."""
    _write(tmp_path, "param.workflow.md", _VALID_PLACEHOLDER)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=["product-engineer", "software-engineer"])
    workflows = store.list()
    assert len(workflows) == 1
    impl_stage = next(s for s in workflows[0].stages if s.id == "implement")
    # The placeholder is stored verbatim — the orchestrator resolves it at run time.
    assert impl_stage.agent == "{{implementer_agent}}"


def test_agent_placeholder_referencing_unknown_input_rejected(tmp_path: Path) -> None:
    """Placeholder pointing at a name not declared under 'inputs' must fail validation."""
    broken = _VALID_PLACEHOLDER.replace("{{implementer_agent}}", "{{unknown_param}}")
    _write(tmp_path, "param.workflow.md", broken)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=["product-engineer", "software-engineer"])
    with pytest.raises(WorkflowSchemaError):
        store.list()


# ---------------------------------------------------------------------------
# AGT-33 — 3 new workflow YAMLs (audit-cycle, code-review-fan-out, design-validation)
# ---------------------------------------------------------------------------

# Minimal schema-valid representations of the 3 new workflows.
# These strip the extended `inputs` / `gate` / `inputs` stage sub-keys that
# the MarkdownWorkflowStore schema does not require, while preserving the
# shape that is validated (name, stages, agent, needs, parallel_group).

_AUDIT_CYCLE_YAML = """---
name: audit-cycle
description: "4-way parallel audit."
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
stages:
  - id: audit_intake
    agent: project-auditor
    expected_output:
      path: out/{run_id}/intake.html
  - id: code_review
    agent: code-reviewer
    needs: [audit_intake]
    parallel_group: audit
    expected_output:
      path: out/{run_id}/code.html
  - id: security_review
    agent: security-reviewer
    needs: [audit_intake]
    parallel_group: audit
    expected_output:
      path: out/{run_id}/security.html
  - id: research_review
    agent: researcher
    needs: [audit_intake]
    parallel_group: audit
    expected_output:
      path: out/{run_id}/research.html
  - id: qa_review
    agent: qa-engineer
    needs: [audit_intake]
    parallel_group: audit
    expected_output:
      path: out/{run_id}/qa.html
  - id: synthesis
    agent: project-auditor
    needs: [code_review, security_review, research_review, qa_review]
    expected_output:
      path: out/{run_id}/synthesis.html
---
# audit-cycle
"""

_CODE_REVIEW_FAN_OUT_YAML = """---
name: code-review-fan-out
description: "Per-PR parallel review."
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
  pr_ref:
    type: string
    required: true
stages:
  - id: code_review
    agent: code-reviewer
    parallel_group: review
    expected_output:
      path: out/{run_id}/code.html
  - id: security_review
    agent: security-reviewer
    parallel_group: review
    expected_output:
      path: out/{run_id}/security.html
  - id: design_review
    agent: design-specialist
    parallel_group: review
    expected_output:
      path: out/{run_id}/design.html
  - id: consolidation
    agent: project-manager
    needs: [code_review, security_review, design_review]
    expected_output:
      path: out/{run_id}/verdict.html
---
# code-review-fan-out
"""

_DESIGN_VALIDATION_YAML = """---
name: design-validation
description: "Sequential design validation."
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
stages:
  - id: capture_screens
    agent: qa-engineer
    expected_output:
      path: out/{run_id}/screens.html
  - id: ux_review
    agent: design-specialist
    needs: [capture_screens]
    expected_output:
      path: out/{run_id}/ux.html
---
# design-validation
"""

_NEW_WORKFLOW_CATALOG = [
    "project-auditor",
    "code-reviewer",
    "security-reviewer",
    "researcher",
    "qa-engineer",
    "project-manager",
    "design-specialist",
]


def test_audit_cycle_schema_loads(tmp_path: Path) -> None:
    """audit-cycle YAML is parseable by MarkdownWorkflowStore."""
    _write(tmp_path, "audit-cycle.workflow.md", _AUDIT_CYCLE_YAML)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=_NEW_WORKFLOW_CATALOG)
    workflows = store.list()
    assert len(workflows) == 1
    wf = workflows[0]
    assert wf.name == "audit-cycle"
    assert len(wf.stages) == 6


def test_audit_cycle_parallel_group_present(tmp_path: Path) -> None:
    """audit-cycle: the 4 audit stages must be in parallel_group='audit'."""
    _write(tmp_path, "audit-cycle.workflow.md", _AUDIT_CYCLE_YAML)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=_NEW_WORKFLOW_CATALOG)
    workflows = store.list()
    audit_parallel = [s for s in workflows[0].stages if s.parallel_group == "audit"]
    assert len(audit_parallel) == 4, (
        f"Expected 4 stages in audit parallel group, got {len(audit_parallel)}"
    )


def test_code_review_fan_out_schema_loads(tmp_path: Path) -> None:
    """code-review-fan-out YAML is parseable by MarkdownWorkflowStore."""
    _write(tmp_path, "code-review-fan-out.workflow.md", _CODE_REVIEW_FAN_OUT_YAML)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=_NEW_WORKFLOW_CATALOG)
    workflows = store.list()
    assert len(workflows) == 1
    wf = workflows[0]
    assert wf.name == "code-review-fan-out"
    assert len(wf.stages) == 4


def test_code_review_fan_out_parallel_group_present(tmp_path: Path) -> None:
    """code-review-fan-out: 3 review stages must be in parallel_group='review'."""
    _write(tmp_path, "code-review-fan-out.workflow.md", _CODE_REVIEW_FAN_OUT_YAML)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=_NEW_WORKFLOW_CATALOG)
    workflows = store.list()
    review_parallel = [s for s in workflows[0].stages if s.parallel_group == "review"]
    assert len(review_parallel) == 3, (
        f"Expected 3 stages in review parallel group, got {len(review_parallel)}"
    )


def test_design_validation_schema_loads(tmp_path: Path) -> None:
    """design-validation YAML is parseable by MarkdownWorkflowStore."""
    _write(tmp_path, "design-validation.workflow.md", _DESIGN_VALIDATION_YAML)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=_NEW_WORKFLOW_CATALOG)
    workflows = store.list()
    assert len(workflows) == 1
    wf = workflows[0]
    assert wf.name == "design-validation"
    assert len(wf.stages) == 2


def test_design_validation_sequential_stages(tmp_path: Path) -> None:
    """design-validation: ux_review depends on capture_screens."""
    _write(tmp_path, "design-validation.workflow.md", _DESIGN_VALIDATION_YAML)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=_NEW_WORKFLOW_CATALOG)
    workflows = store.list()
    ux_review = next(s for s in workflows[0].stages if s.id == "ux_review")
    assert "capture_screens" in ux_review.needs


@pytest.mark.parametrize(
    "wf_name,wf_yaml,stage_count",
    [
        ("audit-cycle", _AUDIT_CYCLE_YAML, 6),
        ("code-review-fan-out", _CODE_REVIEW_FAN_OUT_YAML, 4),
        ("design-validation", _DESIGN_VALIDATION_YAML, 2),
    ],
)
def test_new_workflow_stage_counts(
    tmp_path: Path, wf_name: str, wf_yaml: str, stage_count: int
) -> None:
    """Each new workflow parses with the expected stage count."""
    _write(tmp_path, f"{wf_name}.workflow.md", wf_yaml)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=_NEW_WORKFLOW_CATALOG)
    workflows = store.list()
    assert len(workflows) == 1
    assert len(workflows[0].stages) == stage_count
