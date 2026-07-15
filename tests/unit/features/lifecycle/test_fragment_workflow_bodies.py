"""Shared workflow-body suite over the ``FragmentGateWorkflow`` base (v0.1.57 FR1).

``release_definition`` / ``audit`` are thin subclasses of the
same base — role -> fragments -> dynamic selector -> output schema -> Python gate, wired to the
same Wave-D handoff ledger. Before the FR1 dedup each body carried its own copy-paste suite
proving these four behaviors; they are now ONE parametrized suite over the four workflow
classes, replacing ~19 near-identical functions (T-5, plan-lifecycle.md).

Each param case supplies: the workflow class, its module (for ``_SEQUENCE`` + step type +
fixture setup), a ``_workspace`` seeder, and the expected step labels. Workflow-specific
behavior (audit's graph-completeness BLOCK branch and
release_definition's rejected-review-blocks-advancement) stays in each slim per-workflow file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
)
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.features.lifecycle.workflows import (
    audit,
    release_definition,
)
from dadaia_workspace.features.lifecycle.workflows.audit import AuditStep, AuditWorkflow
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    ReleaseDefinitionWorkflow,
    ReleaseStep,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

pytestmark = pytest.mark.unit

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.30"
_VALIDATION_DEPENDENCY_TABLE = (
    "## Validation Dependency Table\n\n"
    "| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |\n"
    "|---|---|---|---|---|\n"
    "| WS-1 | value | unit tests | None | None |\n"
)


@dataclass(frozen=True)
class _KindFake:
    kind: AgentRuntimeKind
    result: AgentRunResult

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return self.result


def _approved() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="step ok",
        artifact_refs=(f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json",),
        structured_output={"verdict": "APPROVED"},
    )


@dataclass(frozen=True)
class _AuditFake:
    kind: AgentRuntimeKind

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        step = (request.task_id or "").rsplit(":", 1)[-1]
        payloads: dict[str, dict[str, object]] = {
            "audit_scope": {
                "summary": "Bound architecture drift.",
                "audit_question": "Does implementation match architecture memory?",
                "lenses": [{"name": "architecture", "rationale": "Contract fidelity."}],
                "surfaces": ["src/games.py"],
                "acceptance_criteria": [
                    {"lens": "architecture", "pass_condition": "No contract drift."}
                ],
            },
            "drift_scan": {
                "summary": "No drift found.",
                "verdict": "APPROVED",
                "verdict_reason": "Every scoped lens passed.",
                "lens_results": [
                    {
                        "lens": "architecture",
                        "status": "PASS",
                        "evidence": ["src/games.py:1"],
                    }
                ],
                "findings": [],
            },
            "triage": {
                "summary": "No findings require routing.",
                "source_verdict": "APPROVED",
                "dispositions": [],
            },
        }
        payload = payloads[step]
        artifact_ref = f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/{step}.step-output.json"
        verdict = payload.get("verdict")
        structured: dict[str, str] = {"verdict": verdict} if isinstance(verdict, str) else {}
        if isinstance(payload.get("verdict_reason"), str):
            structured["verdict_reason"] = payload["verdict_reason"]
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=str(payload["summary"]),
            artifact_refs=(artifact_ref,),
            structured_output=structured,
            domain_payload=payload,
        )


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "bugs").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text("# c\n", encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text("# a\n", encoding="utf-8")
    (specs / "memory" / "quality-assurance.md").write_text("# q\n", encoding="utf-8")
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    for art in ("SPEC.md", "PLAN.md", "TASKS.md"):
        body = f"# {art}\n"
        if art == "PLAN.md":
            body += f"\n{_VALIDATION_DEPENDENCY_TABLE}"
        (specs / "releases" / _RELEASE / art).write_text(body, encoding="utf-8")
    return tmp_path


def _resolver(tmp_path: Path) -> WorkflowHandoffResolver:
    return WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-06-27T12:00:00Z",
    )


def _selector(tmp_path: Path) -> ContextSelector:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    return ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )


@dataclass(frozen=True)
class _WorkflowCase:
    case_id: str
    workflow_cls: type
    module: Any
    labels: tuple[str, ...]
    runtime_factory: Any = None  # override; default is uniform-approved

    def factory(self) -> Any:
        if self.runtime_factory is not None:
            return self.runtime_factory
        return lambda kind: _KindFake(kind, _approved())

    def build(self, tmp_path: Path, *, resolver: WorkflowHandoffResolver | None) -> Any:
        _workspace(tmp_path)
        kwargs = dict(
            context=_CONTEXT,
            release_id=_RELEASE,
            run_store=JsonLifecycleRunStore(tmp_path),
            runtime_factory=self.factory(),
            context_selector=_selector(tmp_path),
            handoff_resolver=resolver,
        )
        return self.workflow_cls(**kwargs)


_CASES = (
    _WorkflowCase(
        "audit",
        AuditWorkflow,
        audit,
        ("audit_scope", "drift_scan", "triage", "audit_disposition_gate"),
        runtime_factory=lambda kind: _AuditFake(kind),
    ),
    _WorkflowCase(
        "release_definition",
        ReleaseDefinitionWorkflow,
        release_definition,
        (
            "release_scope",
            "spec_create",
            "spec_arch_review",
            "spec_qa_review",
            "plan_create",
            "plan_review",
            "tasks_create",
            "tasks_implementability_review",
            "definition_commit_gate",
        ),
    ),
)


def _ids(cases: tuple[_WorkflowCase, ...]) -> list[str]:
    return [c.case_id for c in cases]


# ---------------------------------------------------------------------------
# ① e2e completes + exact step labels + terminal gate + injected fragment ids
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", _CASES, ids=_ids(_CASES))
def test_body_completes_end_to_end_with_recorded_fragments(
    tmp_path: Path, case: _WorkflowCase
) -> None:
    """Runs to completion on the fake runtime, hits every labeled step in order, ends on the
    terminal Python gate, and records each model step's injected fragment ids (auditability)."""
    resolver = _resolver(tmp_path)
    wf = case.build(tmp_path, resolver=resolver)

    result = wf.run(f"{case.case_id}-run")  # must not raise NotImplementedError

    assert result.completed is True
    labels = [s.label for s in result.steps]
    assert labels == list(case.labels)
    assert result.steps[-1].is_gate is True

    run = JsonLifecycleRunStore(tmp_path).load(f"{case.case_id}-run")
    assert run is not None
    by_step = {ic.step: ic for ic in run.injected_context}
    seq_by_label = {step.label: step for step in case.module._SEQUENCE}
    for label in case.labels[:-1]:  # every model step (all but the terminal gate)
        assert seq_by_label[label].fragment_id in by_step[label].fragment_ids


def test_release_definition_approves_yaml_frontmatter_statuses(tmp_path: Path) -> None:
    wf = _CASES[1].build(tmp_path, resolver=_resolver(tmp_path))
    release_dir = tmp_path / "repos" / _CONTEXT / "specs" / "releases" / _RELEASE
    for artifact in ("SPEC.md", "PLAN.md", "TASKS.md"):
        plan_contract = f"\n{_VALIDATION_DEPENDENCY_TABLE}" if artifact == "PLAN.md" else ""
        (release_dir / artifact).write_text(
            f"---\nrelease: {_RELEASE}\nstatus: Draft\n---\n\n# {artifact}\n\n"
            f"**Status:** Draft\n{plan_contract}",
            encoding="utf-8",
        )

    result = wf.run("release-definition-yaml-status")

    assert result.completed is True
    for artifact in ("SPEC.md", "PLAN.md", "TASKS.md"):
        text = (release_dir / artifact).read_text(encoding="utf-8")
        assert "status:" not in text
        assert "status: Draft" not in text
        assert text.count("> **Status:** Aprovado") == 1
        assert "**Status:** Draft" not in text


# ---------------------------------------------------------------------------
# ② downstream consumes EXACT upstream payload by (run, step, attempt)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", _CASES, ids=_ids(_CASES))
def test_downstream_consumes_exact_upstream_payload(tmp_path: Path, case: _WorkflowCase) -> None:
    resolver = _resolver(tmp_path)
    wf = case.build(tmp_path, resolver=resolver)
    wf.run(f"{case.case_id}-consume")

    run = JsonLifecycleRunStore(tmp_path).load(f"{case.case_id}-consume")
    assert run is not None
    producer_label, consumer_label = case.labels[0], case.labels[1]
    producer_record = run.workflow_steps.find(producer_label, 0)
    assert producer_record is not None
    consumers = {(c.consumer_step, c.consumer_attempt) for c in producer_record.consumptions}
    assert (consumer_label, 0) in consumers
    # A18: the payload artifact is immutable and lands under the workspace-root runs zone.
    assert producer_record.payload_ref.startswith(
        f".dadaia/runs/lifecycle/{case.case_id}-consume/steps/"
    )
    assert (tmp_path / producer_record.payload_ref).is_file()


# ---------------------------------------------------------------------------
# ③ missing required upstream BLOCKS with reason
# ---------------------------------------------------------------------------


def _broken_sequence(case: _WorkflowCase) -> tuple[Any, ...]:
    """A 2-step sequence whose only model step CONSUMES a producer that never ran."""
    consumer_label, gate_label = case.labels[1], case.labels[-1]
    step_cls: type
    kwargs: dict[str, Any]
    if case.case_id == "audit":
        step_cls = AuditStep
        kwargs = {"role": "project-auditor", "is_review": True}
    elif case.case_id == "release_definition":
        step_cls = ReleaseStep
        kwargs = {"role": "product-engineer", "is_review": True}
    consumer = step_cls(
        label=consumer_label,
        fragment_id=f"{case.module.__name__.rsplit('.', 1)[-1]}.{consumer_label}",
        produces="generic-step-handoff-v1",
        consumes=(case.labels[0],),  # producer never ran in this sequence
        **kwargs,
    )
    gate = step_cls(label=gate_label, role="python", fragment_id=None)
    return (consumer, gate)


@pytest.mark.parametrize("case", _CASES, ids=_ids(_CASES))
def test_missing_required_upstream_blocks(tmp_path: Path, case: _WorkflowCase) -> None:
    resolver = _resolver(tmp_path)
    wf = case.build(tmp_path, resolver=resolver)

    result = wf.run(f"{case.case_id}-block", sequence=_broken_sequence(case))

    assert result.completed is False
    assert result.final_phase is LifecyclePhase.BLOCKED
    assert result.blocked is not None
    assert "required upstream handoff unavailable" in result.blocked.reason


# ---------------------------------------------------------------------------
# ④ no-resolver wired -> runs (back-compat), zero ledger entries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", _CASES, ids=_ids(_CASES))
def test_without_resolver_runs_and_writes_no_ledger(tmp_path: Path, case: _WorkflowCase) -> None:
    wf = case.build(tmp_path, resolver=None)

    result = wf.run(f"{case.case_id}-nores")

    assert result.completed is True
    run = JsonLifecycleRunStore(tmp_path).load(f"{case.case_id}-nores")
    assert run is not None
    assert len(run.workflow_steps) == 0
    assert [s.label for s in case.module._SEQUENCE if s.produces][0] == case.labels[0]
