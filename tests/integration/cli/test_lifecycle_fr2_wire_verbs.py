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
from dadaia_workspace.features.lifecycle.workflows.bug_report import (
    _BUG_WRITE_STEP,
)
from dadaia_workspace.features.lifecycle.workflows.bug_report import (
    _SEQUENCE as _BUG_REPORT_SEQUENCE,
)
from dadaia_workspace.features.workflows.dadaia_catalog import (
    AVAILABILITY_AVAILABLE,
    governed_workflow_catalog,
    list_dadaia_workflows,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.helpers.golden_platform import norm_stderr

# _norm_stderr: consolidated into tests/helpers/golden_platform.norm_stderr (v0.1.64 FR1).


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
    """AC-3: the verb runs to COMPLETED under fake and leaves a resolver-derived snapshot."""
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


@pytest.mark.parametrize(
    ("verb", "step_label"), [(row[1], row[4]) for row in _WIRE_VERBS], ids=_IDS
)
def test_wire_verb_rejects_raw_step_model(workspace: Path, verb: str, step_label: str) -> None:
    """AC-2(iii): a raw ``--step-model label=<id>:<effort>`` is a D-3 profile-id rejection."""
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            verb,
            "--release-id",
            _RELEASE,
            "--harness",
            "fake",
            "--step-model",
            f"{step_label}=gpt-5.5:high",
        ],
    )
    assert result.exit_code != 0
    assert "profile id" in result.output


@pytest.mark.parametrize("verb", [row[1] for row in _WIRE_VERBS], ids=_IDS)
def test_wire_verb_model_flag_is_removed(workspace: Path, verb: str) -> None:
    """v0.1.57 FR6 (inverted from the v0.1.56 non-fatal-deprecation case): ``--model`` is now
    an UNKNOWN option — exit 2 + ``No such option: --model`` on stderr + empty stdout (Q4).

    The D-3 profile-id rejection stays asserted by ``test_wire_verb_rejects_raw_step_model``.
    """
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            verb,
            "--release-id",
            _RELEASE,
            "--harness",
            "fake",
            "--model",
            "anything:high",
            "--json",
        ],
    )
    assert result.exit_code == 2
    assert "No such option: --model" in norm_stderr(result.stderr)
    # Q4: the UsageError is on stderr — stdout stays empty.
    assert result.stdout == ""


def test_governed_catalog_reports_wired_workflows_available_and_invocable() -> None:
    """AC-3: the three wired bodies are AVAILABLE and all 7 governed workflows are invocable."""
    availability = {wf.name: wf.availability for wf in list_dadaia_workflows()}
    # The three Wave-E bodies wired this release are AVAILABLE (unchanged — always were).
    for wired in ("audit", "research", "bug_report"):
        assert availability[wired] == AVAILABILITY_AVAILABLE

    # The governed resolver catalog carries all 7 workflow ids (the single governed source).
    governed_ids = {wf.workflow_id for wf in governed_workflow_catalog().workflows}
    assert governed_ids == set(_WORKFLOW_TO_VERB)

    # Every one of the 7 workflows is now invocable — its surfacing CLI verb is registered
    # (the three new verbs close the last invocability gap: 7 defined / 7 invocable).
    registered = set(typer.main.get_command(lifecycle_app).commands)
    for workflow_id, verb_path in _WORKFLOW_TO_VERB.items():
        assert verb_path[0] in registered, f"{workflow_id} verb {verb_path[0]!r} not registered"


def test_bug_report_verb_routes_through_additive_no_lease_path_structurally(
    workspace: Path,
) -> None:
    """AC-3 (structural): the bug_report verb's real ``bug_write`` target is ADDITIVE.

    The verb routes through NO MUTATING/lease-acquiring path by construction: the only
    file-writing step, ``bug_write``, scopes writes exclusively to the ADDITIVE
    ``specs/bugs/`` path class (the gate's path classifier never leases ADDITIVE writes).
    Every other step writes only to the handoff dir. This is a construction property of the
    verb — asserted on the workflow the container builder produces, NOT a fake-run lease
    observation (under ``--harness fake`` "no lease" is vacuous — the fake writes nothing).
    """
    wf = container.build_bug_report_workflow(workspace, context=_CONTEXT, release_id=_RELEASE)
    bug_write_step = next(s for s in _BUG_REPORT_SEQUENCE if s.label == _BUG_WRITE_STEP)
    bug_write_scope = wf._scope(bug_write_step, "struct", "suffix")  # noqa: SLF001
    # ADDITIVE-only: exactly the specs/bugs channel — no .dadaia/, no MUTATING repo path.
    assert bug_write_scope.allowed_paths == (
        f"repos/{_CONTEXT}/specs/bugs/**",
        "specs/bugs/**",
    )
    assert all("specs/bugs" in p for p in bug_write_scope.allowed_paths)

    # Every OTHER (non-writing) step emits only to the handoff dir — never specs/bugs, never a
    # MUTATING target that would take a lease.
    for step in _BUG_REPORT_SEQUENCE:
        if step.fragment_id is None or step.label == _BUG_WRITE_STEP:
            continue
        other_scope = wf._scope(step, "struct", "suffix")  # noqa: SLF001
        assert all("specs/bugs" not in p for p in other_scope.allowed_paths)
        assert all(p.startswith(".dadaia/handoff/") for p in other_scope.allowed_paths)
