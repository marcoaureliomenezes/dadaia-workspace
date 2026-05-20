"""Run-state domain models — durable representation of orchestrate runs."""

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


def make_run_id(now: datetime | None = None) -> str:
    """ULID-like: UTC timestamp compact + 6-char random suffix."""
    ts = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}-{secrets.token_hex(3)}"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_GATE = "awaiting_gate"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_RESUME = "needs_resume"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_GATE = "awaiting_gate"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EventKind(StrEnum):
    RUN_STARTED = "run_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    GATE_PENDING = "gate_pending"
    GATE_RESOLVED = "gate_resolved"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


class DispatcherMode(StrEnum):
    NATIVE = "native"
    BEST_EFFORT_SEQUENTIAL = "best-effort-sequential"
    UNSUPPORTED = "unsupported"
    CLI_ONLY = "cli-only"
    CODEX = "codex"


@dataclass(frozen=True)
class StageState:
    id: str
    agent: str
    status: StageStatus
    started_at: str | None = None
    finished_at: str | None = None
    output_path: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    workflow_name: str
    workflow_version: str
    context: str
    runtime: str
    status: RunStatus
    started_at: str
    finished_at: str | None
    stages: tuple[StageState, ...]
    inputs: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RunEvent:
    ts: str
    run_id: str
    kind: EventKind
    stage_id: str | None = None
    payload: dict[str, str] | None = None


@dataclass(frozen=True)
class StageInvocation:
    run_id: str
    stage_id: str
    workflow_name: str
    agent: str
    inputs: dict[str, str]
    expected_output_path: str
    must_include: tuple[str, ...]
    parallel_group: str | None
    invocation_path: str


@dataclass(frozen=True)
class StageResult:
    run_id: str
    stage_id: str
    status: StageStatus
    output_path: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class DispatcherCapabilities:
    runtime_name: str
    supports_parallel: bool
    supports_gates_inline: bool
    mode: DispatcherMode
