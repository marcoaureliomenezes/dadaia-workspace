"""T3 discovery: the image builds on this checkout's wheel, holds no dadaia
on PATH, installs only the run's build, and the grader passes a hand-done workspace and fails an empty one.

Docker is required: a missing tool fails the row, never skips it. 600 s: T1's four image builds
took 95 s on ubuntu-24.04 (run 37554712931). Candidate only: no published build is installed.

Owner: dd-sw-engineer-sr
"""

import pytest

from tests.helpers.evals import HAND_T3, T3, image, reward, wheel
from tests.helpers.oslib import run

VERSIONS = ("candidate",)

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.timeout(600)]


def _in_image(version: str, script: str):
    return run(["docker", "run", "--rm", image(T3, version), "bash", "-c", script])


@pytest.mark.parametrize("version", VERSIONS)
def test_the_image_builds_on_each_version(version: str) -> None:
    assert image(T3, version) == f"dadaia-workspace-evals-{T3}:{version}"


@pytest.mark.parametrize("version", VERSIONS)
def test_no_dadaia_is_on_path(version: str) -> None:
    assert _in_image(version, "command -v dadaia").returncode == 1


@pytest.mark.parametrize("version", VERSIONS)
def test_a_plain_install_resolves_the_lib_build(version: str) -> None:
    want = wheel().name.split("-")[1]
    done = _in_image(
        version,
        "python3 -m venv /tmp/v && /tmp/v/bin/pip install -q --no-index --find-links /opt/wheelhouse dadaia-workspace >&2"
        " && /tmp/v/bin/dadaia --version",
    )
    assert done.returncode == 0, done.stderr[-3000:]
    assert want in done.stdout


@pytest.mark.parametrize("version", VERSIONS)
def test_the_grader_passes_a_hand_done_workspace(version: str) -> None:
    assert reward(T3, version, HAND_T3) == "1"


@pytest.mark.parametrize("version", VERSIONS)
def test_the_grader_fails_an_empty_workspace(version: str) -> None:
    assert reward(T3, version, "true") == "0"
