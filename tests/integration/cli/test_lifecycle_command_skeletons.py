"""Integration tests for guarded lifecycle skeleton commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _payload(output: str) -> dict[str, object]:
    payload = json.loads(output)
    assert isinstance(payload, dict)
    return payload


@pytest.mark.parametrize(
    ("command", "expected_phase"),
    (
        (["lifecycle", "implement"], "qa_review"),
        (["lifecycle", "review", "qa"], "qa_review"),
        (["lifecycle", "review", "security"], "security_review"),
        (["lifecycle", "review", "code"], "code_review"),
    ),
)
def test_review_phase_verbs_advance_on_fake_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
    expected_phase: str,
) -> None:
    """Review-phase single-step verbs drive the engine and pass on FAKE.

    The deterministic FAKE runtime materializes an in-scope review handoff with
    ``verdict=APPROVED`` when the prompt is explicitly a review step. That keeps CLI smoke
    reviewable without live providers while still exercising the real typed gate.
    """
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [*command, "--release-id", "multiharness-engine-v0116", "--harness", "fake", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = _payload(result.output)
    assert payload["status"] == "OK"
    assert payload["runtime"] == "fake"
    assert payload["accepted"] is True
    assert payload["phase"] == expected_phase
    assert payload["blocked"] is None


def test_close_on_fake_emits_closure_artifact_and_advances(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAKE close writes a closure artifact so the create-step evidence gate passes (v0.1.42).

    Regression for bug ``lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence``:
    the FAKE closure runtime now emits a deterministic closure handoff, so
    ``lifecycle close --harness fake`` advances instead of blocking on
    "agent result missing artifact evidence".
    """
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "close",
            "--release-id",
            "multiharness-engine-v0116",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = _payload(result.output)
    assert payload["status"] == "OK"
    assert payload["runtime"] == "fake"
    assert payload["accepted"] is True
    assert payload["phase"] == "closure"
    assert payload["blocked"] is None


def test_release_define_runs_fragment_driven_sequence_on_fake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`release define` runs the §6.1 fragment-driven sequence end-to-end on FAKE (T-24-09).

    Unlike the generic single-step verbs, the release-definition verb composes
    fragment-assembled, scoped prompts with Python-owned gates; the driving FAKE adapter
    approves each step so the sequence reaches the terminal Python ``definition_commit_gate``
    and advances the release to IMPLEMENTATION.
    """
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "release",
            "define",
            "--release-id",
            "multiharness-engine-v0116",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = _payload(result.output)
    assert payload["status"] == "OK"
    assert payload["completed"] is True
    assert payload["final_phase"] == "implementation"
    steps = payload["steps"]
    assert isinstance(steps, list)
    labels = [step["label"] for step in steps]
    assert labels[-1] == "definition_commit_gate"
    # Fragment-driven: each model step carries a fragment id (not a generic step).
    assert steps[0]["fragment_id"] == "release_definition.release_scope"


def test_resume_existing_run_returns_ok_next_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    JsonLifecycleRunStore(workspace).save(
        LifecycleRun(
            run_id="run-ok",
            context="dadaia-workspace",
            release_id="v0.1.15",
            command="implement",
            phase=LifecyclePhase.IMPLEMENTATION,
            status=LifecycleRunStatus.BLOCKED,
            current_step="preflight",
            expected_artifacts=(),
            idempotency_key="idem-run-ok",
        )
    )
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "resume", "run-ok"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "OK resumed run-ok"


def test_phase_step_prompt_is_step_kind_aware() -> None:
    """The CLI single-step worker prompt (the THIRD prompt surface) is review/create aware.

    v0.1.32 D-2/L1: a review-phase verb is told to emit a verdict; a create verb is NOT
    (instructing a create step to self-verdict is the Drift-1 incoherence this release
    eliminated on the other two surfaces). Guards the entry point for
    ``dadaia lifecycle implement``/``close`` against re-introducing the universal-self-verdict
    text.
    """
    from dadaia_workspace.cli.commands.lifecycle import _phase_step_prompt
    from dadaia_workspace.core.models.lifecycle import LifecyclePhase

    review = _phase_step_prompt(
        "review qa",
        "v0.1.99",
        "ctx",
        LifecyclePhase.QA_REVIEW,
        artifact_dir="specs/releases/v0.1.99/alpha-1",
    )
    create = _phase_step_prompt(
        "implement",
        "v0.1.99",
        "ctx",
        LifecyclePhase.IMPLEMENTATION,
    )
    close = _phase_step_prompt("close", "v0.1.99", "ctx", LifecyclePhase.CLOSURE)

    assert "verdict is APPROVED or REJECTED" in review
    assert "Do not self-verdict" not in review
    assert "specs/releases/v0.1.99/alpha-1" in review
    for prompt in (create, close):
        assert "Do not self-verdict" in prompt
        assert "is APPROVED or REJECTED" not in prompt


def test_release_artifact_dir_hint_uses_active_segment(tmp_path: Path) -> None:
    from dadaia_workspace.cli.commands.lifecycle import _release_artifact_dir_hint

    specs = tmp_path / "repos" / "ctx" / "specs" / "releases"
    specs.mkdir(parents=True)
    (specs / "ACTIVE.md").write_text(
        "release: v0.1.99\nsegment: alpha-1\nphase: IMPLEMENTATION\n",
        encoding="utf-8",
    )

    assert (
        _release_artifact_dir_hint(tmp_path, context="ctx", release_id="v0.1.99")
        == "specs/releases/v0.1.99/alpha-1"
    )
    assert (
        _release_artifact_dir_hint(tmp_path, context="ctx", release_id="v0.2.0")
        == "specs/releases/v0.2.0"
    )
