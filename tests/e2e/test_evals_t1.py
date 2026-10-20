"""T1 cold onboarding: each image builds on the 0.4.7 layer and on this checkout's wheel;
the grader passes a hand-onboarded workspace of each version and fails an empty one.

Docker is required: a missing tool fails the row, never skips it. 600 s: evals' whole suite, with
four image builds, took 95 s on ubuntu-24.04 (run 37554712931).

Owner: dd-sw-engineer-sr
"""

import pytest

from tests.helpers.evals import HAND, T1, VERSIONS, image, reward, task_dir
from tests.helpers.oslib import run

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.timeout(600)]


@pytest.mark.parametrize("version", VERSIONS)
def test_the_image_builds_on_each_version(version: str) -> None:
    assert image(T1, version) == f"dadaia-workspace-evals-{T1}:{version}"


@pytest.mark.parametrize("version", VERSIONS)
def test_the_grader_passes_a_hand_onboarded_workspace(version: str) -> None:
    assert reward(T1, version, HAND[version]) == "1"


@pytest.mark.parametrize("version", VERSIONS)
def test_the_grader_fails_an_empty_workspace(version: str) -> None:
    assert reward(T1, version, "true") == "0"


@pytest.mark.parametrize("version", VERSIONS)
def test_the_grader_reports_what_doctor_found_when_it_exits_1(version: str) -> None:
    script = (
        f"({HAND[version]}) >&2; echo stray > /workspace/stray.txt; python3 /tests/test_grade.py"
    )
    done = run([
        "docker", "run", "--rm", "--mount", f"type=bind,src={task_dir(T1) / 'tests'},dst=/tests,readonly",
        image(T1, version), "bash", "-c", script,
    ])  # fmt: skip
    assert "WS-root-slop slop stray.txt  (not in the root law or " in done.stderr
    assert "Traceback" not in done.stderr
    assert done.returncode == 1
