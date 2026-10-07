"""AC6.1 (ADR 0209): a strict xfail is this repo's RED marker and expects an assertion failure
only — a RED test that errors fails its stage instead of passing as an expected failure.
Size: MEDIUM (a nested pytest run).
"""

from __future__ import annotations

import importlib.util

import pytest

RED_FILE = """
import pytest

@pytest.mark.xfail(strict=True, reason="red")
def test_fails_by_assertion():
    assert 0

@pytest.mark.xfail(strict=True, reason="red")
def test_errors():
    undefined_name
"""


def test_a_red_test_that_errors_fails_while_one_that_asserts_xfails(
    pytester: pytest.Pytester,
) -> None:
    assert importlib.util.find_spec("tests.fixtures.red_marker")
    pytester.makepyfile(RED_FILE)
    result = pytester.runpytest("-p", "tests.fixtures.red_marker", "-p", "no:cacheprovider")
    result.assert_outcomes(xfailed=1, failed=1)
