"""v0.1.78 T-D / FR-D — worker-noncompliance diagnostic evidence, executed-path
(bug ``worker-noncompliance-block-carries-no-diagnostic-evidence``).

Drives ``dadaia lifecycle pipeline`` end-to-end with a noncompliant fake implement
worker (empty ``artifact_refs`` + an attached ``WorkerDiagnostic``) and asserts the CLI's
``blocked`` payload carries a ``diagnostic_ref`` pointing at a real, readable, redacted
run-scoped diagnostic file — never a silent evidence-free block.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    WorkerDiagnostic,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.78"


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


class _NoncompliantRuntime:
    """A worker that always returns a SUCCEEDED-but-empty-refs result carrying a
    WorkerDiagnostic — the exact remote-bug shape (PI/kimi malformed prose)."""

    def __init__(self, kind: AgentRuntimeKind) -> None:
        self._kind = kind
        self.received_requests: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return self._kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="pi headless completed",
            artifact_refs=(),
            diagnostic=WorkerDiagnostic(
                runtime="pi_headless",
                model="gpt-5.3-codex",
                requested_reasoning="high",
                actual_reasoning=None,
                exit_code=0,
                parser_classification="no-artifact-refs",
                output_tail="unrelated malformed prose, secret=[REDACTED]",
                session_ref="pi-session-xyz",
            ),
        )


def test_pipeline_blocked_by_noncompliant_worker_carries_diagnostic_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace_root)
    monkeypatch.setenv(
        "DADAIA_CONTEXT", "dadaia-workspace"
    )  # explicit rung (no first-ALIVE/terminal fallback)

    noncompliant = _NoncompliantRuntime(AgentRuntimeKind.FAKE)

    def fake_build(
        kind: AgentRuntimeKind, *, cwd: Path | None = None, model: object = None
    ) -> AgentRuntimePort:
        return noncompliant

    monkeypatch.setattr(container, "build_agent_runtime", fake_build)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implementation-reviews",
            "--skip-preflight",
            "--release-id",
            _RELEASE,
            "--run-id",
            "diag-repro",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output  # BLOCKED
    payload = json.loads(result.stdout)
    assert payload["completed"] is False
    blocked = payload["blocked"]
    assert blocked is not None
    assert blocked["reason"] == "agent result missing artifact evidence"
    diagnostic_ref = blocked["detail"].get("diagnostic_ref")
    assert diagnostic_ref, f"blocked.detail must carry diagnostic_ref; got {blocked['detail']!r}"

    persisted_path = workspace_root / diagnostic_ref
    assert persisted_path.is_file(), f"diagnostic_ref must reference a real file: {persisted_path}"
    diagnostic_payload = json.loads(persisted_path.read_text(encoding="utf-8"))
    assert diagnostic_payload["runtime"] == "pi_headless"
    assert diagnostic_payload["model"] == "gpt-5.3-codex"
    assert diagnostic_payload["requested_reasoning"] == "high"
    assert diagnostic_payload["parser_classification"] == "no-artifact-refs"
    assert diagnostic_payload["session_ref"] == "pi-session-xyz"
    assert "[REDACTED]" in diagnostic_payload["output_tail"]
