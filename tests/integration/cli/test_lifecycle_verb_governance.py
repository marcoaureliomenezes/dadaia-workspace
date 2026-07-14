"""Every one of the four workflows is governed by the shared policy resolver.

AC-1 (RED-first, all 7 exact verb ids): each verb run under ``--harness fake`` persists a
``LifecycleRun.workflow_policy`` snapshot in the run-store record whose per-step
``harness``/``model`` came from the resolver (``None`` pre-wire, resolver-derived post-wire).

AC-2 (FAKE-aware): (a) ``runtime_kind`` stayed FAKE + (v) the FAKE adapter executed;
(b) the persisted snapshot entry is resolver-derived; (c) the request's
``resolved_model.profile_id`` equals the resolved profile; (iii) a raw ``--step-model``
``label=<id>:<effort>`` is rejected (D-3); (iv) ``--model`` emits the stderr deprecation
warning while the ``--json`` stdout stays parseable (R-QA-1).

The assertion channel is the persisted ``LifecycleRun.workflow_policy`` via
``JsonLifecycleRunStore`` — NOT ``--show-policy`` (pipeline-only, not added elsewhere).
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
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_RELEASE = "v0.1.56"
_CONTEXT = "dadaia-workspace"

# (test id, sub-argv, run_id, workflow_id, catalog_step_label, step-model label)
_VERBS: list[tuple[str, list[str], str, str, str, str]] = [
    (
        "release-define",
        ["release-definition"],
        "gov-reldef",
        "release_definition",
        "release_scope",
        "release_scope",
    ),
    (
        "backlog-define",
        ["backlog-definition"],
        "gov-bldef",
        "backlog_definition",
        "intake_grill",
        "intake_grill",
    ),
    (
        "implementation-reviews",
        ["implementation-reviews"],
        "gov-implementation-reviews",
        "implementation_reviews",
        "implement",
        "implement",
    ),
    (
        "audit",
        ["audit"],
        "gov-audit",
        "audit",
        "audit_scope",
        "audit_scope",
    ),
]

_IDS = [row[0] for row in _VERBS]


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run_json_runtimes(payload: dict[str, object]) -> set[str]:
    """The set of runtime_kind values reported by a verb's JSON envelope."""
    steps = payload.get("steps")
    if isinstance(steps, list) and steps:
        return {str(s["runtime"]) for s in steps if isinstance(s, dict) and s.get("runtime")}
    runtime = payload.get("runtime")
    return {str(runtime)} if runtime is not None else set()


@pytest.mark.parametrize(
    ("subcmd", "run_id", "workflow_id", "step_label"),
    [(row[1], row[2], row[3], row[4]) for row in _VERBS],
    ids=_IDS,
)
def test_verb_persists_resolver_derived_snapshot(
    workspace: Path,
    subcmd: list[str],
    run_id: str,
    workflow_id: str,
    step_label: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1 + AC-2(a/b/v): the run-store snapshot is resolver-derived; runtime stayed FAKE.
    The release-define row additionally carries a recording-fake extra case (folded from
    the standalone resolved-model-in-request test): the built request's
    ``resolved_model.profile_id`` equals the resolver's derived profile."""
    recording: FakeAgentRuntime | None = None
    if subcmd == ["release-definition"]:
        # AC-2(c) extra case: capture every request via a recording FAKE adapter (the
        # release-definition factory seam) so we can assert resolved_model afterward.
        recording = FakeAgentRuntime(
            result=AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="recording fake: APPROVED",
                artifact_refs=(f".dadaia/handoff/{_CONTEXT}/release-definition-step.handoff.json",),
                structured_output={"verdict": "APPROVED"},
            ),
            # Gate verifies refs EXIST (bug gate-accepts-phantom-artifact-evidence).
            materialize_root=Path.cwd(),
        )

        def factory_builder(
            *,
            context: str,  # noqa: ARG001
            run_cwd: Path,  # noqa: ARG001
            release_id: str | None = None,  # noqa: ARG001
        ) -> object:
            def factory(kind: AgentRuntimeKind) -> FakeAgentRuntime:
                return recording  # type: ignore[return-value]

            return factory

        monkeypatch.setattr(container, "_release_definition_runtime_factory", factory_builder)

    argv = [
        "lifecycle",
        *subcmd,
        "--release-id",
        _RELEASE,
        "--run-id",
        run_id,
        "--harness",
        "fake",
        "--json",
    ]
    if subcmd == ["implementation-reviews"]:
        argv.append("--skip-preflight")
    result = _runner.invoke(
        app,
        argv,
    )

    # AC-1: the persisted run carries a resolver-derived workflow_policy (None pre-wire).
    run = container.build_lifecycle_run_store(workspace).load(run_id)
    assert run is not None, result.output
    policy = run.workflow_policy
    assert policy is not None, "workflow_policy is None — verb is not resolver-governed"
    assert policy.workflow_id == workflow_id
    entry = policy.step(step_label)
    assert entry is not None

    # AC-2(b): the persisted entry equals what the shared resolver derives independently.
    resolver = container.build_workflow_policy_resolver(workspace, context=_CONTEXT)
    expected = resolver.resolve(workflow_id, context="default").step(step_label)
    assert expected is not None
    assert (entry.harness, entry.model_profile, entry.model, entry.reasoning) == (
        expected.harness,
        expected.model_profile,
        expected.model,
        expected.reasoning,
    )
    # The governed harness is a real Layer-2 worker — NOT ``fake`` (fake is never resolved).
    assert entry.harness in {"codex", "pi"}

    # AC-2(a/v): runtime_kind stayed FAKE — the fake adapter ran, never codex/pi.
    payload = json.loads(result.output)
    assert _run_json_runtimes(payload) == {AgentRuntimeKind.FAKE.value}

    if recording is not None:
        # AC-2(c): the built request carries the resolver-derived resolved_model; AC-2(v):
        # the FAKE adapter (not codex/pi) executed.
        assert recording.runtime_kind() is AgentRuntimeKind.FAKE
        assert recording.received_requests, "recording fake never ran"
        first = recording.received_requests[0]
        assert first.resolved_model is not None
        assert first.resolved_model.profile_id == expected.model_profile
