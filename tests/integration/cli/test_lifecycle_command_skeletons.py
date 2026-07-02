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
    ("command", "expected_reason"),
    (
        # Review-phase verbs (target QA/SECURITY/CODE_REVIEW) run as REVIEW steps under the
        # v0.1.31 review-only gate: the bare FAKE worker emits no verdict → block on the
        # verdict requirement. ``implement`` targets QA_REVIEW, so it is a review step too.
        (["lifecycle", "implement"], "agent result missing APPROVED verdict"),
        (["lifecycle", "review", "qa"], "agent result missing APPROVED verdict"),
        (["lifecycle", "review", "security"], "agent result missing APPROVED verdict"),
        (["lifecycle", "review", "code"], "agent result missing APPROVED verdict"),
        # ``close`` targets CLOSURE — a NON-review (create) phase. Under the review-only
        # gate it is no longer verdict-gated; the bare FAKE worker yields empty
        # ``artifact_refs``, so it blocks on the still-active artifact-evidence check
        # instead. The block proves the engine path ran — just not via the verdict gate.
        (["lifecycle", "close"], "agent result missing artifact evidence"),
    ),
)
def test_every_phase_verb_runs_the_engine_and_blocks_on_fake_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
    expected_reason: str,
) -> None:
    """Every generic single-step lifecycle verb drives the engine (no `unavailable_workflow`).

    With the FAKE harness the bare worker emits neither an APPROVED verdict nor artifact
    evidence, so the real typed gate blocks every verb — proving the engine path executed
    end-to-end on a selectable harness. Under the v0.1.31 **review-only** gate the *reason*
    differs by step kind: a review-phase verb (implement, review qa/security/code) blocks on
    the verdict requirement, while a create-phase verb (close → CLOSURE) is not verdict-gated
    and blocks on the artifact-evidence check instead. Either way it is a real engine
    ``BlockedState``, never an ``unavailable_workflow`` stub. (``release define`` and
    ``backlog define`` are the fragment-driven multi-step workflows — covered separately.)
    """
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [*command, "--release-id", "multiharness-engine-v0116", "--harness", "fake", "--json"],
    )

    assert result.exit_code == 3, result.output
    payload = _payload(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["runtime"] == "fake"
    assert payload["accepted"] is False
    blocked = payload["blocked"]
    assert isinstance(blocked, dict)
    assert blocked["reason"] == expected_reason


def test_close_fake_harness_fails_actionably_not_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W1-11 (T-47-20, grill D-10) smoke: `lifecycle close --harness fake` fails actionably.

    Recorded behavior: `close` targets CLOSURE (a create step). The bare FAKE worker emits no
    artifact evidence, so the typed create-step gate holds and the CLI exits with the
    documented BLOCKED code (3) — NOT a crash/traceback and NOT a silent no-op. The block
    carries a human-readable reason naming the missing evidence, so the outcome is actionable
    (the operator sees exactly why the step held). This is the intended create-step gate
    contract, already codified in
    ``test_every_phase_verb_runs_the_engine_and_blocks_on_fake_harness`` — the D-10 concern of
    an *unactionable* block is NOT reproducible, so no production fix is warranted.
    """
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        ["lifecycle", "close", "--release-id", "multiharness-engine-v0116", "--harness", "fake"],
    )

    # Documented BLOCKED exit code — a clean typed failure, never a crash (1/2) or success (0).
    assert result.exit_code == 3, result.output
    # No Python traceback leaked to the operator — the failure is gate-mediated, not an error.
    assert "Traceback (most recent call last)" not in result.output
    # The human-facing line names the blocked verb + harness + phase (actionable orientation).
    assert "BLOCKED close" in result.output
    assert "harness=fake" in result.output

    # And the --json surface carries the actionable reason string.
    json_result = _runner.invoke(
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
    assert json_result.exit_code == 3, json_result.output
    payload = _payload(json_result.output)
    assert payload["accepted"] is False
    assert payload["blocked"]["reason"] == "agent result missing artifact evidence"


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

    review = _phase_step_prompt("review qa", "v0.1.99", "ctx", LifecyclePhase.QA_REVIEW)
    create = _phase_step_prompt("implement", "v0.1.99", "ctx", LifecyclePhase.IMPLEMENTATION)
    close = _phase_step_prompt("close", "v0.1.99", "ctx", LifecyclePhase.CLOSURE)

    assert "verdict is APPROVED or REJECTED" in review
    assert "Do not self-verdict" not in review
    for prompt in (create, close):
        assert "Do not self-verdict" in prompt
        assert "is APPROVED or REJECTED" not in prompt
