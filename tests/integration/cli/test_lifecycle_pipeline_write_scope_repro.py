"""T-66-08 (FR7) — AC7(repro): the implement step's write scope covers the reserved
task's production path when the operator supplies ``--write-scope``.

Drives the real ``dadaia lifecycle pipeline`` CLI (via ``CliRunner`` + ``main.app``)
through the real engine (``container.build_agent_runtime`` → ``LifecyclePipeline`` →
``LifecycleAgentRunner`` → ``LifecycleStateMachine``), with only the outermost
``container.build_agent_runtime`` factory faked to inject a ``FakeAgentRuntime`` result
downstream of the adapter boundary — the exact seam ``test_lifecycle_pipeline_full.py``
uses for FR6/FR7-class engine-logic tests (PLAN.md's documented pattern).

On current code, ``LifecyclePipeline._scope`` hardcodes ``allowed_paths`` to the
handoff-dir glob for every step, so an implement worker whose result reports a changed
production path is rejected by the out-of-scope gate — even though no
``--write-scope`` option exists yet to widen it. After the fix, ``--write-scope``
reaches ``PipelineStep.extra_allowed_paths`` for the ``implement`` step only, and the
same changed path is accepted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.features.lifecycle.prompt_builder import canonical_worker_output_ref
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_CONTEXT = "dadaia-workspace"
_PRODUCTION_PATH = "repos/sample-consumer/docker/sample-capture/Dockerfile"


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _implement_result_with_production_change() -> AgentRunResult:
    """A worker result whose ``changed_paths`` includes a production file path, plus a
    valid in-scope handoff artifact_ref (the create-step gate requires ``artifact_refs``
    to be non-empty regardless of the write-scope union under test)."""
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake runtime: implement wrote a production file",
        artifact_refs=(
            canonical_worker_output_ref(_CONTEXT, "pipe-write-scope:implement:attempt-0"),
        ),
        structured_output={"changed_paths": _PRODUCTION_PATH},
    )


def _inject_fake_implement_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fake ONLY the outermost ``container.build_agent_runtime`` factory seam — every
    other step in the ladder (which this test never reaches, since implement blocks or
    the run stops there) would fall through to the real factory untouched."""
    real_build = container.build_agent_runtime

    def fake_build(
        kind: AgentRuntimeKind, *, cwd: Path | None = None, model: object = None
    ) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            # Gate verifies declared refs EXIST (bug gate-accepts-phantom-artifact-evidence).
            return FakeAgentRuntime(
                result=_implement_result_with_production_change(),
                materialize_root=cwd or Path.cwd(),
            )
        return real_build(kind, cwd=cwd)

    monkeypatch.setattr(container, "build_agent_runtime", fake_build)


def test_implement_pipeline_write_scope_covers_reserved_task_production_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC7(repro): FAILS on current code (out-of-scope block on the current-code CLI
    invocation lacking ``--write-scope``), PASSES once ``--write-scope`` reaches
    ``allowed_paths`` for the implement step."""
    import json as _json

    _inject_fake_implement_result(monkeypatch)
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv(
        "DADAIA_CONTEXT", "dadaia-workspace"
    )  # explicit rung (no first-ALIVE/terminal fallback)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implementation-reviews",
            "--skip-preflight",
            "--release-id",
            "v0.1.16",
            "--run-id",
            "pipe-write-scope",
            "--harness",
            "fake",
            "--write-scope",
            "repos/sample-consumer/docker/sample-capture/**",
            "--json",
        ],
    )

    payload = _json.loads(result.output)
    # The implement step must be ACCEPTED (in-scope) once --write-scope reaches the gate.
    assert payload["steps"][0]["label"] == "implement"
    assert payload["steps"][0]["accepted"] is True, payload
    # Never converts a genuine out-of-scope block into anything other than the honest
    # accept — the run advances past implement (blocks later at review_qa on the fake's
    # missing APPROVED verdict, which is a SEPARATE gate, not the write-scope gate under
    # test here).
    assert payload["blocked"] is None or payload["blocked"]["reason"] != (
        "agent result contains out-of-scope paths"
    )


def test_implement_pipeline_without_write_scope_still_blocks_out_of_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression guard: omitting --write-scope keeps today's handoff-only behavior — a
    production-path change is still rejected as out-of-scope. Proves the fix is
    additive-optional, never a default widening."""
    import json as _json

    _inject_fake_implement_result(monkeypatch)
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv(
        "DADAIA_CONTEXT", "dadaia-workspace"
    )  # explicit rung (no first-ALIVE/terminal fallback)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implementation-reviews",
            "--skip-preflight",
            "--release-id",
            "v0.1.16",
            "--run-id",
            "pipe-no-write-scope",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = _json.loads(result.output)
    assert payload["steps"][0]["label"] == "implement"
    assert payload["steps"][0]["accepted"] is False
    assert payload["blocked"]["reason"] == "agent result contains out-of-scope paths"
    assert _PRODUCTION_PATH in payload["blocked"]["detail"]["out_of_scope"]
