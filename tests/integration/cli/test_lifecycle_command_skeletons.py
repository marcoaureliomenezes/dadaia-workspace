"""Integration tests for guarded lifecycle skeleton commands.

Merged per plan-integration.md (5 -> 1): kept the parametrized every-verb-runs-the-engine
block matrix (the single "every verb runs the engine" proof) with the non-traceback
assert (from the former close-actionable smoke, itself a duplicate matrix row) folded
in as an extra check on every row. Deleted: close-actionable smoke (dup of the close
row), release-define fake e2e (dup of test_release_definition_workflow.py's baseline),
resume-ok (folded into test_lifecycle_cli.py's exit matrix), `_phase_step_prompt`
step-kind (relocated to tests/unit/cli/commands/test_lifecycle_phase_step_prompt.py —
direct function call, no fs/subprocess).
"""

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
    ``BlockedState``, never an ``unavailable_workflow`` stub — and never a crash/traceback
    (W1-11 / T-47-20 grill D-10 smoke folded in, exercised on every row via ``close`` and
    every other verb identically). (``release define`` and ``backlog define`` are the
    fragment-driven multi-step workflows — covered separately.)
    """
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [*command, "--release-id", "multiharness-engine-v0116", "--harness", "fake", "--json"],
    )

    assert result.exit_code == 3, result.output
    # No Python traceback leaked to the operator — the failure is gate-mediated, not an error.
    assert "Traceback (most recent call last)" not in result.output
    payload = _payload(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["runtime"] == "fake"
    assert payload["accepted"] is False
    blocked = payload["blocked"]
    assert isinstance(blocked, dict)
    assert blocked["reason"] == expected_reason
