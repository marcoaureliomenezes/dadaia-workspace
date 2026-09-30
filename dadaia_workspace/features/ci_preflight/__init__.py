"""Local CI-equivalent preflight gate (T-GATE-01).

Runs the locally runnable subset of ci.yml (lint, types, hygiene, doctor, import
contracts, tests with the coverage floor); `.github/required-checks.json` gates a merge.
"""

from dadaia_workspace.features.ci_preflight.service import (
    Check,
    CheckResult,
    Runner,
    all_passed,
    checks_for,
    failed_names,
    run_preflight,
    subprocess_runner,
)

__all__ = [
    "Check",
    "CheckResult",
    "Runner",
    "all_passed",
    "checks_for",
    "failed_names",
    "run_preflight",
    "subprocess_runner",
]
