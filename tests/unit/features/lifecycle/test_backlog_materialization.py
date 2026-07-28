"""v0.2.9 T1 — backlog_author acceptance requires an authored DELTA (materialization).

Bug codex-backlog-author-no-materialization-regression-040: on 0.4.0 the author step
was ACCEPTED with codex_exec while the worker wrote nothing — the deliverable zone
check proved zone-mere-existence (scaffold files satisfy it), and the run only failed
later at ``backlog_review_gate``. The author step's deliverable gate now runs in delta
mode: a file in the zone must be NEW or hash-CHANGED vs the pre-authoring snapshot, or
the step BLOCKs (with the one bounded structural-correction retry).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.backlog.classifier import BoundItem
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    AuthoredItem,
    BacklogDefinitionWorkflow,
    BacklogDemand,
    ProposedIntent,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

pytestmark = pytest.mark.unit

_CONTEXT = "ctx"
_RELEASE = "v0.1.0"
_ANCHOR_A = "pkg/a.py#A"

_ITEM_BODY = """---
slug: new-item
status: OPEN
intents:
  - subject: { kind: code, ref: pkg/a.py#A }
    change: add A
---

# new-item

Authored item body.
"""


def _seed_workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)
    (specs / "bugs").mkdir(parents=True)
    (specs / "audits").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (specs / "memory" / "quality-assurance.md").write_text("# QA\n", encoding="utf-8")
    (specs / "memory" / "product" / "catalog.json").write_text(
        '{"features": []}\n', encoding="utf-8"
    )
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (specs / "releases" / _RELEASE / name).write_text(f"# {name}\n", encoding="utf-8")
    return specs


def _registry(tmp_path: Path, specs: Path) -> Registry:
    root = specs.parent
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("class A:\n    pass\n", encoding="utf-8")
    return build_registry(
        source_root=root,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=tmp_path / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs,
        cli_anchors=frozenset(),
    )


def _demand() -> BacklogDemand:
    return BacklogDemand(
        proposed_intents=(ProposedIntent(kind=SubjectKind.CODE, ref=_ANCHOR_A, change="add A"),),
        existing=(),
        authored=AuthoredItem(
            slug="new-item",
            is_new=True,
            bound=BoundItem(slug="new-item", anchor_changes={_ANCHOR_A: "add A"}),
        ),
    )


class _ScriptedFake:
    """Fake runtime whose backlog_author behavior is scripted per test."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        write_on_attempt: int | None,
        body: str | None = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.write_on_attempt = write_on_attempt
        self.body = body if body is not None else _ITEM_BODY
        self.calls = 0

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def _write_item(self) -> None:
        item = self.workspace_root / "repos" / _CONTEXT / "specs" / "backlog" / "new-item.md"
        item.parent.mkdir(parents=True, exist_ok=True)
        item.write_text(self.body, encoding="utf-8")

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.calls += 1
        step = (request.task_id or "").rsplit(":", 1)[-1]
        if (
            step == "backlog_author"
            and self.write_on_attempt is not None
            and self.calls >= self.write_on_attempt
        ):
            self._write_item()
        allowed = (
            request.allowed_paths[0]
            if request.allowed_paths
            else ".dadaia/tmp/lifecycle-worker/x/**"
        )
        artifact = allowed.replace("**", "step.step-output.json")
        # The phantom-artifact gate requires every referenced path to EXIST under the
        # artifact root — materialize it like a real worker's step-output file.
        artifact_path = self.workspace_root / artifact
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("{}\n", encoding="utf-8")
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="author step ok",
            artifact_refs=(artifact,),
            structured_output={},
            domain_payload={},
        )


def _workflow(tmp_path: Path, fake: _ScriptedFake) -> BacklogDefinitionWorkflow:
    specs = _seed_workspace(tmp_path)
    return BacklogDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=ContextSelector(
            SpecContext(
                specs_dir=specs,
                release_id=_RELEASE,
                handoff_dir=tmp_path / ".dadaia" / "handoff",
            )
        ),
        registry=_registry(tmp_path, specs),
        handoff_resolver=WorkflowHandoffResolver(
            run_store=JsonLifecycleRunStore(tmp_path),
            payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
            clock=lambda: "2026-07-19T12:00:00Z",
        ),
        artifact_root=tmp_path,
    )


def test_no_write_worker_blocks_at_the_author_step(tmp_path: Path) -> None:
    """The 0.4.0 regression: a do-nothing worker must NOT be accepted."""
    fake = _ScriptedFake(tmp_path, write_on_attempt=None)
    result = _workflow(tmp_path, fake).run("bd-mat-1", _demand())

    assert result.completed is False
    author = next(step for step in result.steps if step.label == "backlog_author")
    assert author.accepted is False
    assert result.blocked is not None
    assert "no NEW or CHANGED deliverable" in result.blocked.reason
    # The bounded structural-correction retry fired (initial attempt + one retry).
    assert fake.calls == 2


def test_retry_recovers_when_the_worker_writes_on_the_correction(tmp_path: Path) -> None:
    """The structural retry gives the worker one chance to actually materialize."""
    fake = _ScriptedFake(tmp_path, write_on_attempt=2)
    result = _workflow(tmp_path, fake).run("bd-mat-2", _demand())

    author = next(step for step in result.steps if step.label == "backlog_author")
    assert author.accepted is True
    assert fake.calls == 2


def test_writing_new_item_completes_the_chain(tmp_path: Path) -> None:
    fake = _ScriptedFake(tmp_path, write_on_attempt=1)
    result = _workflow(tmp_path, fake).run("bd-mat-3", _demand())

    assert result.completed is True
    item = tmp_path / "repos" / _CONTEXT / "specs" / "backlog" / "new-item.md"
    assert item.is_file()


def test_editing_an_existing_item_satisfies_the_delta(tmp_path: Path) -> None:
    """An EDIT (same path, changed content) is a valid materialization."""
    fake = _ScriptedFake(tmp_path, write_on_attempt=1)
    wf = _workflow(tmp_path, fake)
    # Seed the pre-existing item after the workspace tree exists but BEFORE run()
    # (the pre-authoring snapshot is captured at run start, not at construction).
    item = tmp_path / "repos" / _CONTEXT / "specs" / "backlog" / "new-item.md"
    item.write_text(_ITEM_BODY.replace("add A", "seed A"), encoding="utf-8")
    result = wf.run("bd-mat-4", _demand())

    author = next(step for step in result.steps if step.label == "backlog_author")
    assert author.accepted is True


#: What a live worker produced on R9/F-26: the block opens and the process stopped before
#: writing the closing delimiter.
_TRUNCATED_ITEM_BODY = """---
name: new-item
status: candidate
intents: []

# BACKLOG — the worker stopped before closing the frontmatter block
"""


def test_a_truncated_item_blocks_at_the_author_step_not_downstream(tmp_path: Path) -> None:
    """Bug r9-f26-author-accepts-unterminated-frontmatter.

    The deliverable gate proves a file APPEARED, never that it is READABLE, so a worker
    that stopped mid-write got its item promoted and the failure resurfaced at
    ``backlog_review_gate`` as "status missing" — a diagnosis that names a consequence
    and drops the worker's trace. Malformed is not-delivered: it must block HERE.
    """
    fake = _ScriptedFake(tmp_path, write_on_attempt=1, body=_TRUNCATED_ITEM_BODY)
    result = _workflow(tmp_path, fake).run("bd-mat-trunc", _demand())

    assert result.completed is False
    assert result.blocked is not None
    assert result.blocked.blocked_at_step == "backlog_author", (
        f"blocked at {result.blocked.blocked_at_step!r} instead of the step that "
        "produced the malformed file"
    )
    assert "unterminated" in result.blocked.reason.lower()
    assert "status" not in result.blocked.reason.lower().split("unterminated")[0]
    assert result.blocked.operator_command, "a block without a remedy is a dead end"
