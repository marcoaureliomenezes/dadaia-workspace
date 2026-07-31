"""The gates the operator actually meets, driven through the CLI, on a real workspace.

Written because the E2E suite was measured and found wanting. Seven realistic defects —
each one a class the consumer-side validator reported over rounds 19-24 — were reintroduced
into production code one at a time and the whole E2E suite was run against each:

    approval-gate-bypass (r22) .................. SURVIVED — 101 passed
    table cell split on every pipe (r24/F-26) .... SURVIVED — 101 passed
    terminal bug event without reported (r19) .... SURVIVED — 101 passed
    ledger attempt overwrite (r23/R-11) ......... SURVIVED — 101 passed
    silent chmod failure (r24/R-21) ............. caught
    resume accepts an unknown step (r24/R-16) ... caught

Four of six defect classes shipped past a fully green E2E suite. Two of the four are the
exact bugs that stopped a live release inside the consumer's validator. That is what "the
tests are green and the product is broken" looks like from the inside, and the operator
has been saying so for three weeks.

The full suite, for the record, caught all seven — every one of these classes is pinned by
a unit or contract test. So the problem was never "the tests are worthless"; it was that
the layer which exercises the product the way the operator does was blind to four of them,
and every one of those pins was written only AFTER the consumer-side validator found the
bug. The suite has been good at not re-shipping a known defect and has never once found a
new one.

Each test below was written against a specific survivor and then MEASURED: the mutant was
reintroduced and the test confirmed to go red, then reverted and confirmed green. Every one
kills exactly its own target and nothing else. A test whose failure mode has not been
observed is not evidence of anything, which is the whole lesson of this file — two of these
first passed for the wrong reason (one refused on schema validation before ever reaching
the guard it claimed to test) and only the measurement exposed it.

Writing the fourth of them found a live defect that the ledger had recorded as fixed:
``r25-resume-still-overwrites-attempt-zero-on-the-cli-path``. Driving a real resume through
the CLI changed ``definition_draft`` attempt-0's content hash in place and created no
attempt-1. The resume path dropped every record for the steps it re-runs, so
``next_attempt_for`` read an empty ledger and answered 0 again — the fix shipped for
``r23-resume-overwrites-ledger-owned-step-payload`` was pinned by a unit test on the helper
in isolation and was never reached from the CLI at all. That is the precise shape of "the
tests are green and the product is broken", and it took a mutation measurement plus an
end-to-end test to see it.

``--harness fake`` pins the Python contract rather than model output; the gates under test
are deterministic Python, so the fake harness exercises exactly the code the operator hits.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.e2e

_runner = CliRunner()

_CTX = "gatesctx"
_REPO = "gatesrepo"
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
    monkeypatch.setenv("DADAIA_SESSION_ID", "e2e-gates-session")
    assert _cli("context", "create", _CTX, "--repo", _REPO, "--url", str(repo)).exit_code == 0
    assert _cli("context", "alive", _CTX).exit_code == 0
    return tmp_path


def _release_dir(workspace: Path) -> Path:
    return workspace / "repos" / _REPO / "specs" / "releases" / _RELEASE


def _defined_release(workspace: Path) -> None:
    """Drive backlog-definition then release-definition to completion, as the operator does."""
    backlog = _cli(
        "lifecycle", "backlog-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "bd1",
        "--harness", "fake", "--demand", "add an example verb",
    )  # fmt: skip
    assert backlog.exit_code == 0, backlog.output
    define = _cli(
        "lifecycle", "release-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "rd1",
        "--harness", "fake", "--backlog-run-id", "bd1",
    )  # fmt: skip
    assert define.exit_code == 0, define.output
    for name in ("SPEC", "PLAN", "TASKS"):
        assert "**Status:** Aprovado" in (_release_dir(workspace) / f"{name}.md").read_text(
            encoding="utf-8"
        )


# ── survivor 1: approval-gate-bypass (r22-release-completes-with-unapproved-plan-tasks) ──


def test_a_release_cannot_bind_over_an_artifact_that_is_not_approved(workspace: Path) -> None:
    """Resuming onto the terminal gate must re-read the artifacts, not trust the itinerary.

    The existing e2e resume test could not discriminate this: driven from a killed draft,
    the step-graph check fires FIRST and the approval gate is never reached, so the test
    stayed green with the fix reverted. Here the release is driven to completion first, so
    every ledger payload exists and the graph check passes — which is the only state in
    which the approval gate is the thing under test.
    """
    _defined_release(workspace)
    plan = _release_dir(workspace) / "PLAN.md"
    plan.write_text(
        plan.read_text(encoding="utf-8").replace("**Status:** Aprovado", "**Status:** Draft", 1),
        encoding="utf-8",
    )

    resumed = _cli(
        "lifecycle", "release-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "rd1",
        "--harness", "fake", "--backlog-run-id", "bd1",
        "--resume-from", "definition_commit_gate",
    )  # fmt: skip

    assert resumed.exit_code != 0, (
        "a release bound itself to IMPLEMENTATION over a PLAN a human reads as Draft:\n"
        + resumed.output
    )
    assert "PLAN.md" in resumed.output, "the refusal must name the artifact that is not approved"


# ── survivor 2: table cell split (r24-live-definition-draft-fails-validation-table) ──


_PIPED_PLAN = """# PLAN

> **Status:** Aprovado

## Validation Dependency Table

| Workstream | Produces by end | Direct validation | Validation dependencies \
| Deferred integration evidence |
|---|---|---|---|---|
| WS-1 | the verb | `rg -n "alpha|beta|gamma" README.md` | None | None |
"""


def test_a_validation_command_containing_a_pipe_does_not_block_the_release(
    workspace: Path,
) -> None:
    """The column asks for a command; commands contain pipes.

    This is the defect that deadlocked a live release in round 24 and that the whole E2E
    suite let through. The lint runs again wherever artifacts are flipped to Aprovado, so
    resuming onto the review step re-runs it against the plan written here.
    """
    _defined_release(workspace)
    (_release_dir(workspace) / "PLAN.md").write_text(_PIPED_PLAN, encoding="utf-8")

    resumed = _cli(
        "lifecycle", "release-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "rd1",
        "--harness", "fake", "--backlog-run-id", "bd1",
        "--resume-from", "definition_review",
    )  # fmt: skip

    assert "all five non-empty cells" not in resumed.output, (
        "the lint reported empty cells for a row whose cells are all populated — the false "
        "diagnosis a retry loop cannot converge on:\n" + resumed.output
    )
    assert "plan dependency lint failed" not in resumed.output, resumed.output


def test_a_genuinely_short_row_is_still_refused_and_says_which_row(workspace: Path) -> None:
    """The tolerance must not have turned the gate off."""
    _defined_release(workspace)
    (_release_dir(workspace) / "PLAN.md").write_text(
        _PIPED_PLAN.replace("| WS-1 | the verb | `rg -n \"alpha|beta|gamma\" README.md` | None | None |",
                            "| WS-1 | the verb | None |"),
        encoding="utf-8",
    )  # fmt: skip

    resumed = _cli(
        "lifecycle", "release-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "rd1",
        "--harness", "fake", "--backlog-run-id", "bd1",
        "--resume-from", "definition_review",
    )  # fmt: skip

    assert "plan dependency lint failed" in resumed.output, resumed.output
    assert "'WS-1'" in resumed.output, "the author has to be told which row to go and fix"


# ── survivor 3: a bug nobody opened cannot be closed (r19) ──


def test_closing_a_bug_that_was_never_opened_is_refused(workspace: Path) -> None:
    """A mistyped --bug-id used to mint a phantom resolved bug, so the real one stayed open.

    Covered by a unit test since r19 and by nothing the operator can run. The operator
    meets this through the CLI, which is where it has to hold.
    """
    # `--release` is required by the event schema. Omitting it made an earlier version of
    # this test pass for the wrong reason: the CLI refused on schema validation and the
    # terminal-event guard was never reached, so the test stayed green with the guard
    # removed. Measured, not assumed — every field the event needs is supplied here so the
    # guard is the only thing left that can refuse.
    result = _cli(
        "bugs", "append", "--context", _CTX,
        "--bug-id", "a-bug-that-was-never-reported", "--event", "resolved",
        "--release", "0.4.2",
        "--resolution-evidence", "a plausible looking twenty plus character evidence string",
    )  # fmt: skip

    assert result.exit_code != 0, (
        "the ledger accepted a close for a bug nobody opened — the evidence trail now "
        "contains an entry that cannot be evidence of anything"
    )
    # Asserted on the ledger rather than on the printed message: the CLI renders a
    # DadaiaError through `_safe_app`, which CliRunner does not go through, so an assertion
    # on stdout here would be measuring the test harness. What must hold is that the file
    # on disk gained nothing.
    written = [
        line
        for path in (workspace / "repos" / _REPO / "specs" / "bugs").glob("*.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
        if "a-bug-that-was-never-reported" in line
    ]
    assert not written, f"a phantom event reached the ledger: {written}"


# ── survivor 4: a resume adds to the record (r23-resume-overwrites-ledger-owned-payload) ──


def test_a_resume_records_a_new_attempt_and_leaves_the_first_one_intact(
    workspace: Path,
) -> None:
    """What an operator reads after an interruption is what the first attempt wrote.

    Asserted on the ledger the product itself writes, through the CLI, because the unit
    test for this pins ``next_attempt_for`` in isolation — and isolation is exactly where a
    produce site that still hard-codes ``attempt=0`` stays invisible.
    """
    _defined_release(workspace)
    state = workspace / ".dadaia" / "states" / "lifecycle" / "rd1.json"
    before = _first_draft(state)
    assert before is not None, "the completed run recorded no definition_draft attempt"

    resumed = _cli(
        "lifecycle", "release-definition",
        "--context", _CTX, "--release-id", _RELEASE, "--run-id", "rd1",
        "--harness", "fake", "--backlog-run-id", "bd1",
        "--resume-from", "definition_draft",
    )  # fmt: skip
    assert resumed.exit_code == 0, resumed.output

    records = _step_records(state)
    drafts = sorted(
        (r for r in records if r["producer_step"] == "definition_draft"),
        key=lambda r: r["attempt"],
    )
    assert [r["attempt"] for r in drafts][:2] == [0, 1], (
        "the resumed run produced at the same (step, attempt) key, so the earlier "
        f"attempt was replaced instead of preserved: {[(r['attempt'], r['content_hash'][:8]) for r in drafts]}"
    )
    after = _first_draft(state)
    assert after is not None
    assert after["content_hash"] == before["content_hash"], (
        "attempt-0's content hash changed in place — what the first attempt wrote is "
        "exactly what an operator needs to read after an interruption"
    )
    assert after["payload_ref"] == before["payload_ref"]


def _step_records(state: Path) -> list[dict]:
    """The ledger as the product writes it: ``run.workflow_steps``."""
    run = json.loads(state.read_text(encoding="utf-8"))["run"]
    return [r for r in (run.get("workflow_steps") or []) if isinstance(r, dict)]


def _first_draft(state: Path) -> dict | None:
    for record in _step_records(state):
        if record["producer_step"] == "definition_draft" and record["attempt"] == 0:
            return record
    return None
