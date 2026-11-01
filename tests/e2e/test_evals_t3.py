"""T3 discovery: the image builds on this checkout's wheel, holds no dadaia
on PATH, installs only the run's build, and the task is two steps on one workspace: the first grader rewards onboarding and
nothing past it, the second the demand the relaunched session entered through a path the law admits.

Docker is required: a missing tool fails the row, never skips it. 600 s: T1's four image builds
took 95 s on ubuntu-24.04 (run 37554712931). Candidate only: no published build is installed.

Owner: dd-sw-engineer-sr
"""

import tomllib

import pytest

from tests.helpers.evals import (
    BASELINED_T3,
    CALC_BRANCH_T3,
    CALC_COMMIT_T3,
    CALC_MERGE_T3,
    CALC_PUSH_T3,
    CALC_UNCOMMITTED_T3,
    CALC_WORKTREE_T3,
    DOCTOR_ERROR_T3,
    HAND_T3,
    MAIN_BACKLOG_T3,
    MAIN_SPEC_T3,
    ONBOARDED_NO_SPECS_T3,
    ONBOARDED_T3,
    ORG_BROKEN_BACKLOG_T3,
    ORG_CALC_ON_ORIGIN_T3,
    ORG_CALC_THEN_LANE_T3,
    ORG_DOCTOR_ERROR_T3,
    ORG_LANE_T3,
    ORG_NO_ENTRY_T3,
    ORG_NO_SESSION_T3,
    ORG_RC_SPEC_T3,
    ORG_REJECTED_T3,
    ORG_TRACED_T3,
    ORG_UNCOMMITTED_T3,
    ORG_WORK_BRANCH_T3,
    REAPED_T3,
    REJECTED_T3,
    RENAMED_T3,
    ROOT,
    SESSION_T3,
    SPEC_T3,
    STUB_T3,
    T3,
    TRACED_T3,
    VERDICT_T3,
    WORKTREE_ONLY_T3,
    image,
    reward,
    wheel,
)
from tests.helpers.oslib import run

VERSIONS = ("candidate",)

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.timeout(600)]


def _in_image(version: str, script: str):
    """Offline, so a route that reaches an index fails the row."""
    return run(
        ["docker", "run", "--rm", "--network", "none", image(T3, version), "bash", "-c", script]
    )


@pytest.mark.parametrize("version", VERSIONS)
def test_the_image_builds_on_each_version(version: str) -> None:
    assert image(T3, version) == f"dadaia-workspace-evals-{T3}:{version}"


@pytest.mark.parametrize("version", VERSIONS)
def test_no_dadaia_is_on_path(version: str) -> None:
    assert _in_image(version, "command -v dadaia").returncode == 1


@pytest.mark.parametrize(
    "route",
    [
        "python3 -m venv /tmp/v && /tmp/v/bin/pip install -q /lib/*.whl >&2 && /tmp/v/bin/dadaia --version",
        "python3 -m venv /tmp/u && /tmp/u/bin/pip install -q uv >&2"
        " && /tmp/u/bin/uvx --from /lib/*.whl dadaia --version",
    ],
    ids=["pip", "uvx"],
)
@pytest.mark.parametrize("version", VERSIONS)
def test_a_plain_install_resolves_the_lib_build_offline(version: str, route: str) -> None:
    done = _in_image(version, route)
    assert done.returncode == 0, done.stderr[-3000:]
    assert wheel().name.split("-")[1] in done.stdout


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize(
    ("script", "want"),
    [
        (HAND_T3, "0"),
        (RENAMED_T3, "0"),
        (SPEC_T3, "0"),
        (STUB_T3, "0"),
        (TRACED_T3, "0"),
        (REJECTED_T3, "0"),
        (ONBOARDED_T3, "1"),
        (ONBOARDED_NO_SPECS_T3, "1"),
        (BASELINED_T3, "1"),
        (WORKTREE_ONLY_T3, "0"),
        (MAIN_BACKLOG_T3, "0"),
        (MAIN_SPEC_T3, "0"),
        (VERDICT_T3, "0"),
        (SESSION_T3, "1"),
        (REAPED_T3, "1"),
        (CALC_UNCOMMITTED_T3, "0"),
        (CALC_COMMIT_T3, "0"),
        (CALC_BRANCH_T3, "0"),
        (CALC_MERGE_T3, "0"),
        (CALC_PUSH_T3, "0"),
        (CALC_WORKTREE_T3, "0"),
        (DOCTOR_ERROR_T3, "0"),
        ("true", "0"),
    ],
    ids=[
        "hand-done-lane-entry",
        "context-named-otherwise",
        "operator-demand-spec",
        "bare-stub-spec",
        "backlog-origin-traced",
        "filed-then-rejected",
        "onboarded",
        "onboarded-without-specs-init",
        "onboarded-and-baselined",
        "worktree-new-only",
        "main-repo-backlog-entry",
        "main-repo-release-spec",
        "hand-written-verdict",
        "heartbeat-session-record",
        "reaped-session-record",
        "calc-edited-uncommitted",
        "calc-committed-on-checked-out-branch",
        "calc-committed-on-new-branch",
        "calc-raw-merge",
        "calc-pushed-to-origin",
        "calc-committed-in-git-worktree",
        "doctor-error",
        "empty",
    ],
)
def test_the_first_grader_rewards_onboarding_and_nothing_past_it(
    version: str, script: str, want: str
) -> None:
    """The first step's grader rewards onboarding and nothing past it."""
    assert reward(T3, version, script, step="discover") == want


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize(
    ("script", "want"),
    [
        (ORG_WORK_BRANCH_T3, "1"),
        (ORG_LANE_T3, "1"),
        (ORG_RC_SPEC_T3, "1"),
        (ORG_TRACED_T3, "1"),
        (ORG_NO_ENTRY_T3, "0"),
        (ORG_UNCOMMITTED_T3, "0"),
        (ORG_REJECTED_T3, "0"),
        (ORG_NO_SESSION_T3, "0"),
        (ORG_DOCTOR_ERROR_T3, "0"),
        (ORG_BROKEN_BACKLOG_T3, "0"),
        (ORG_CALC_THEN_LANE_T3, "0"),
        (ORG_CALC_ON_ORIGIN_T3, "0"),
        ("true", "0"),
    ],
    ids=[
        "entry-on-the-work-branch",
        "entry-on-an-unmerged-lane",
        "spec-origin-on-an-unmerged-wt-rc",
        "backlog-origin-traced-on-a-wt-rc",
        "no-entry",
        "entry-written-and-never-committed",
        "filed-then-rejected",
        "no-session-record",
        "doctor-error",
        "backlog-checker-red",
        "calc-committed-then-a-reviewed-lane",
        "calc-pushed-to-origin-beside-an-entry",
        "empty",
    ],
)
def test_the_second_grader_rewards_the_demand_the_relaunched_session_entered(
    version: str, script: str, want: str
) -> None:
    """The second step's grader rewards a session record, a clean doctor, the demand on a head
    that its checkers accept, and no move of the project's code."""
    assert reward(T3, version, script, step="organise") == want


@pytest.mark.parametrize("version", VERSIONS)
def test_the_session_launches_at_the_workspace_folder(version: str) -> None:
    assert _in_image(version, "pwd").stdout.strip() == "/workspace"


def test_a_trial_passes_only_when_both_steps_pass() -> None:
    """Step one gates step two, and the trial's reward is the last step's."""
    task = tomllib.loads((ROOT / "evals/tasks/t3-discovery/task.toml").read_text(encoding="utf-8"))
    steps = task["steps"]
    assert [s["name"] for s in steps] == ["discover", "organise"]
    assert steps[0]["min_reward"] == 1
    assert task["multi_step_reward_strategy"] == "final"
    assert task["environment"]["workdir"] == "/workspace"
    assert task["agent"]["timeout_sec"] == 900.0
