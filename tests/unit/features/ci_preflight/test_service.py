"""Unit tests for the pre-push preflight service (T-GATE-01)."""

from __future__ import annotations

from collections.abc import Sequence

from dadaia_workspace.features.ci_preflight import (
    all_passed,
    checks_for,
    failed_names,
    run_preflight,
)


def _pass(argv: Sequence[str]) -> tuple[int, str]:
    return 0, "ok"


def test_checks_for_full_has_lint_type_and_full_pytest() -> None:
    names = [c.name for c in checks_for(quick=False)]
    assert names[:3] == ["ruff format --check", "ruff check", "mypy --strict"]
    assert names[-1] == "pytest"


def test_checks_for_quick_swaps_in_no_e2e_pytest() -> None:
    names = [c.name for c in checks_for(quick=True)]
    assert names[:3] == ["ruff format --check", "ruff check", "mypy --strict"]
    assert names[-1] == "pytest (no e2e)"


def test_run_preflight_all_pass() -> None:
    results = run_preflight(checks_for(), _pass)
    assert len(results) == 4
    assert all_passed(results)
    assert failed_names(results) == []


def test_fail_fast_stops_at_first_failure() -> None:
    calls: list[tuple[str, ...]] = []

    def runner(argv: Sequence[str]) -> tuple[int, str]:
        calls.append(tuple(argv))
        return (1, "boom") if len(calls) == 2 else (0, "ok")

    results = run_preflight(checks_for(), runner, fail_fast=True)

    assert len(results) == 2  # stopped right after the failing 2nd check
    assert len(calls) == 2  # later checks never ran
    assert not all_passed(results)
    assert failed_names(results) == ["ruff check"]


def test_no_fail_fast_runs_every_check() -> None:
    def runner(argv: Sequence[str]) -> tuple[int, str]:
        return (1, "boom") if "mypy" in argv else (0, "ok")

    results = run_preflight(checks_for(), runner, fail_fast=False)

    assert len(results) == 4
    assert not all_passed(results)
    assert failed_names(results) == ["mypy --strict"]


def test_all_passed_is_false_for_empty() -> None:
    assert all_passed([]) is False
