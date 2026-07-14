"""BacklogDefinitionWorkflow — the simplified author-first sequence with a REAL gate.

End-to-end on the FAKE harness. Proves the v0.2.x simplified behaviours:

- the default path runs exactly ONE model step (``backlog_author``) followed by the
  Python ``backlog_review_gate``; ``intake_grill`` is skipped unless ``grill=True``;
- the review gate validates what the author ACTUALLY wrote to disk: no new/changed
  ``specs/backlog/*.md`` item blocks; a NEW item overlapping an existing item's bound
  anchors blocks (the R1 classifier over real files, not a CLI-threaded demand);
- ``grill=True`` runs the intake grill and injects its payload digest into the author
  prompt (the grill output is consumed, never discarded);
- ``resume_from="backlog_author"`` re-runs authoring without re-running the grill.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry
from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    SpecContext,
)
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    _SEQUENCE,
    BacklogDefinitionWorkflow,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.26"

_ANCHOR_A = "pkg/a.py#A"

_ITEM_A = """\
---
slug: {slug}
status: OPEN
intents:
  - subject: {{ kind: code, ref: pkg/a.py#A }}
    change: {change}
---

# {slug}

Body of {slug}.
"""


@dataclass
class _AuthoringFake:
    """Approves every step; optionally WRITES a backlog item during backlog_author."""

    root: Path
    writes_item: bool = True
    slug: str = "new-item"
    change: str = "add A"
    received: list[AgentRunRequest] | None = None

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if self.received is None:
            self.received = []
        self.received.append(request)
        step = (request.task_id or "").rsplit(":", 1)[-1]
        artifact = f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/{step}.step-output.json"
        path = self.root / artifact
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"fake": true}\n', encoding="utf-8")
        if step == "backlog_author" and self.writes_item:
            item = self.root / "specs" / "backlog" / f"{self.slug}.md"
            item.parent.mkdir(parents=True, exist_ok=True)
            item.write_text(_ITEM_A.format(slug=self.slug, change=self.change), encoding="utf-8")
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="ok",
            artifact_refs=(artifact,),
            structured_output={"verdict": "APPROVED"},
            domain_payload={"summary": f"{step} done", "open_questions": []},
        )


class _MemoryRunStore:
    def __init__(self) -> None:
        self.saved: dict[str, LifecycleRun] = {}

    def save(self, run: LifecycleRun) -> None:
        self.saved[run.run_id] = run

    def load(self, run_id: str) -> LifecycleRun | None:
        return self.saved.get(run_id)

    def resume(self, run_id: str) -> LifecycleRun:
        run = self.saved.get(run_id)
        if run is None:
            raise LifecycleRunStoreError(message="missing", path=None)
        return run


def _registry(tmp_path: Path) -> Registry:
    specs = tmp_path / "specs"
    (specs / "memory" / "product").mkdir(parents=True, exist_ok=True)
    pkg = tmp_path / "pkg"
    pkg.mkdir(exist_ok=True)
    (pkg / "a.py").write_text("class A:\n    pass\n", encoding="utf-8")
    return build_registry(
        source_root=tmp_path,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=tmp_path / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs,
        cli_anchors=frozenset(),
    )


def _workflow(
    tmp_path: Path, store: _MemoryRunStore, fake: _AuthoringFake
) -> BacklogDefinitionWorkflow:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    selector = ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / "handoff")
    )
    json_store = JsonLifecycleRunStore(tmp_path)
    resolver = WorkflowHandoffResolver(
        run_store=json_store,
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-14T12:00:00Z",
    )
    return BacklogDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=json_store,
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=selector,
        registry=_registry(tmp_path),
        handoff_resolver=resolver,
    )


def test_default_path_is_one_model_step_and_completes(tmp_path: Path) -> None:
    fake = _AuthoringFake(root=tmp_path)
    wf = _workflow(tmp_path, _MemoryRunStore(), fake)

    result = wf.run("bd-1", operator_demand="add class A support")

    assert result.completed is True
    assert result.final_phase is LifecyclePhase.RELEASE_DEFINITION
    labels = [(s.label, s.skipped) for s in result.steps]
    assert labels == [
        ("intake_grill", True),
        ("backlog_author", False),
        ("backlog_review_gate", False),
    ]
    # Exactly ONE worker session ran (the author) — the grill cost zero model calls.
    assert [r.task_id.rsplit(":", 1)[-1] for r in (fake.received or [])] == ["backlog_author"]
    author_prompt = (fake.received or [])[0].prompt
    assert "add class A support" in author_prompt


def test_gate_blocks_when_author_writes_nothing(tmp_path: Path) -> None:
    fake = _AuthoringFake(root=tmp_path, writes_item=False)
    wf = _workflow(tmp_path, _MemoryRunStore(), fake)

    result = wf.run("bd-nothing")

    assert result.completed is False
    assert result.blocked is not None
    assert result.blocked.blocked_at_step == "backlog_review_gate"
    assert "no new/changed item" in result.blocked.reason


def test_gate_blocks_new_item_overlapping_existing_anchor(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    (specs / "backlog" / "existing-a.md").write_text(
        _ITEM_A.format(slug="existing-a", change="rework A"), encoding="utf-8"
    )
    fake = _AuthoringFake(root=tmp_path, slug="twin-item", change="rework A differently")
    wf = _workflow(tmp_path, _MemoryRunStore(), fake)

    result = wf.run("bd-twin")

    assert result.completed is False
    assert result.blocked is not None
    assert result.blocked.blocked_at_step == "backlog_review_gate"
    assert "twin-item" in result.blocked.reason


def test_grill_opt_in_runs_and_its_digest_reaches_the_author_prompt(tmp_path: Path) -> None:
    fake = _AuthoringFake(root=tmp_path)
    wf = _workflow(tmp_path, _MemoryRunStore(), fake)

    result = wf.run("bd-grill", grill=True, operator_demand="add class A support")

    assert result.completed is True
    ran = [r.task_id.rsplit(":", 1)[-1] for r in (fake.received or [])]
    assert ran == ["intake_grill", "backlog_author"]
    author_prompt = (fake.received or [])[-1].prompt
    # The grill payload digest was injected — its output is consumed, not discarded.
    assert "intake_grill" in author_prompt


def test_resume_from_author_skips_the_grill(tmp_path: Path) -> None:
    fake = _AuthoringFake(root=tmp_path, writes_item=False)
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, fake)

    first = wf.run("bd-resume", grill=True)
    assert first.completed is False

    fake.writes_item = True
    resumed = wf.run("bd-resume", grill=True, resume_from="backlog_author")
    assert resumed.completed is True
    ran = [r.task_id.rsplit(":", 1)[-1] for r in (fake.received or [])]
    # grill ran ONCE (first attempt); the resume re-ran only the author.
    assert ran == ["intake_grill", "backlog_author", "backlog_author"]


def test_sequence_shape() -> None:
    assert [s.label for s in _SEQUENCE] == [
        "intake_grill",
        "backlog_author",
        "backlog_review_gate",
    ]
