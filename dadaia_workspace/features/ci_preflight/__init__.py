"""Local CI-equivalent preflight gate (T-GATE-01).

Runs the same checks CI enforces — ruff format, ruff check, mypy --strict,
pytest — so locally-solvable failures never reach a push.
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
