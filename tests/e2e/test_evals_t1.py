"""T1 cold onboarding (AC11.1): each image builds on the 0.4.7 layer and on this checkout's wheel;
the grader passes a hand-onboarded workspace of each version and fails an empty one.

Docker is required: a missing tool fails the row, never skips it. 600 s: evals' whole suite, with
four image builds, took 95 s on ubuntu-24.04 (run 37554712931).

Owner: dd-software-engineer
"""

import pytest

from tests.helpers.evals import HAND, T1, VERSIONS, image, reward

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.timeout(600)]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="AC11.1 evals/tasks/t1 (J9.S3)")
@pytest.mark.parametrize("version", VERSIONS)
def test_the_image_builds_on_each_version(version: str) -> None:
    assert image(T1, version) == f"dadaia-evals-{T1}:{version}"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="AC11.1 evals/tasks/t1 (J9.S3)")
@pytest.mark.parametrize("version", VERSIONS)
def test_the_grader_passes_a_hand_onboarded_workspace(version: str) -> None:
    assert reward(T1, version, HAND[version]) == "1"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="AC11.1 evals/tasks/t1 (J9.S3)")
@pytest.mark.parametrize("version", VERSIONS)
def test_the_grader_fails_an_empty_workspace(version: str) -> None:
    assert reward(T1, version, "true") == "0"
