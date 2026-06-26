"""Pure lifecycle models for deterministic dadaia workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class LifecyclePhase(StrEnum):
    BACKLOG_DEFINITION = "backlog_definition"
    RELEASE_DEFINITION = "release_definition"
    IMPLEMENTATION = "implementation"
    QA_REVIEW = "qa_review"
    SECURITY_REVIEW = "security_review"
    CODE_REVIEW = "code_review"
    CLOSURE = "closure"
    BLOCKED = "blocked"


class LifecycleRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class GateEvidenceKind(StrEnum):
    ACTIVE_RELEASE = "active_release"
    HANDOFF = "handoff"
    GIT_STATUS = "git_status"
    COMMIT_SHA = "commit_sha"
    DIRTY_DIFF = "dirty_diff"
    TEST_RESULT = "test_result"
    SPECS_DOCTOR = "specs_doctor"
    HYGIENE_COUNTERS = "hygiene_counters"


class GateVerdict(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AgentRuntimeKind(StrEnum):
    FAKE = "fake"
    CODEX_EXEC = "codex_exec"
    CLAUDE_SDK = "claude_sdk"
    PI_HEADLESS = "pi_headless"


class AgentRunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


TRANSITIONS: dict[LifecyclePhase, frozenset[LifecyclePhase]] = {
    LifecyclePhase.BACKLOG_DEFINITION: frozenset(
        {LifecyclePhase.RELEASE_DEFINITION, LifecyclePhase.BLOCKED}
    ),
    LifecyclePhase.RELEASE_DEFINITION: frozenset(
        {LifecyclePhase.IMPLEMENTATION, LifecyclePhase.BLOCKED}
    ),
    LifecyclePhase.IMPLEMENTATION: frozenset({LifecyclePhase.QA_REVIEW, LifecyclePhase.BLOCKED}),
    LifecyclePhase.QA_REVIEW: frozenset(
        {LifecyclePhase.IMPLEMENTATION, LifecyclePhase.SECURITY_REVIEW, LifecyclePhase.BLOCKED}
    ),
    LifecyclePhase.SECURITY_REVIEW: frozenset(
        {LifecyclePhase.IMPLEMENTATION, LifecyclePhase.CODE_REVIEW, LifecyclePhase.BLOCKED}
    ),
    LifecyclePhase.CODE_REVIEW: frozenset(
        {LifecyclePhase.IMPLEMENTATION, LifecyclePhase.CLOSURE, LifecyclePhase.BLOCKED}
    ),
    LifecyclePhase.CLOSURE: frozenset({LifecyclePhase.BLOCKED}),
    LifecyclePhase.BLOCKED: frozenset(
        {
            LifecyclePhase.BACKLOG_DEFINITION,
            LifecyclePhase.RELEASE_DEFINITION,
            LifecyclePhase.IMPLEMENTATION,
            LifecyclePhase.QA_REVIEW,
            LifecyclePhase.SECURITY_REVIEW,
            LifecyclePhase.CODE_REVIEW,
            LifecyclePhase.CLOSURE,
        }
    ),
}


def is_legal_transition(source: LifecyclePhase, target: LifecyclePhase) -> bool:
    """Return whether the lifecycle state table permits source -> target."""
    return target in TRANSITIONS[source]


@dataclass(frozen=True)
class BlockedState:
    reason: str
    blocked_at_step: str
    resume_token: str | None = None
    operator_command: str | None = None
    detail: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "blocked_at_step": self.blocked_at_step,
            "resume_token": self.resume_token,
            "operator_command": self.operator_command,
            "detail": dict(self.detail),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> BlockedState:
        detail_raw = data.get("detail", {})
        assert isinstance(detail_raw, dict)
        return cls(
            reason=str(data["reason"]),
            blocked_at_step=str(data["blocked_at_step"]),
            resume_token=_optional_str(data.get("resume_token")),
            operator_command=_optional_str(data.get("operator_command")),
            detail={str(k): str(v) for k, v in detail_raw.items()},
        )


@dataclass(frozen=True)
class GateEvidence:
    evidence_kind: GateEvidenceKind
    source: str
    context: str
    release_id: str
    agent: str | None = None
    verdict: GateVerdict | None = None
    commit_sha: str | None = None
    task_group: str | None = None
    metrics: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_kind": self.evidence_kind.value,
            "source": self.source,
            "context": self.context,
            "release_id": self.release_id,
            "agent": self.agent,
            "verdict": self.verdict.value if self.verdict else None,
            "commit_sha": self.commit_sha,
            "task_group": self.task_group,
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> GateEvidence:
        metrics_raw = data.get("metrics", {})
        assert isinstance(metrics_raw, dict)
        verdict = data.get("verdict")
        return cls(
            evidence_kind=GateEvidenceKind(str(data["evidence_kind"])),
            source=str(data["source"]),
            context=str(data["context"]),
            release_id=str(data["release_id"]),
            agent=_optional_str(data.get("agent")),
            verdict=GateVerdict(str(verdict)) if verdict else None,
            commit_sha=_optional_str(data.get("commit_sha")),
            task_group=_optional_str(data.get("task_group")),
            metrics={str(k): str(v) for k, v in metrics_raw.items()},
        )


@dataclass(frozen=True)
class GateRequirement:
    evidence_kind: GateEvidenceKind
    required_agent: str | None = None
    required_verdict: GateVerdict | None = None
    release_id: str | None = None
    commit_sha: str | None = None
    task_group: str | None = None
    max_unresolved_severity: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_kind": self.evidence_kind.value,
            "required_agent": self.required_agent,
            "required_verdict": self.required_verdict.value if self.required_verdict else None,
            "release_id": self.release_id,
            "commit_sha": self.commit_sha,
            "task_group": self.task_group,
            "max_unresolved_severity": self.max_unresolved_severity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> GateRequirement:
        verdict = data.get("required_verdict")
        return cls(
            evidence_kind=GateEvidenceKind(str(data["evidence_kind"])),
            required_agent=_optional_str(data.get("required_agent")),
            required_verdict=GateVerdict(str(verdict)) if verdict else None,
            release_id=_optional_str(data.get("release_id")),
            commit_sha=_optional_str(data.get("commit_sha")),
            task_group=_optional_str(data.get("task_group")),
            max_unresolved_severity=_optional_str(data.get("max_unresolved_severity")),
        )


@dataclass(frozen=True)
class InjectedContext:
    """Auditable record of the prompt composition injected into one workflow step.

    Records which fragment ids were assembled and which dynamic-context refs
    (file paths, atom slugs, handoff ids) the context selector (WS-4) resolved for
    a step, plus the ``max_context_policy`` that bounded each resolution. This makes
    context selection auditable per epic §8.8 — every run records which fragments and
    which dynamic files were injected.

    The WS-9 prompt-observability fields complete the per-step composition record so a
    run's prompt is fully queryable without re-running it:

    - ``prefix_hash`` — sha256 of the cacheable :class:`PromptPrefix` reused across
      steps (byte-identity is the cacheability invariant);
    - ``model`` — the discrete model id selected for the step (LAW 2);
    - ``runtime_kind`` — the Layer-2 harness the step ran on (pi/codex/fake);
    - ``output_schema`` — the fragment's declared output contract; and
    - ``gate_result`` — the Python gate verdict for the step (``APPROVED`` /
      ``REJECTED``), or ``None`` for a non-gated step.

    The five WS-9 fields default to ``None`` so the WS-4 context-audit seam
    (``to_injected_context``) and existing run records remain valid; the workflow
    enriches the entry with them once the step's gate has run.
    """

    step: str
    fragment_ids: tuple[str, ...] = ()
    refs: tuple[str, ...] = ()
    policies: tuple[str, ...] = ()
    prefix_hash: str | None = None
    model: str | None = None
    runtime_kind: str | None = None
    output_schema: str | None = None
    gate_result: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "fragment_ids": list(self.fragment_ids),
            "refs": list(self.refs),
            "policies": list(self.policies),
            "prefix_hash": self.prefix_hash,
            "model": self.model,
            "runtime_kind": self.runtime_kind,
            "output_schema": self.output_schema,
            "gate_result": self.gate_result,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> InjectedContext:
        fragment_ids = data.get("fragment_ids", [])
        refs = data.get("refs", [])
        policies = data.get("policies", [])
        assert isinstance(fragment_ids, list)
        assert isinstance(refs, list)
        assert isinstance(policies, list)
        return cls(
            step=str(data["step"]),
            fragment_ids=tuple(str(item) for item in fragment_ids),
            refs=tuple(str(item) for item in refs),
            policies=tuple(str(item) for item in policies),
            prefix_hash=_optional_str(data.get("prefix_hash")),
            model=_optional_str(data.get("model")),
            runtime_kind=_optional_str(data.get("runtime_kind")),
            output_schema=_optional_str(data.get("output_schema")),
            gate_result=_optional_str(data.get("gate_result")),
        )


@dataclass(frozen=True)
class LifecycleRun:
    run_id: str
    context: str
    release_id: str
    command: str
    phase: LifecyclePhase
    status: LifecycleRunStatus
    current_step: str
    expected_artifacts: tuple[str, ...] = ()
    idempotency_key: str | None = None
    blocked: BlockedState | None = None
    injected_context: tuple[InjectedContext, ...] = ()

    def prompt_composition(self) -> tuple[dict[str, Any], ...]:
        """Return the per-step prompt composition for this run (WS-9 observability).

        A minimal, queryable projection of each step's ``InjectedContext`` — the
        fragment ids, dynamic-context refs, prefix hash, discrete model, runtime kind,
        output schema, and gate result. This is the deferred-panel-view stand-in: the
        fields are persisted and surfaced as plain data so a report/panel view can read
        them without re-running the workflow.
        """
        return tuple(entry.to_dict() for entry in self.injected_context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "context": self.context,
            "release_id": self.release_id,
            "command": self.command,
            "phase": self.phase.value,
            "status": self.status.value,
            "current_step": self.current_step,
            "expected_artifacts": list(self.expected_artifacts),
            "idempotency_key": self.idempotency_key,
            "blocked": self.blocked.to_dict() if self.blocked else None,
            "injected_context": [entry.to_dict() for entry in self.injected_context],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> LifecycleRun:
        artifacts_raw = data.get("expected_artifacts", [])
        assert isinstance(artifacts_raw, list)
        blocked_raw = data.get("blocked")
        assert blocked_raw is None or isinstance(blocked_raw, dict)
        injected_raw = data.get("injected_context", [])
        assert isinstance(injected_raw, list)
        injected: list[InjectedContext] = []
        for entry in injected_raw:
            assert isinstance(entry, dict)
            injected.append(InjectedContext.from_dict(entry))
        return cls(
            run_id=str(data["run_id"]),
            context=str(data["context"]),
            release_id=str(data["release_id"]),
            command=str(data["command"]),
            phase=LifecyclePhase(str(data["phase"])),
            status=LifecycleRunStatus(str(data["status"])),
            current_step=str(data["current_step"]),
            expected_artifacts=tuple(str(item) for item in artifacts_raw),
            idempotency_key=_optional_str(data.get("idempotency_key")),
            blocked=BlockedState.from_dict(blocked_raw) if blocked_raw else None,
            injected_context=tuple(injected),
        )


@dataclass(frozen=True)
class AgentRunRequest:
    role: str
    prompt: str
    runtime: AgentRuntimeKind
    context: str
    release_id: str
    task_id: str | None = None
    model_profile: str | None = None
    allowed_paths: tuple[str, ...] = ()
    forbidden_paths: tuple[str, ...] = ()
    expected_schema: str | None = None
    required_evidence: tuple[GateEvidenceKind, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "prompt": self.prompt,
            "runtime": self.runtime.value,
            "context": self.context,
            "release_id": self.release_id,
            "task_id": self.task_id,
            "model_profile": self.model_profile,
            "allowed_paths": list(self.allowed_paths),
            "forbidden_paths": list(self.forbidden_paths),
            "expected_schema": self.expected_schema,
            "required_evidence": [kind.value for kind in self.required_evidence],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AgentRunRequest:
        allowed_paths = data.get("allowed_paths", [])
        forbidden_paths = data.get("forbidden_paths", [])
        required_evidence = data.get("required_evidence", [])
        assert isinstance(allowed_paths, list)
        assert isinstance(forbidden_paths, list)
        assert isinstance(required_evidence, list)
        return cls(
            role=str(data["role"]),
            prompt=str(data["prompt"]),
            runtime=AgentRuntimeKind(str(data["runtime"])),
            context=str(data["context"]),
            release_id=str(data["release_id"]),
            task_id=_optional_str(data.get("task_id")),
            model_profile=_optional_str(data.get("model_profile")),
            allowed_paths=tuple(str(path) for path in allowed_paths),
            forbidden_paths=tuple(str(path) for path in forbidden_paths),
            expected_schema=_optional_str(data.get("expected_schema")),
            required_evidence=tuple(GateEvidenceKind(str(kind)) for kind in required_evidence),
        )


@dataclass(frozen=True)
class AgentRunResult:
    status: AgentRunStatus
    summary: str
    artifact_refs: tuple[str, ...] = ()
    structured_output: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "summary": self.summary,
            "artifact_refs": list(self.artifact_refs),
            "structured_output": dict(self.structured_output),
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AgentRunResult:
        artifact_refs = data.get("artifact_refs", [])
        structured_output = data.get("structured_output", {})
        assert isinstance(artifact_refs, list)
        assert isinstance(structured_output, dict)
        return cls(
            status=AgentRunStatus(str(data["status"])),
            summary=str(data["summary"]),
            artifact_refs=tuple(str(ref) for ref in artifact_refs),
            structured_output={str(k): str(v) for k, v in structured_output.items()},
            error=_optional_str(data.get("error")),
        )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
