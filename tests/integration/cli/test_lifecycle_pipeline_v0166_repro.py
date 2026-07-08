"""Executed-path reproduction tests for release v0.1.66 (Layer-2 Worker Path Remediation).

Every test here is named exactly as SPEC.md's ``AC-N(repro)``/``AC-N(repro-negative)``
criteria specify (traceability by name, not inference). Each drives the REAL production
entrypoint the user actually hit — ``dadaia lifecycle`` via ``CliRunner`` +
``dadaia_workspace.cli.main.app``, invoking the real ``container.build_agent_runtime`` /
``LifecycleAgentRunner`` / ``LifecycleStateMachine`` chain — with only the outermost I/O
boundary faked (the ``subprocess.run`` seam for the pi/codex adapters, or an injected
``FakeAgentRuntime`` result for engine-logic-only FRs). This file is a SIBLING of
``test_lifecycle_pipeline_cli.py`` per PLAN.md's judgment call (avoids waves A/B/C
colliding on one growing file) and follows the exact pattern already proven there
(``test_pipeline_runs_first_step_on_pi_harness_end_to_end``).
"""

from __future__ import annotations

import json
import subprocess as _subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _stub_git_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the Ring-2 git seam hermetic (no real repo in the temp workspace)."""
    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )


# ---------------------------------------------------------------------------
# FR1 (T-66-04) — pi non-zero exit reported as FAILED, not the generic block.
# ---------------------------------------------------------------------------


def test_pi_pipeline_surfaces_real_setup_failure_not_generic_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC1(repro) — bug: pi-headless-nonzero-exit-misreported.

    A faked pi subprocess exits ``returncode=1`` with a non-empty JSONL
    session/event preamble on stdout (no usable ``message_end``) and a real,
    actionable stderr. On current (buggy) code
    ``PiHeadlessAdapter._result_from_output`` treats the non-empty stdout as a
    signal the run "completed" (``returncode != 0 and not text``), so the
    engine reports SUCCEEDED with empty ``artifact_refs`` and the pipeline
    blocks with the generic "agent result missing artifact evidence" message —
    the real setup failure is lost. After the fix, ANY non-zero returncode is
    FAILED and the block reason must carry the real stderr text.
    """
    preamble_stdout = (
        "\n".join(
            [
                json.dumps({"type": "session_start", "session_id": "abc123"}),
                json.dumps({"type": "message_start"}),
            ]
        )
        + "\n"
    )

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        return _subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout=preamble_stdout,
            stderr="No API key found for azure-openai-responses.",
        )

    monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake_pi_run)
    _stub_git_diff(monkeypatch)

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0166-fr1-repro",
            "--run-id",
            "pipe-fr1-repro",
            "--harness",
            "pi",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    assert payload["steps"][0]["runtime"] == "pi_headless"
    block_reason = payload["blocked"]["reason"]
    # The precise upstream reason must reach the operator — NOT the flattened generic
    # "agent result missing artifact evidence" message.
    assert "No API key found" in block_reason
    assert block_reason != "agent result missing artifact evidence"
