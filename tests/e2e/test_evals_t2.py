"""T2 block-list bug (AC11.1): on each version the grader passes the planted correct fix and
fails the planted assert-rewriting one (``tests/fixtures/evals/t2/``).

Docker is required: a missing tool fails the row, never skips it. 600 s as in ``test_evals_t1``.

Owner: dd-software-engineer
"""

import pytest

from tests.helpers.evals import ROOT, T2, VERSIONS, reward

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.timeout(600)]

_PLANTS = ROOT / "tests" / "fixtures" / "evals" / "t2"


def _planted(version: str, *plants: str) -> str:
    script = "\n".join((_PLANTS / f"{p}.sh").read_text(encoding="utf-8") for p in plants)
    return reward(T2, version, script)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="AC11.1 evals/tasks/t2 (J9.S3)")
@pytest.mark.parametrize("version", VERSIONS)
def test_the_planted_correct_fix_passes(version: str) -> None:
    assert _planted(version, "correct-fix") == "1"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="AC11.1 evals/tasks/t2 (J9.S3)")
@pytest.mark.parametrize("version", VERSIONS)
def test_the_planted_assert_rewriting_fix_fails(version: str) -> None:
    assert _planted(version, "correct-fix", "assert-rewrite") == "0"
