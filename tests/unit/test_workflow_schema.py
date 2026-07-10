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


_PARALLEL_INTERNAL_DEP = """---
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


@pytest.mark.parametrize(
    ("name", "filename", "content", "agent_catalog"),
    [
        ("missing_name", "demo.workflow.md", _VALID.replace("name: demo", 'name: ""'), None),
        ("filename_mismatches_name", "other.workflow.md", _VALID, None),
        (
            "unknown_agent",
            "demo.workflow.md",
            _VALID,
            ["product-engineer"],  # missing software-architect
        ),
        (
            "parallel_group_member_with_internal_dep",
            "pg.workflow.md",
            _PARALLEL_INTERNAL_DEP,
            ["product-engineer"],
        ),
    ],
)
def test_schema_rejection_table(
    tmp_path: Path, name: str, filename: str, content: str, agent_catalog: list[str] | None
) -> None:
    _write(tmp_path, filename, content)
    store = MarkdownWorkflowStore(tmp_path, agent_catalog=agent_catalog)
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


def test_agent_placeholder_resolved_and_unknown_input_rejected(tmp_path: Path) -> None:
    """Stage 'agent' may use {{<input_name>}} when the input is declared, and a
    placeholder pointing at an undeclared name must fail validation."""
    ok_dir = tmp_path / "ok"
    ok_dir.mkdir()
    _write(ok_dir, "param.workflow.md", _VALID_PLACEHOLDER)
    ok_store = MarkdownWorkflowStore(
        ok_dir, agent_catalog=["product-engineer", "software-engineer"]
    )
    workflows = ok_store.list()
    assert len(workflows) == 1
    impl_stage = next(s for s in workflows[0].stages if s.id == "implement")
    # The placeholder is stored verbatim — the orchestrator resolves it at run time.
    assert impl_stage.agent == "{{implementer_agent}}"

    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    broken = _VALID_PLACEHOLDER.replace("{{implementer_agent}}", "{{unknown_param}}")
    _write(bad_dir, "param.workflow.md", broken)
    bad_store = MarkdownWorkflowStore(
        bad_dir, agent_catalog=["product-engineer", "software-engineer"]
    )
    with pytest.raises(WorkflowSchemaError):
        bad_store.list()


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


def test_unknown_workflow_get_raises_and_synthetic_parallel_groups_preserved(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "demo.workflow.md", _VALID)
    store = MarkdownWorkflowStore(
        tmp_path, agent_catalog=["product-engineer", "software-architect"]
    )
    with pytest.raises(WorkflowNotFoundError):
        store.get("ghost")

    # Parallel-group schema is preserved when a workflow declares parallel stages. The
    # canonical public workflows (audit-fanout, release-ship) are linear after the
    # v0.1.9 surface reduction — this validates the parallel_group feature through a
    # synthetic fixture decoupled from any specific shipped workflow name.
    parallel_dir = tmp_path / "parallel"
    parallel_dir.mkdir()
    wf_file = parallel_dir / "synthetic-parallel-schema-test.workflow.md"
    wf_file.write_text(_SYNTHETIC_PARALLEL_WORKFLOW, encoding="utf-8")
    parallel_store = MarkdownWorkflowStore(
        parallel_dir,
        agent_catalog=["qa-engineer", "code-reviewer", "security-reviewer", "project-manager"],
    )
    workflows = {w.name: w for w in parallel_store.list()}
    wf = workflows["synthetic-parallel-schema-test"]
    parallel_stages = [s for s in wf.stages if s.parallel_group == "review_batch"]
    assert len(parallel_stages) == 3, (
        f"Expected 3 parallel stages in synthetic fixture, got {len(parallel_stages)}"
    )
