"""Workflow domain models — declarative DAG of agent stages."""

from dataclasses import dataclass, field


@dataclass
class WorkflowSummaryDTO:
    """Card-level summary of a workflow definition (no stages[], no diagram_svg)."""

    name: str
    display_name: str
    description: str
    version: str
    schema_version: str
    stage_count: int
    agent_ids: list[str]
    has_parallel: bool
    has_gates: bool
    source_path: str
    lifecycle_phase: str = "Unmapped"


@dataclass(frozen=True)
class WorkflowInput:
    name: str
    type: str
    required: bool = False
    description: str | None = None
    default: str | None = None


@dataclass(frozen=True)
class StageInputBinding:
    kind: str  # "workflow_input" | "stage_output" | "path" | "literal"
    from_ref: str
    as_name: str


@dataclass(frozen=True)
class StageExpectedOutput:
    path: str  # template; may contain {context}, {run_ts}, {run_id}
    must_include: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StageGate:
    kind: str  # "operator-approval" | "none"
    prompt: str


@dataclass(frozen=True)
class WorkflowStage:
    id: str
    agent: str
    expected_output: StageExpectedOutput
    needs: tuple[str, ...] = field(default_factory=tuple)
    parallel_group: str | None = None
    inputs: tuple[StageInputBinding, ...] = field(default_factory=tuple)
    gate: StageGate | None = None
    on_failure: str = "stop"  # "stop" | "continue" | "mark-needs-resume"


@dataclass(frozen=True)
class ExitCriterion:
    kind: str  # "all_stages" | "file_exists"
    value: str


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    description: str
    version: str
    schema_version: str
    inputs: tuple[WorkflowInput, ...]
    stages: tuple[WorkflowStage, ...]
    exit_criteria: tuple[ExitCriterion, ...] = field(default_factory=tuple)
    # Development-lifecycle phase, sourced from the workflow markdown frontmatter
    # `lifecycle_phase:` key. Falls back to "Unmapped" when absent or unrecognised.
    lifecycle_phase: str = "Unmapped"
