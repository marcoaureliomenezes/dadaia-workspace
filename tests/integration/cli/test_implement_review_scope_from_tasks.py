"""v0.1.78 T-E / FR-E — implement-review write-scope parity (absorbed backlog
``implement-review-write-scope-from-tasks-parity``).

RED-first proof: the v0.1.68 FR3 ``write_scope_from_tasks`` derivation is wired ONLY at
the ``pipeline`` verb (``dadaia_workspace/cli/commands/lifecycle.py``) — the
``implement-review`` verb builds its ``implement_step`` with no ``extra_allowed_paths`` at
all, so its implement worker under-scopes its legal write surface exactly as ``pipeline``
did pre-v0.1.68. Driving a real ``dadaia lifecycle implement-review`` implement step — with
NO ``--write-scope`` flag — must produce a built request whose ``allowed_paths`` contains
the reserved task's declared ``Write set:`` glob.

The ``--harness fake`` path resolves through ``_implement_review_runtime_factory`` — a
DRIVING fake (always-APPROVED) that never routes through ``container.build_agent_runtime``
for the ``FAKE`` kind (mirrors ``test_implement_review_cli.py``'s ``_RejectingRuntime``
seam) — so this test injects a request-recording runtime at that module-level seam
instead of patching ``container.build_agent_runtime``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import lifecycle as lifecycle_cli
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_CONTEXT = "dadaia-workspace"
_RELEASE = "v0178-fr-e-repro"


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _seed_tasks(workspace: Path, release: str) -> None:
    tasks_dir = workspace / "specs" / "releases" / release
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "TASKS.md").write_text(
        """# TASKS — fixture

### T-fr-e-01 — implement the thing `[-]`
- **Owner:** software-engineer
- **Write set:** `foo/bar.py`
- **Task:** implement the thing.
""",
        encoding="utf-8",
    )


@dataclass
class _RecordingApprovingRuntime:
    """A structurally-valid always-APPROVED worker that records every request it sees —
    mirrors ``test_implement_review_cli.py``'s ``_RejectingRuntime`` shape."""

    kind: AgentRuntimeKind
    received_requests: list[AgentRunRequest] = field(default_factory=list)

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="recording worker: APPROVED",
            artifact_refs=(f".dadaia/handoff/{_CONTEXT}/impl.handoff.json",),
            structured_output={"verdict": "APPROVED"},
        )


def _install_recording_factory(monkeypatch: pytest.MonkeyPatch) -> _RecordingApprovingRuntime:
    recorder = _RecordingApprovingRuntime(AgentRuntimeKind.FAKE)

    def _factory(workspace_root: Path, *, context: str) -> object:
        return lambda kind: recorder

    monkeypatch.setattr(lifecycle_cli, "_implement_review_runtime_factory", _factory)
    return recorder


def test_implement_review_scope_derived_from_tasks_with_no_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC (parity): with NO ``--write-scope`` flag, ``implement-review``'s implement step
    must derive the reserved task's Write-set globs — exactly like ``pipeline`` does."""
    workspace = _init_workspace(tmp_path)
    _seed_tasks(workspace, _RELEASE)
    recorder = _install_recording_factory(monkeypatch)
    monkeypatch.chdir(workspace)

    _runner.invoke(
        app,
        [
            "lifecycle",
            "implement-review",
            "--skip-preflight",
            "--release-id",
            _RELEASE,
            "--run-id",
            "impl-review-fr-e-repro",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert recorder.received_requests, "the recording implement worker must have been invoked"
    implement_request = recorder.received_requests[0]
    assert "foo/bar.py" in implement_request.allowed_paths, (
        "the implement-review implement step's allowed_paths must include the "
        f"TASKS.md-derived write set even with no --write-scope flag; got "
        f"{implement_request.allowed_paths!r}"
    )


def test_implement_review_write_scope_flag_is_additive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--write-scope`` is an additive escape hatch: an extra glob unions with the
    TASKS.md-derived scope, it never replaces it."""
    workspace = _init_workspace(tmp_path)
    _seed_tasks(workspace, _RELEASE)
    recorder = _install_recording_factory(monkeypatch)
    monkeypatch.chdir(workspace)

    _runner.invoke(
        app,
        [
            "lifecycle",
            "implement-review",
            "--skip-preflight",
            "--release-id",
            _RELEASE,
            "--run-id",
            "impl-review-fr-e-flag",
            "--harness",
            "fake",
            "--write-scope",
            "extra/glob.py",
            "--json",
        ],
    )

    assert recorder.received_requests
    implement_request = recorder.received_requests[0]
    assert "foo/bar.py" in implement_request.allowed_paths
    assert "extra/glob.py" in implement_request.allowed_paths


def test_implement_review_review_step_never_widened(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The review step must stay handoff-only — the TASKS.md-derived write scope (and any
    ``--write-scope`` extra) applies to the implement step ONLY, never the review step."""
    workspace = _init_workspace(tmp_path)
    _seed_tasks(workspace, _RELEASE)
    recorder = _install_recording_factory(monkeypatch)
    monkeypatch.chdir(workspace)

    _runner.invoke(
        app,
        [
            "lifecycle",
            "implement-review",
            "--skip-preflight",
            "--release-id",
            _RELEASE,
            "--run-id",
            "impl-review-fr-e-review-scope",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert len(recorder.received_requests) >= 2
    review_request = recorder.received_requests[1]
    assert "foo/bar.py" not in review_request.allowed_paths
    assert all(
        path.startswith(f".dadaia/handoff/{_CONTEXT}/") for path in review_request.allowed_paths
    )
