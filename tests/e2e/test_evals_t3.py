"""T3 discovery: the image builds on this checkout's wheel, holds no dadaia
on PATH, installs only the run's build, and the grader passes a hand-done workspace and fails an empty one.

Docker is required: a missing tool fails the row, never skips it. 600 s: T1's four image builds
took 95 s on ubuntu-24.04 (run 37554712931). Candidate only: no published build is installed.

Owner: dd-sw-engineer-sr
"""

import pytest

from tests.helpers.evals import HAND_T3, ONBOARDED_T3, RENAMED_T3, ROOT, T3, image, reward, wheel
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
    [(HAND_T3, "1"), (RENAMED_T3, "1"), (ONBOARDED_T3, "0"), ("true", "0")],
    ids=["hand-done", "context-named-otherwise", "no-backlog-entry", "empty"],
)
def test_the_grader_rewards_the_discovery(version: str, script: str, want: str) -> None:
    assert reward(T3, version, script) == want


def test_the_instruction_gives_the_operator_work_and_names_the_workspace() -> None:
    text = (ROOT / "evals" / "tasks" / T3 / "instruction.md").read_text()
    assert "`/workspace` itself is the workspace folder" in text
    assert "`calc.py`" in text
    assert "`subtract`" in text
