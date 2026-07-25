"""A prescribed remedy must advance the run — no gate/author contradiction loop.

Bug backlog-resume-contradiction-loop-after-fixing-a-preexisting-item.

A backlog-definition run blocks at ``backlog_review_gate`` because a PRE-EXISTING item —
one the gate itself reports as NOT written by this run — is invalid. Its prescribed
``operator_command`` says to resume from ``backlog_author``. The operator fixes exactly
that item and runs the command verbatim, and:

* the author step blocked with "no NEW or CHANGED deliverable", ``operator_command`` NULL —
  a dead end;
* resuming the gate instead blocked with "no new/changed item found", prescribing the
  author resume that had just failed.

The two remedies pointed at each other and the run could never finish. Root cause: both
checks asked "did this ATTEMPT write something new?" when the correct question on a resume
is "did this RUN deliver?" — the run's item was already on disk from its first attempt, and
what had been broken was someone else's item, which the operator had already fixed.

The guard the delta mode exists for is unchanged and asserted here too: a run that never
authored anything carries no exemption at all
(bug codex-backlog-author-no-materialization-regression-040).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.fixtures.harness_env import claude_hook_env

pytestmark = pytest.mark.integration

_CONTEXT = "loopctx"
_RELEASE = "v0.1.0"
_TIMEOUT = 180


def _dadaia(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", *args],
        cwd=workspace,
        env=claude_hook_env(workspace, extra={"DADAIA_CONTEXT": _CONTEXT}),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(root)
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, timeout=_TIMEOUT)
    created = _dadaia(root, "context", "create", _CONTEXT, "--repo", _CONTEXT, "--url", str(remote))
    assert created.returncode == 0, created.stdout + created.stderr
    alive = _dadaia(root, "context", "alive", _CONTEXT)
    assert alive.returncode == 0, alive.stdout + alive.stderr
    return root


def _backlog_dir(workspace: Path) -> Path:
    return workspace / "repos" / _CONTEXT / "specs" / "backlog"


def _define(workspace: Path, *extra: str) -> tuple[int, dict]:
    proc = _dadaia(
        workspace,
        "lifecycle",
        "backlog-definition",
        "--context",
        _CONTEXT,
        "--release-id",
        _RELEASE,
        "--run-id",
        "loop-run",
        "--harness",
        "fake",
        "--demand",
        "probe",
        "--json",
        *extra,
    )
    return proc.returncode, json.loads(proc.stdout or "{}")


def test_prescribed_remedy_completes_after_fixing_a_preexisting_item(workspace: Path) -> None:
    bad = _backlog_dir(workspace) / "preexisting-bad.md"
    bad.write_text("---\nstatus: candidate\n---\n\n# no intents\n", encoding="utf-8")

    code, blocked = _define(workspace)
    assert code != 0, blocked
    remedy = (blocked.get("blocked") or {}).get("operator_command")
    assert remedy and "--resume-from backlog_author" in remedy, blocked

    # Do exactly what the block's reason instructs, then run its remedy verbatim.
    bad.write_text("---\nstatus: idea\n---\n\n# an unbound brainstorm\n", encoding="utf-8")
    code, payload = _define(workspace, "--resume-from", "backlog_author")

    assert code == 0, payload
    assert payload["completed"] is True, payload
    # The run's deliverable from its FIRST attempt is what satisfied the gate.
    assert any(
        p.stem.startswith("dadaia-fake-harness-canary")
        for p in _backlog_dir(workspace).glob("*.md")
    )


def test_a_fresh_run_carries_no_authored_path_exemption(workspace: Path) -> None:
    """The guard the delta mode exists for must survive the fix.

    Without this, "stop demanding a fresh delta on resume" could quietly become "stop
    demanding a deliverable at all", and a worker that materializes nothing would sail
    through — the exact regression the delta mode was added to catch.
    """
    from dadaia_workspace import container

    workflow = container.build_backlog_definition_workflow(
        workspace, context=_CONTEXT, release_id=_RELEASE
    )
    assert workflow._resumed_authored_paths == ()


def test_prescribed_remedy_preserves_the_runs_own_harness(workspace: Path) -> None:
    """Bug r6h-backlog-remedy-command-loses-fake-harness (validator-reported).

    The prescribed command carried no ``--harness``, so pasting it literally fell back to
    ``auto`` — which in a real validation environment resolves to Codex. The remedy then
    resumed the run on a DIFFERENT runtime than the one that created it and re-blocked on
    a conflict with what the first attempt had authored. A remedy that only works if the
    operator silently re-adds a flag is not a remedy.
    """
    bad = _backlog_dir(workspace) / "preexisting-bad.md"
    bad.write_text("---\nstatus: candidate\n---\n\n# no intents\n", encoding="utf-8")

    _code, blocked = _define(workspace)
    remedy = (blocked.get("blocked") or {}).get("operator_command") or ""

    assert "--harness fake" in remedy, (
        "the prescribed command must reproduce the run's own invocation, including the "
        f"harness it ran with; got: {remedy!r}"
    )


def test_first_attempt_with_a_non_writing_worker_still_blocks(workspace: Path) -> None:
    """The delta guard must not have been weakened by the resume fix.

    Relaxing "demand a fresh delta" on RESUME must not become "stop demanding a
    deliverable at all". A live model cannot be reliably coerced into writing nothing —
    asked to, it writes a file explaining that it wrote nothing — so this asserts the
    guard with a runtime that provably writes nothing
    (bug codex-backlog-author-no-materialization-regression-040).
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import (
        AgentRunRequest,
        AgentRunResult,
        AgentRunStatus,
        AgentRuntimeKind,
    )

    class _NonWritingRuntime:
        def runtime_kind(self) -> AgentRuntimeKind:
            return AgentRuntimeKind.FAKE

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            # Claims success and cites a file that ALREADY existed (the scaffold README),
            # writing nothing itself. That is the precise shape the delta mode exists to
            # catch: a merely non-empty zone must never satisfy the deliverable check.
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="worker claims APPROVED while pointing at a pre-existing file",
                artifact_refs=(f"repos/{_CONTEXT}/specs/backlog/README.md",),
                structured_output={"verdict": "APPROVED"},
            )

    from dataclasses import replace as _replace

    from dadaia_workspace.features.lifecycle.workflows.backlog_definition import _SEQUENCE

    workflow = container.build_backlog_definition_workflow(
        workspace, context=_CONTEXT, release_id=_RELEASE
    )
    workflow._runtime_factory = lambda _kind: _NonWritingRuntime()
    sequence = tuple(_replace(step, runtime_kind=AgentRuntimeKind.FAKE) for step in _SEQUENCE)

    result = workflow.run(run_id="no-write-run", sequence=sequence)

    assert result.blocked is not None, "a worker that writes nothing must BLOCK"
    assert result.blocked.blocked_at_step == "backlog_author", result.blocked
    assert "NEW or CHANGED deliverable" in result.blocked.reason, result.blocked.reason
