"""v0.1.56 FR1 — every run-a-worker verb is governed by the shared policy resolver.

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
        ["release", "define"],
        "gov-reldef",
        "release_definition",
        "release_scope",
        "release_scope",
    ),
    (
        "backlog-define",
        ["backlog", "define"],
        "gov-bldef",
        "backlog_definition",
        "intake_grill",
        "intake_grill",
    ),
    ("implement", ["implement"], "gov-impl", "implementation", "implement", "implement"),
    ("review-qa", ["review", "qa"], "gov-rqa", "implementation", "review_qa", "review_qa"),
    (
        "review-security",
        ["review", "security"],
        "gov-rsec",
        "implementation",
        "review_security",
        "review_security",
    ),
    (
        "review-code",
        ["review", "code"],
        "gov-rcode",
        "implementation",
        "review_code",
        "review_code",
    ),
    ("close", ["close"], "gov-close", "closure", "close", "close"),
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
) -> None:
    """AC-1 + AC-2(a/b/v): the run-store snapshot is resolver-derived; runtime stayed FAKE."""
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            *subcmd,
            "--release-id",
            _RELEASE,
            "--run-id",
            run_id,
            "--harness",
            "fake",
            "--json",
        ],
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


@pytest.mark.parametrize(
    ("subcmd", "step_model_label"), [(row[1], row[5]) for row in _VERBS], ids=_IDS
)
def test_verb_rejects_raw_step_model(
    workspace: Path, subcmd: list[str], step_model_label: str
) -> None:
    """AC-2(iii): a raw ``--step-model label=<id>:<effort>`` is a D-3 profile-id rejection."""
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            *subcmd,
            "--release-id",
            _RELEASE,
            "--harness",
            "fake",
            "--step-model",
            f"{step_model_label}=gpt-5.5:high",
        ],
    )
    assert result.exit_code != 0
    assert "profile id" in result.output


@pytest.mark.parametrize("subcmd", [row[1] for row in _VERBS], ids=_IDS)
def test_verb_model_flag_is_nonfatal_deprecation(workspace: Path, subcmd: list[str]) -> None:
    """AC-2(iv) / R-QA-1: ``--model`` warns on stderr; the ``--json`` stdout stays parseable.

    Click 8.3 keeps stderr separate from stdout by default (the removed ``mix_stderr=False``),
    so ``result.stderr`` isolates the warning and ``result.stdout`` stays clean JSON.
    """
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            *subcmd,
            "--release-id",
            _RELEASE,
            "--harness",
            "fake",
            "--model",
            "anything:high",
            "--json",
        ],
    )
    assert "--model is deprecated" in result.stderr
    assert "--step-model" in result.stderr
    # The warning is NOT on stdout — the JSON payload parses cleanly.
    json.loads(result.stdout)


def test_release_define_threads_resolved_model_into_request(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-2(c): the built request carries the resolver-derived ``resolved_model``.

    A recording FAKE adapter (via the release-definition factory seam) captures every
    request; the ``release_scope`` request's ``resolved_model.profile_id`` equals the
    resolver's derived profile. Also AC-2(v): the FAKE adapter (not codex/pi) executed.
    """
    recording = FakeAgentRuntime(
        result=AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="recording fake: APPROVED",
            artifact_refs=(f".dadaia/handoff/{_CONTEXT}/release-definition-step.handoff.json",),
            structured_output={"verdict": "APPROVED"},
        )
    )

    def factory_builder(*, context: str, run_cwd: Path) -> object:  # noqa: ARG001
        def factory(kind: AgentRuntimeKind) -> FakeAgentRuntime:
            return recording

        return factory

    monkeypatch.setattr(container, "_release_definition_runtime_factory", factory_builder)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "release",
            "define",
            "--release-id",
            _RELEASE,
            "--run-id",
            "gov-cap",
            "--harness",
            "fake",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output

    assert recording.runtime_kind() is AgentRuntimeKind.FAKE
    assert recording.received_requests, "recording fake never ran"
    first = recording.received_requests[0]
    assert first.resolved_model is not None
    resolver = container.build_workflow_policy_resolver(workspace, context=_CONTEXT)
    expected = resolver.resolve("release_definition", context="default").step("release_scope")
    assert expected is not None
    # NOT ``FAKE == codex``: the request records the governed profile, the adapter stays fake.
    assert first.resolved_model.profile_id == expected.model_profile
