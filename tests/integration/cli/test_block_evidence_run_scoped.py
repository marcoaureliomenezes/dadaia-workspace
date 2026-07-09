"""FR1 (v0.1.68) — block evidence must be run-scoped, never a stale cross-run handoff.

RED-first executed-path proof for
``lifecycle-pipeline-selects-stale-unrelated-handoff`` (SPEC AC1(repro)): a fresh
``dadaia lifecycle pipeline`` run whose implement worker returns SUCCEEDED with EMPTY
``artifact_refs`` must not have its BLOCK detail enriched with an unrelated, older
``*-software-engineer-*.handoff.json`` that happens to independently validate. On
current (pre-FR1) code, ``container._build_handoff_lookup`` globs
``.dadaia/handoff/<ctx>/*-{agent}-*.handoff.json`` newest-first keyed ONLY on
``(context, role)`` — no ``run_id``/``step`` — so it surfaces exactly this seeded stale
file. This test drives the REAL CLI (``CliRunner`` + ``dadaia_workspace.cli.main.app``)
through the real ``container.build_lifecycle_pipeline`` -> ``LifecyclePipeline`` ->
``LifecycleAgentRunner`` chain, swapping only the FAKE adapter's injected result (the
documented test seam — no production code patched).
"""

from __future__ import annotations

import json
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
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_CONTEXT = "dadaia-workspace"


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _seed_stale_handoff(workspace: Path) -> Path:
    """Write a genuinely valid, independently-validating handoff from an unrelated task.

    Named to sort newest-first ahead of anything the current run would ever produce
    (ISO-8601 UTC-prefixed convention the emitter uses), matching the ``implement``
    step's role (``software-engineer``) so the role-keyed glob catches it.
    """
    handoff_dir = workspace / ".dadaia" / "handoff" / _CONTEXT
    handoff_dir.mkdir(parents=True, exist_ok=True)
    stale_path = (
        handoff_dir / "2099-01-01T000000Z-software-engineer-unrelated-old-task.handoff.json"
    )
    stale_doc = {
        "schema_version": "handoff-v1.1",
        "agent": "software-engineer",
        "context": _CONTEXT,
        "produced_at": "2099-01-01T00:00:00Z",
        "scope": "an unrelated prior task — NOT this run's evidence",
        "metrics": {},
        "artifact": {"type": "other"},
    }
    stale_path.write_text(json.dumps(stale_doc, indent=2), encoding="utf-8")
    return stale_path


def _no_op_implement_result() -> AgentRunResult:
    """SUCCEEDED but empty ``artifact_refs`` — the genuine no-op-create case FR1 covers."""
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="implement worker produced nothing structured",
        artifact_refs=(),
        structured_output={},
    )


def _inject_no_op_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every FAKE-kind adapter the pipeline builds return the no-op result."""
    real_build = container.build_agent_runtime

    def fake_build(
        kind: AgentRuntimeKind, *, cwd: Path | None = None, model: object = None
    ) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            return FakeAgentRuntime(result=_no_op_implement_result())
        return real_build(kind, cwd=cwd)

    monkeypatch.setattr(container, "build_agent_runtime", fake_build)


def test_block_evidence_is_run_scoped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC1(repro) RED half — T-68-01.

    Seeds a stale, unrelated, independently-validating handoff for the same
    (context, role) pair, then drives a fresh fake-harness pipeline run whose implement
    worker returns SUCCEEDED + empty ``artifact_refs``. The block detail must NEVER
    reference the seeded stale file — on current (pre-FR1) code it does, because the
    role-keyed disk-glob has no run/step identity and blindly returns the newest match.
    """
    workspace = _init_workspace(tmp_path)
    stale_path = _seed_stale_handoff(workspace)
    _inject_no_op_fake(monkeypatch)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0168-fr1-repro",
            "--run-id",
            "pipe-fr1-repro",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    assert payload["blocked"]["reason"] == "agent result missing artifact evidence"

    stale_rel_path = str(stale_path.relative_to(workspace))
    detail = payload["blocked"]["detail"]
    # The precise defect: current code enriches detail with the stale cross-run handoff.
    assert detail.get("validated_handoff_path") != stale_rel_path, (
        f"block detail must NOT surface a stale, unrelated handoff's path — got detail={detail!r}"
    )
