"""The route the operator takes when something has ALREADY gone wrong.

Measured, not assumed: with the ``r22-release-completes-with-unapproved-plan-tasks``
defect deliberately put back into the terminal gate, the entire e2e + integration suite
stayed green — 309 passed. The happy path was covered end to end and every recovery path
was covered by nothing, which is precisely where the consumer-side validator kept finding
real defects. A suite that is green while the product is broken is the complaint the
operator has been making all along, and it was correct.

What these tests drive is the CLI itself, on a real workspace, in the order a human hits
it: run, get interrupted, read what the tool printed, paste it back. The assertions are on
what the operator can actually see and do — the exit code, the printed command, the state
the ledger reports afterwards — because those are the things that were wrong.

``--harness fake`` pins the Python contract, not model output (same reasoning as the
happy-path chain). Interrupting is simulated by writing the ledger state a killed driver
leaves behind, since a test cannot SIGKILL an in-process runner — the state on disk is the
whole input to recovery, so reproducing it exactly is what matters.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.pipeline import InvalidResumeStepError
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.e2e

_runner = CliRunner()

_CTX = "recoveryctx"
_REPO = "recoveryrepo"
_RELEASE = "v0.1.0"


def _cli(*args: str):
    return _runner.invoke(app, list(args))


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    repo = tmp_path / "repos" / _REPO
    repo.mkdir(parents=True)
    for args in (
        ["init", "-q"],
        ["config", "user.email", "e2e@test"],
        ["config", "user.name", "e2e"],
        ["commit", "-q", "--allow-empty", "-m", "init"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DADAIA_SESSION_ID", "e2e-recovery-session")
    assert _cli("context", "create", _CTX, "--repo", _REPO, "--url", str(repo)).exit_code == 0
    assert _cli("context", "alive", _CTX).exit_code == 0
    return tmp_path


def _specs(workspace: Path) -> Path:
    return workspace / "repos" / _REPO / "specs"


def _release_dir(workspace: Path) -> Path:
    return _specs(workspace) / "releases" / _RELEASE


def _kill_driver_at(workspace: Path, run_id: str, step: str) -> None:
    """Leave behind exactly what a SIGKILLed driver leaves: a run still claiming to run.

    Written through the store rather than by hand so the on-disk shape is the product's
    own, not this test's idea of it.
    """
    JsonLifecycleRunStore(workspace).save(
        LifecycleRun(
            run_id=run_id,
            command="release_definition",
            context=_CTX,
            release_id=_RELEASE,
            phase=LifecyclePhase.RELEASE_DEFINITION,
            status=LifecycleRunStatus.RUNNING,
            current_step=step,
            expected_artifacts=(),
            idempotency_key=run_id,
        )
    )


def _printed_command(output: str) -> str:
    """The recovery line the tool told the operator to run, taken verbatim from stdout.

    Deliberately parsed out of the real output instead of reconstructed: the defect being
    guarded against is the tool printing something the operator CANNOT paste, and a test
    that rebuilds the command itself would pass while the printed one stays prose.
    """
    for raw in output.splitlines():
        line = raw.strip()
        # The tool labels the line ("Recovery: dadaia lifecycle …"). Strip a label, never
        # anything else: the point is to take what was PRINTED, minus the human prefix and
        # the trailing `  # note`, and run exactly that.
        if ": dadaia lifecycle" in line:
            line = line.split(": ", 1)[1].strip()
        if line.startswith("dadaia lifecycle"):
            return line.split("  #", 1)[0].strip()
    raise AssertionError(f"no pasteable `dadaia lifecycle …` command was printed:\n{output}")


def _authored_pick(workspace: Path) -> str:
    backlog = _cli(
        "lifecycle", "backlog-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "bd1",
        "--harness", "fake", "--demand", "add an example verb",
    )  # fmt: skip
    assert backlog.exit_code == 0, backlog.output
    items = [p for p in (_specs(workspace) / "backlog").glob("*.md") if p.stem != "README"]
    assert items, "backlog-definition completed without leaving an item on disk"
    return items[0].stem


def test_an_interrupted_definition_is_sealed_and_its_recovery_is_runnable(
    workspace: Path,
) -> None:
    """Bugs ``r21-killed-driver-leaves-running-ledger`` and the R-23 recovery class.

    Inspecting a dead run must not merely describe the wreck: it must resolve it, and hand
    back a line that runs. Both halves failed on live rounds, and both were reported as
    "there is nothing I can do next".
    """
    _authored_pick(workspace)
    _kill_driver_at(workspace, "rd-killed", "definition_draft")

    status = _cli("lifecycle", "status", "--run-id", "rd-killed")
    assert status.exit_code == 0, status.output

    sealed = JsonLifecycleRunStore(workspace).load("rd-killed")
    assert sealed is not None
    assert sealed.status is LifecycleRunStatus.BLOCKED, (
        "the run was left RUNNING on disk, so every later reader — status, panel, the "
        "next preflight — believes work is still in flight that nothing is doing"
    )

    command = _printed_command(status.output)
    assert command.startswith("dadaia lifecycle release-definition "), command
    for required in ("--run-id rd-killed", "--resume-from definition_draft", f"--context {_CTX}"):
        assert required in command, f"{required!r} missing from the printed recovery: {command}"


def test_the_printed_recovery_actually_runs_and_finishes_the_release(workspace: Path) -> None:
    """The recovery is only real if pasting it works — so this pastes it.

    Every earlier round asserted that a command was PRINTED. None executed it. That gap is
    how a remedy naming the wrong workflow survived
    (``r22-lifecycle-status-pipeline-recovery-wrong-verb``).
    """
    _authored_pick(workspace)
    _kill_driver_at(workspace, "rd-resume", "definition_draft")
    status = _cli("lifecycle", "status", "--run-id", "rd-resume")
    command = _printed_command(status.output)

    resumed = _cli(*command.split()[1:], "--harness", "fake", "--backlog-run-id", "bd1")

    assert resumed.exit_code == 0, (
        f"the command the tool told the operator to run does not work:\n{command}\n{resumed.output}"
    )
    for name in ("SPEC", "PLAN", "TASKS"):
        artifact = _release_dir(workspace) / f"{name}.md"
        assert artifact.is_file(), f"{name}.md was never written by the resumed run"
        assert "**Status:** Aprovado" in artifact.read_text(encoding="utf-8"), (
            f"{name}.md exists but was never approved by the resumed run"
        )


def test_a_resume_past_the_review_cannot_reach_implementation(workspace: Path) -> None:
    """A resume landing on the terminal gate cannot declare a release binding.

    Honest about what this proves. Driving it through the CLI, the FIRST barrier hit is the
    step-graph check (``definition_draft`` wrote no ledger payload), not the approval gate —
    so this test alone does not discriminate the approval fix. The discriminating proof for
    ``r22-release-completes-with-unapproved-plan-tasks`` is
    ``tests/unit/features/lifecycle/test_resume_cannot_bypass_approval.py``, which calls the
    terminal gate directly; that test goes red the moment the fix is reverted, and this one
    does not. Saying so is the point — a test whose failure mode I have not measured is a
    test I do not know the value of, and that is what the operator has been getting.

    What it DOES prove, and nothing else covered: the CLI route ends in a refusal, the
    refusal names its real cause, and ACTIVE.md is not repointed. The reason is asserted
    exactly so it can never start passing for a different one.
    """
    _authored_pick(workspace)
    _kill_driver_at(workspace, "rd-skip", "definition_commit_gate")
    status = _cli("lifecycle", "status", "--run-id", "rd-skip")
    command = _printed_command(status.output)
    assert "--resume-from definition_commit_gate" in command, command

    resumed = _cli(*command.split()[1:], "--harness", "fake", "--backlog-run-id", "bd1")

    assert resumed.exit_code != 0, (
        "a resume that lands on the terminal gate completed the definition. Whatever it "
        f"declared binding was never produced or never approved:\n{resumed.output}"
    )
    assert "graph incomplete" in resumed.output, (
        f"the refusal must name its cause, not merely happen:\n{resumed.output}"
    )
    active = _specs(workspace) / "releases" / "ACTIVE.md"
    if active.is_file():
        assert "phase: IMPLEMENTATION" not in active.read_text(encoding="utf-8"), (
            "ACTIVE.md was repointed to IMPLEMENTATION over artifacts the run never produced"
        )


def test_a_blocked_gate_never_prescribes_the_command_that_just_failed(
    workspace: Path,
) -> None:
    """Found by writing the test above; it is the R-16 class arriving on a new route.

    The step-graph block prescribed ``--resume-from <the gate that detected the hole>`` —
    so pasting the recovery re-ran the gate, which re-detected the same hole, forever. A
    recovery that reproduces the condition is worse than none: it looks like progress.
    The remedy now names the step whose missing payload caused it.
    """
    _authored_pick(workspace)
    _kill_driver_at(workspace, "rd-loop", "definition_commit_gate")
    command = _printed_command(_cli("lifecycle", "status", "--run-id", "rd-loop").output)

    blocked = _cli(*command.split()[1:], "--harness", "fake", "--backlog-run-id", "bd1")

    assert "graph incomplete" in blocked.output, blocked.output
    remedy = _printed_command(blocked.output)
    assert "--resume-from definition_draft" in remedy, (
        "the recovery must name the step that has to run, not the gate that noticed. "
        f"Pasting this would reproduce the same block:\n{remedy}"
    )
    assert remedy != command, "the block prescribed the exact command that produced it"


def test_a_blocked_definition_never_reports_completed_in_the_ledger(
    workspace: Path,
) -> None:
    """Bug ``r22-release-definition-completes-with-consumes-bind-error``.

    The command said BLOCKED and exited 3 while the ledger every tool reads said COMPLETED.
    Asserting the exit code alone would have passed throughout — the disagreement IS the
    defect, so both are asserted together.
    """
    blocked = _cli(
        "lifecycle", "release-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "rd-bind",
        "--harness", "fake", "--backlog-run-id", "never-ran",
    )  # fmt: skip

    assert blocked.exit_code != 0, blocked.output
    persisted = JsonLifecycleRunStore(workspace).load("rd-bind")
    if persisted is not None:
        assert persisted.status is not LifecycleRunStatus.COMPLETED, (
            "the command told the operator it was blocked and the ledger says the run "
            "completed. The ledger wins by default, because it is what every later tool "
            "reads, and a false COMPLETED lets the next phase start on a definition that "
            "never consumed its backlog"
        )
    status = _cli("lifecycle", "status", "--run-id", "rd-bind", "--json")
    if status.exit_code == 0:
        assert json.loads(status.output)["status"] != "completed", status.output


def test_status_on_a_run_nobody_started_says_so_instead_of_inventing_one(
    workspace: Path,
) -> None:
    """The guard against making every recovery path 'work' by fabricating state.

    If ``status`` answered for unknown ids, the tests above would pass against a tool that
    seals runs into existence — and the operator would chase a run that never ran.
    """
    result = _cli("lifecycle", "status", "--run-id", "never-existed")
    assert JsonLifecycleRunStore(workspace).load("never-existed") is None
    assert "never-existed" in result.output


def test_every_recovery_this_suite_produced_is_a_command_not_prose(workspace: Path) -> None:
    """Bug ``r22-release-review-rejection-deadlocks`` (escapability), on real output.

    The contract ratchet reads source and cannot see what is PRINTED. This drives the two
    block routes an operator actually meets and reads the terminal, which is the only place
    the promise is either kept or broken.
    """
    _kill_driver_at(workspace, "rd-prose-1", "definition_draft")
    outputs = [_cli("lifecycle", "status", "--run-id", "rd-prose-1").output]
    outputs.append(
        _cli(
            "lifecycle",
            "release-definition",
            "--context",
            _CTX,
            "--release-id",
            _RELEASE,
            "--run-id",
            "rd-prose-2",
            "--harness",
            "fake",
            "--backlog-run-id",
            "never-ran",
        ).output  # fmt: skip
    )
    for output in outputs:
        lowered = output.lower()
        for prose in ("re-run the workflow with", "re-run the step that produces"):
            assert prose not in lowered, (
                f"the operator was handed instructions to assemble a command:\n{output}"
            )


def test_the_ledger_a_recovery_leaves_behind_is_readable_by_the_next_tool(
    workspace: Path,
) -> None:
    """Recovery is not done when the command exits — it is done when the tree is coherent.

    ``lifecycle status --json`` is what the panel and the next preflight consume; if a
    sealed run cannot be read back as valid JSON carrying its own reason and remedy, the
    seal helped nobody.
    """
    _kill_driver_at(workspace, "rd-json", "definition_review")
    assert _cli("lifecycle", "status", "--run-id", "rd-json").exit_code == 0

    result = _cli("lifecycle", "status", "--run-id", "rd-json", "--json")
    payload = json.loads(result.output)
    assert payload["detail"], payload
    assert str(payload["recovery"]).startswith("dadaia lifecycle"), (
        "the machine-readable recovery is what the panel and the next preflight consume. "
        f"A prose fallback here is invisible to the source ratchet: {payload}"
    )


# ── bug r24-invalid-resume-implementation-preflight-mask (validator R24 / R-16) ────
#
# `backlog-definition` and `release-definition` both reject an unknown `--resume-from`
# with one clean line naming the valid steps. `implementation-reviews` ran its preflight
# FIRST, so the operator was told to go fix a context bind — and only after doing that,
# re-running, and waiting, would they learn the step name was wrong all along. Two round
# trips for a command that was wrong on its face.
#
# The file already states the rule one line above where it broke: "Argument validation
# FIRST (bad --harness fails fast regardless of preflight state)". `--resume-from` is an
# argument like any other; whether it names a real step is knowable without reading a
# single byte of workspace state.


@pytest.mark.parametrize(
    "verb, expected_steps",
    [
        ("backlog-definition", "backlog_author"),
        ("release-definition", "definition_draft"),
        ("implementation-reviews", "implement"),
        # audit was left out of the first fix for this class and round 25 found it:
        # bug r25-audit-resume-invalid-step-validates-target-first.
        ("audit", "audit_report"),
    ],
)
def test_an_unknown_resume_step_is_named_before_any_state_is_read(
    workspace: Path, verb: str, expected_steps: str
) -> None:
    result = _cli(
        "lifecycle", verb,
        "--context", _CTX, "--release-id", _RELEASE,
        "--run-id", f"r16-{verb}", "--harness", "fake",
        "--resume-from", "unknown-step",
    )  # fmt: skip

    # Rendering a DadaiaError down to one operator-facing line is `_safe_app`'s job and is
    # covered in tests/unit/cli/test_main_safe_app.py. CliRunner invokes `app` directly, so
    # what is pinned here is WHICH error surfaces and WHEN — the half that was broken.
    assert result.exit_code != 0
    surfaced = str(result.exception) if result.exception is not None else result.output
    assert isinstance(result.exception, InvalidResumeStepError), surfaced
    assert "is not a step of this workflow" in surfaced
    assert expected_steps in surfaced, "the operator must be told which steps ARE valid"
    assert "active release mismatch" not in surfaced, (
        "a preflight complaint here sends the operator to fix workspace state for a "
        "command that could never have run"
    )


@pytest.mark.parametrize(
    "verb", ["backlog-definition", "release-definition", "implementation-reviews", "audit"]
)
def test_an_unknown_resume_step_is_named_even_with_no_context_flag(
    workspace: Path, verb: str
) -> None:
    """Bug ``r25-resume-invalid-step-validates-context-first`` (validator R25 / R-16).

    The previous fix put the check after ``--context`` resolution, so dropping the flag —
    which is exactly how an operator types it — meant context resolution ran first and a
    plainly wrong step name came back as an unrelated context error, as a bare
    ``ValueError``. Two mistakes at once: the wrong thing answered, and answered as a
    crash.

    The rule was already written into the fix that preceded this one: a token that is wrong
    on its face is knowable without reading one byte of workspace state. It was simply
    placed one line too late.
    """
    result = _cli(
        "lifecycle", verb,
        "--release-id", _RELEASE, "--run-id", f"noctx-{verb}",
        "--harness", "fake", "--resume-from", "no-such-step",
    )  # fmt: skip

    assert result.exit_code != 0
    surfaced = str(result.exception) if result.exception is not None else result.output
    assert isinstance(result.exception, InvalidResumeStepError), surfaced
    assert "is not a step of this workflow" in surfaced
    assert "context" not in surfaced.lower(), (
        f"the operator was answered about context for a bad step name: {surfaced}"
    )


@pytest.mark.parametrize(
    "verb", ["backlog-definition", "release-definition", "implementation-reviews", "audit"]
)
def test_an_unknown_harness_is_named_rather_than_the_context(workspace: Path, verb: str) -> None:
    """The same class as the resume-step ordering bug, one argument over.

    Found by sweeping rather than by a report: after hoisting the ``--resume-from`` check
    above context resolution, the obvious question was which OTHER argument is still
    validated after it. ``--harness`` was. On ``backlog-definition`` and
    ``release-definition`` a bad harness answered "No caller-owned Spec Context is
    selected" — a bind instruction, for a command whose harness name does not exist — while
    the other two verbs already rejected it correctly.

    Which argument is wrong is knowable with no workspace state, so it is answered first.
    """
    result = _cli(
        "lifecycle", verb,
        "--release-id", _RELEASE, "--run-id", f"badharness-{verb}",
        "--harness", "not-a-harness", "--demand", "d",
    )  # fmt: skip

    assert result.exit_code != 0
    surfaced = str(result.exception) if result.exception is not None else result.output
    assert "Spec Context" not in surfaced, (
        f"a bad --harness was answered with a context bind instruction: {surfaced}"
    )
