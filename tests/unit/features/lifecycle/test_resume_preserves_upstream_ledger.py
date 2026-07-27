"""Bug release-commit-gate-ignores-existing-plan-review-payload (Hermes game cycle 3).

A release-definition run blocked at tasks_create (post-accept lint), was resumed with
resume_from="definition_draft", and then the terminal definition_commit_gate declared
`missing_producer: plan_review` — even though plan_review's attempt-0 payload sat
persisted on disk. Upstream ledger records must survive a resume verbatim.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    ReleaseDefinitionWorkflow,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.3.1"

_VALID_PLAN = (
    "# PLAN\n\n## Validation Dependency Table\n\n"
    "| Workstream | Produces by end | Direct validation | "
    "Validation dependencies | Deferred integration evidence |\n"
    "|---|---|---|---|---|\n"
    "| WS-1 | value | unit tests | None | None |\n"
)


class _ScopeFake:
    def __init__(self) -> None:
        self.received: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received.append(request)
        allowed = request.allowed_paths[0] if request.allowed_paths else ".dadaia/handoff/x/**"
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="ok",
            artifact_refs=(allowed.replace("**", "step.handoff.json"),),
            structured_output={"verdict": "APPROVED"},
        )


def _seed(tmp_path: Path, *, tasks_body: str) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True, exist_ok=True)
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True, exist_ok=True)
    (specs / "constitution.md").write_text("# c\n", encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text("# a\n", encoding="utf-8")
    (specs / "memory" / "quality-assurance.md").write_text("# q\n", encoding="utf-8")
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    (specs / "releases" / _RELEASE / "SPEC.md").write_text("# SPEC\n", encoding="utf-8")
    (specs / "releases" / _RELEASE / "PLAN.md").write_text(_VALID_PLAN, encoding="utf-8")
    (specs / "releases" / _RELEASE / "TASKS.md").write_text(tasks_body, encoding="utf-8")
    return specs


def _workflow(tmp_path: Path, specs: Path) -> ReleaseDefinitionWorkflow:
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-17T12:00:00Z",
    )
    return ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ScopeFake(),  # type: ignore[arg-type,return-value]
        context_selector=ContextSelector(
            SpecContext(
                specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
            )
        ),
        handoff_resolver=resolver,
    )


def test_resume_after_tasks_block_keeps_plan_review_in_ledger(tmp_path: Path) -> None:
    # TASKS with a cache-dirtying pytest snippet: tasks_create's post-accept lint blocks
    # (one in-run revision, then the hard block — the fake can't fix disk content).
    bad_tasks = "# TASKS\n\n- [ ] T-1 - t\n\nRun `pytest tests/`\n"
    specs = _seed(tmp_path, tasks_body=bad_tasks)
    wf = _workflow(tmp_path, specs)

    first = wf.run("resume-ledger")
    assert first.completed is False
    assert first.blocked is not None and first.blocked.blocked_at_step == "definition_draft"

    # The operator follows the documented remediation: fix TASKS.md, resume from
    # tasks_create. Upstream ledger records (spec/plan/plan_review) must survive.
    (specs / "releases" / _RELEASE / "TASKS.md").write_text(
        "# TASKS\n\n- [ ] T-1 - t\n\nRun `pytest -p no:cacheprovider tests/`\n",
        encoding="utf-8",
    )
    resumed = wf.run("resume-ledger", resume_from="definition_draft")

    assert resumed.completed is True, resumed.blocked.reason if resumed.blocked else resumed
    run = JsonLifecycleRunStore(tmp_path).load("resume-ledger")
    assert run is not None
    producers = {record.producer_step for record in run.workflow_steps.records}
    assert "definition_review" in producers, sorted(producers)
    assert "definition_review" in producers, sorted(producers)


def test_commit_gate_recovers_ledger_record_from_persisted_payload(tmp_path: Path) -> None:
    """The interrupted-worker class: a ledger record can be lost between resets/resumes
    while its immutable payload file survives on disk. The terminal graph gate must
    reconcile from the durable payload instead of blocking on the in-memory ledger.
    """
    from dataclasses import replace as _replace

    from dadaia_workspace.core.models.workflow_handoff import WorkflowStepLedger

    good_tasks = "# TASKS\n\n- [ ] T-1 - t\n\nRun `pytest -p no:cacheprovider tests/`\n"
    specs = _seed(tmp_path, tasks_body=good_tasks)
    wf = _workflow(tmp_path, specs)

    first = wf.run("recover-ledger")
    assert first.completed is True

    # Simulate the loss: drop plan_review's record from the persisted run while its
    # attempt-0 payload file stays on disk (exactly the Hermes evidence shape).
    store = JsonLifecycleRunStore(tmp_path)
    run = store.load("recover-ledger")
    assert run is not None
    kept = tuple(r for r in run.workflow_steps.records if r.producer_step != "definition_review")
    assert len(kept) == len(run.workflow_steps.records) - 1
    store.save(
        _replace(
            run,
            status=run.status.__class__("blocked"),
            workflow_steps=WorkflowStepLedger(records=kept),
        )
    )

    resumed = wf.run("recover-ledger", resume_from="definition_commit_gate")

    assert resumed.completed is True, resumed.blocked.reason if resumed.blocked else resumed
    reloaded = store.load("recover-ledger")
    assert reloaded is not None
    producers = {r.producer_step for r in reloaded.workflow_steps.records}
    assert "definition_review" in producers, sorted(producers)
