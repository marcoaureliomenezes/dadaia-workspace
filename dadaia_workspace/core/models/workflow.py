"""Workflow domain models — declarative DAG of agent stages."""

from dataclasses import dataclass, field


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
