"""v0.2.9 follow-up — bug fake-release-definition-leaves-dirty-worktree.

Consumer repro: a successful fake release-definition left ACTIVE.md, the backlog entry,
SPEC.md, PLAN.md and TASKS.md UNCOMMITTED, and implementation-reviews then blocked at
preflight on the dirty tree. The completed definition now commits the context repo's
definition artifacts (Python-owned, best-effort — mirroring the closure commit).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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

pytestmark = pytest.mark.unit

_CONTEXT = "ctx"
_RELEASE = "v0.1.0"


def _approved() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="ok",
        artifact_refs=(f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json",),
        structured_output={"verdict": "APPROVED"},
    )


class _ApprovedFake:
    def __init__(self, kind: AgentRuntimeKind) -> None:
        self.kind = kind

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return _approved()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


def _seed_git_context(tmp_path: Path) -> Path:
    repo = tmp_path / "repos" / _CONTEXT
    specs = repo / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text("# constitution\n", encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text("# architecture\n", encoding="utf-8")
    (specs / "memory" / "quality-assurance.md").write_text("# qa\n", encoding="utf-8")
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    (specs / "releases" / _RELEASE / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    (specs / "releases" / _RELEASE / "PLAN.md").write_text(
        "# plan\n\n## Validation Dependency Table\n\n"
        "| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |\n"
        "|---|---|---|---|---|\n"
        "| WS-1 | value | unit tests | None | None |\n",
        encoding="utf-8",
    )
    (specs / "releases" / _RELEASE / "TASKS.md").write_text("# tasks\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "seed")
    return repo


def test_completed_fake_definition_commits_the_definition_tree(tmp_path: Path) -> None:
    repo = _seed_git_context(tmp_path)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)

    from dadaia_workspace.container import _definition_committer

    specs = repo / "specs"
    wf = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ApprovedFake(kind),  # type: ignore[arg-type,return-value]
        context_selector=ContextSelector(
            SpecContext(
                specs_dir=specs,
                release_id=_RELEASE,
                handoff_dir=tmp_path / ".dadaia" / "handoff",
            )
        ),
        handoff_resolver=WorkflowHandoffResolver(
            run_store=JsonLifecycleRunStore(tmp_path),
            payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
            clock=lambda: "2026-07-20T12:00:00Z",
        ),
        definition_committer=_definition_committer(repo, _RELEASE),
    )

    result = wf.run("rd-git-clean")

    assert result.completed is True
    # The definition artifacts (SPEC/PLAN/TASKS/ACTIVE.md/backlog) are COMMITTED —
    # implementation preflight inherits a clean tree.
    assert _git(repo, "status", "--porcelain") == ""
    log = _git(repo, "log", "--oneline", "-2")
    assert "definition(v0.1.0): approved release definition artifacts" in log


def test_missing_committer_keeps_fixture_behavior(tmp_path: Path) -> None:
    """No committer wired (fixtures): completion succeeds, nothing is committed."""
    repo = _seed_git_context(tmp_path)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    specs = repo / "specs"
    wf = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ApprovedFake(kind),  # type: ignore[arg-type,return-value]
        context_selector=ContextSelector(
            SpecContext(
                specs_dir=specs,
                release_id=_RELEASE,
                handoff_dir=tmp_path / ".dadaia" / "handoff",
            )
        ),
    )
    assert wf.run("rd-git-nocommit").completed is True
