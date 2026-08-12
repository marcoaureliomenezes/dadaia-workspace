"""Unit tests for the pre-push preflight service (T-GATE-01)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from dadaia_workspace.features.ci_preflight import (
    all_passed,
    checks_for,
    failed_names,
    run_preflight,
)


def _pass(argv: Sequence[str]) -> tuple[int, str]:
    return 0, "ok"


@pytest.mark.parametrize(
    ("quick", "expected_last_name", "must_contain"),
    [
        pytest.param(
            False,
            "pytest",
            ("-m", "not quarantine"),
            id="full-has-lint-type-and-full-pytest",
        ),
        pytest.param(
            True,
            "pytest (no e2e)",
            ("-m", "not quarantine", "--ignore=tests/e2e"),
            id="quick-swaps-in-no-e2e-pytest",
        ),
    ],
)
def test_checks_for_lists(
    quick: bool, expected_last_name: str, must_contain: tuple[str, ...]
) -> None:
    checks = checks_for(quick=quick)
    names = [c.name for c in checks]
    assert names[:3] == ["ruff format --check", "ruff check", "mypy --strict"]
    assert names[-1] == expected_last_name
    for flag in must_contain:
        assert flag in checks[-1].argv


@pytest.mark.parametrize(
    ("runner", "fail_fast", "expected_len", "expected_failed"),
    [
        pytest.param(_pass, False, 5, [], id="all-pass"),
        pytest.param(
            "fail-fast-second",
            True,
            2,
            ["ruff check"],
            id="fail-fast-stops-at-first-failure",
        ),
        pytest.param(
            "mypy-fails",
            False,
            5,
            ["mypy --strict"],
            id="no-fail-fast-runs-every-check",
        ),
    ],
)
def test_run_preflight_matrix(
    runner: object, fail_fast: bool, expected_len: int, expected_failed: list[str]
) -> None:
    if runner == "fail-fast-second":
        calls: list[tuple[str, ...]] = []

        def _runner(argv: Sequence[str]) -> tuple[int, str]:
            calls.append(tuple(argv))
            return (1, "boom") if len(calls) == 2 else (0, "ok")

        results = run_preflight(checks_for(), _runner, fail_fast=fail_fast)
        assert len(calls) == 2  # later checks never ran
    elif runner == "mypy-fails":

        def _runner(argv: Sequence[str]) -> tuple[int, str]:
            # argv entries may be absolute tool paths (runner-derived resolution,
            # T-011-06) — match the tool by substring, not exact element.
            return (1, "boom") if any("mypy" in part for part in argv) else (0, "ok")

        results = run_preflight(checks_for(), _runner, fail_fast=fail_fast)
    else:
        results = run_preflight(checks_for(), runner, fail_fast=fail_fast)  # type: ignore[arg-type]

    assert len(results) == expected_len
    assert all_passed(results) == (expected_failed == [])
    assert failed_names(results) == expected_failed
    if expected_len == 5 and expected_failed == []:
        # all_passed is vacuously False for an empty result list, never true-by-default.
        assert all_passed([]) is False


def test_subprocess_runner_missing_binary_returns_127_not_traceback(tmp_path: Path) -> None:
    """A check whose binary is absent fails gracefully (127 + clean message), no traceback.

    Regression for ci-preflight-raw-traceback-when-poetry-absent (rc-4 / T-017-34).
    """
    from dadaia_workspace.features.ci_preflight.service import subprocess_runner

    run = subprocess_runner(tmp_path)
    code, out = run(("definitely-not-a-real-binary-xyz123", "run", "ruff"))
    assert code == 127
    assert "command not found" in out
    assert "definitely-not-a-real-binary-xyz123" in out
