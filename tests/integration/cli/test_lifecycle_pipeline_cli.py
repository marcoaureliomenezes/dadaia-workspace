"""Integration proof: `dadaia lifecycle pipeline` runs the multi-step engine end-to-end."""

from __future__ import annotations

import json
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


def test_pipeline_runs_engine_and_blocks_at_first_step_on_fake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-it",
            "--harness",
            "fake",
            "--step-harness",
            "review_qa=codex",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    # First step ran the engine on the fake harness and blocked on the missing verdict.
    assert payload["steps"][0]["label"] == "implement"
    assert payload["steps"][0]["runtime"] == "fake"
    assert payload["steps"][0]["accepted"] is False
    # The per-step override was accepted by the CLI (parsing path exercised).
    assert payload["blocked"]["reason"]


def test_pipeline_runs_first_step_on_pi_harness_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Layer-2 e2e: `--harness pi` resolves through the CLI to a real
    ``PiHeadlessAdapter`` built by ``container.build_agent_runtime``, which parses a
    genuine ``pi --mode json`` event stream. Only the ``pi`` subprocess and the git
    seam are faked — no real binary, no network, no credits. The engine must record
    the step runtime as ``pi_headless`` and block on the missing verdict (proving the
    PI worker actually ran and its output flowed through the gate)."""
    import subprocess as _subprocess

    # A genuine line-delimited pi --mode json stream whose terminal assistant message
    # carries plain text (no APPROVED verdict) -> the implement gate blocks.
    events = [
        {"type": "message_start"},
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": "implementation step executed via injected pi stream",
            },
        },
    ]
    stdout = "\n".join(json.dumps(event) for event in events) + "\n"

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        return _subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake_pi_run)
    # Keep the Ring-2 git seam hermetic (no real repo in the temp workspace).
    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-pi",
            "--harness",
            "pi",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    # The CLI resolved `--harness pi` -> PI_HEADLESS -> PiHeadlessAdapter, which ran
    # the injected stream; the engine recorded the worker runtime as pi_headless.
    assert payload["steps"][0]["label"] == "implement"
    assert payload["steps"][0]["runtime"] == "pi_headless"
    assert payload["steps"][0]["accepted"] is False
    assert payload["blocked"]["reason"]
