"""v0.1.56 FR2 — audit / research / bug_report are invocable, born resolver-governed verbs.

AC-3: each of ``dadaia lifecycle audit|research|bug_report`` runs end-to-end under
``--harness fake`` to COMPLETED (exit 0), leaves a resolver-derived
``LifecycleRun.workflow_policy`` snapshot in the run-store record (extends the W1 AC-1
pattern to the three verbs), and appears as a registered CLI verb; the governed catalog
reports the three wired workflows AVAILABLE and all 7 workflows now invocable.

The ``bug_report`` ADDITIVE/no-lease property is asserted **structurally** — the verb's real
``bug_write`` target is the ADDITIVE ``specs/bugs/`` path class, so the verb routes through no
MUTATING/lease-acquiring path by construction. Under ``--harness fake`` "no lease" is vacuous
(the fake writes nothing), so it is NOT framed as a fake-run lease observation.

The snapshot assertion channel is the persisted ``LifecycleRun.workflow_policy`` via
``JsonLifecycleRunStore`` — NOT ``--show-policy`` (pipeline-only, not added elsewhere).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.commands.lifecycle import app as lifecycle_app
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.features.workflows.dadaia_catalog import (
    AVAILABILITY_AVAILABLE,
    governed_workflow_catalog,
    list_dadaia_workflows,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_RELEASE = "v0.1.56"
_CONTEXT = "dadaia-workspace"

# (test id, verb argv, run_id, workflow_id, a resolver-governed model-step label)
_WIRE_VERBS: list[tuple[str, str, str, str, str]] = [
    ("audit", "audit", "fr2-audit", "audit", "audit_scope"),
    ("research", "research", "fr2-research", "research", "research_scope"),
    ("bug_report", "bug_report", "fr2-bug", "bug_report", "bug_intake"),
]
_IDS = [row[0] for row in _WIRE_VERBS]

#: The 7 governed workflows and a CLI verb path (argv) that surfaces each — the invocability
#: roster (A8): ~12 verbs on 7 workflows.
_WORKFLOW_TO_VERB: dict[str, tuple[str, ...]] = {
    "release_definition": ("release", "define"),
    "backlog_definition": ("backlog", "define"),
    "implementation": ("pipeline",),
    "closure": ("close",),
    "audit": ("audit",),
    "research": ("research",),
    "bug_report": ("bug_report",),
}


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _model_step_runtimes(payload: dict[str, object]) -> set[str]:
    """The runtime_kind values of the payload's model (non-gate) steps."""
    steps = payload.get("steps")
    assert isinstance(steps, list)
    return {str(s["runtime"]) for s in steps if isinstance(s, dict) and s.get("runtime")}


@pytest.mark.parametrize(
    ("verb", "run_id", "workflow_id", "step_label"),
    [(row[1], row[2], row[3], row[4]) for row in _WIRE_VERBS],
    ids=_IDS,
)
def test_wire_verb_completes_and_persists_resolver_snapshot(
    workspace: Path,
    verb: str,
    run_id: str,
    workflow_id: str,
    step_label: str,
) -> None:
    """AC-3: the verb runs to COMPLETED under fake and leaves a resolver-derived snapshot.
    Also folds in the governed-catalog invocability check: the three wired bodies are
    AVAILABLE, the governed catalog carries all 7 workflow ids, and every one of the 7
    workflows is invocable via its registered CLI verb."""
    availability = {wf.name: wf.availability for wf in list_dadaia_workflows()}
    for wired in ("audit", "research", "bug_report"):
        assert availability[wired] == AVAILABILITY_AVAILABLE

    governed_ids = {wf.workflow_id for wf in governed_workflow_catalog().workflows}
    assert governed_ids == set(_WORKFLOW_TO_VERB)

    registered_verbs = set(typer.main.get_command(lifecycle_app).commands)
    for wf_id, verb_path in _WORKFLOW_TO_VERB.items():
        assert verb_path[0] in registered_verbs, f"{wf_id} verb {verb_path[0]!r} not registered"

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            verb,
            "--release-id",
            _RELEASE,
            "--run-id",
            run_id,
            "--harness",
            "fake",
            "--json",
        ],
    )

    # COMPLETED end-to-end (exit 0) — the bug_report step-aware fake keeps bug_write in-scope.
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["completed"] is True

    # AC-1 extended: the persisted run carries a resolver-derived workflow_policy (None pre-wire).
    run = container.build_lifecycle_run_store(workspace).load(run_id)
    assert run is not None
    policy = run.workflow_policy
    assert policy is not None, "workflow_policy is None — verb is not resolver-governed"
    assert policy.workflow_id == workflow_id
    entry = policy.step(step_label)
    assert entry is not None

    # The persisted entry equals what the shared resolver derives independently.
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

    # AC-2(a/v) parity: runtime_kind stayed FAKE — the fake adapter ran, never codex/pi.
    assert _model_step_runtimes(payload) == {AgentRuntimeKind.FAKE.value}
