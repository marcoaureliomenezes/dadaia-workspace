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


_PUBLIC_ROOT = Path(__file__).parents[2] / "dadaia_workspace" / "public"
_PUBLIC_WORKFLOWS_DIR = _PUBLIC_ROOT / "workflows"
_PUBLIC_AGENTS_DIR = _PUBLIC_ROOT / "agents"

# Synthetic workflow with parallel_group stages — decoupled from canonical workflow content.
# The canonical workflows (audit-fanout, release-ship) are linear; the parallel_group
# schema feature is validated through this synthetic fixture instead.
_SYNTHETIC_PARALLEL_WORKFLOW = """\
---
name: synthetic-parallel-schema-test
description: Synthetic fixture for testing parallel_group schema validation.
version: 0.0.1
schema_version: "1"
stages:
  - id: review_a
    agent: qa-engineer
    parallel_group: review_batch
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-qa-engineer-review-a.handoff.json"
  - id: review_b
    agent: code-reviewer
    parallel_group: review_batch
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-code-reviewer-review-b.handoff.json"
  - id: review_c
    agent: security-reviewer
    parallel_group: review_batch
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-security-reviewer-review-c.handoff.json"
  - id: finalize
    agent: project-manager
    needs: [review_a, review_b, review_c]
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-project-manager-finalize.handoff.json"
---
# synthetic-parallel-schema-test

Synthetic fixture for parallel_group schema validation.
"""


def _public_agent_ids() -> list[str]:
    return [path.stem for path in _PUBLIC_AGENTS_DIR.glob("*.md")]


def _public_workflows() -> dict[str, object]:
    store = MarkdownWorkflowStore(_PUBLIC_WORKFLOWS_DIR, agent_catalog=_public_agent_ids())
    return {workflow.name: workflow for workflow in store.list()}


def test_public_workflows_load_against_public_agent_catalog() -> None:
    """Every shipped workflow parses and references a known shipped agent."""
    workflows = _public_workflows()
    expected_names = {
        path.name.removesuffix(".workflow.md")
        for path in _PUBLIC_WORKFLOWS_DIR.glob("*.workflow.md")
    }
    assert set(workflows) == expected_names


def test_public_audit_and_review_workflows_preserve_parallel_groups(tmp_path: Path) -> None:
    """Parallel-group schema is preserved when a workflow declares parallel stages.

    The canonical public workflows (audit-fanout, release-ship) are linear after the
    v0.1.9 surface reduction. This test validates the parallel_group feature through a
    synthetic fixture decoupled from any specific shipped workflow name.
    """
    wf_file = tmp_path / "synthetic-parallel-schema-test.workflow.md"
    wf_file.write_text(_SYNTHETIC_PARALLEL_WORKFLOW, encoding="utf-8")
    store = MarkdownWorkflowStore(
        tmp_path,
        agent_catalog=["qa-engineer", "code-reviewer", "security-reviewer", "project-manager"],
    )
    workflows = {w.name: w for w in store.list()}
    wf = workflows["synthetic-parallel-schema-test"]
    parallel_stages = [s for s in wf.stages if s.parallel_group == "review_batch"]
    assert len(parallel_stages) == 3, (
        f"Expected 3 parallel stages in synthetic fixture, got {len(parallel_stages)}"
    )
