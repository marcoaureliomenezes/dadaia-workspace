"""Preflight-vs-CI gating parity contract (bug `prepush-gate-omits-import-boundary-
contracts-ci-runs`, FR6/A6.2).

The pre-push hook advertises `dadaia ci preflight` as "CI-equivalent" (module docstring,
``dadaia_workspace/features/ci_preflight/service.py``; the hook's own echo line,
``public/scripts/pre-push-ci-gate.sh``). That claim is a promise: every check the local
preflight names is a check CI also gates on, and vice versa, over the SAME comparable
set — CI additionally gates matrix/e2e/panel/backlog/hygiene jobs that have no local
preflight equivalent at all (importability-smoke, e2e-panel, backlog-doctor,
repo-hygiene, pr-title, pr-source-guard, security-verdict-gate, verdict-gate); those are
OUT of the advertised equivalence claim by design and are never compared here.

This test derives BOTH sides mechanically instead of hardcoding a list twice:
  - LOCAL: ``checks_for()``'s returned ``Check.name`` values (the exact names the
    pre-push hook prints as ``[PASS]/[FAIL] <name>`` — the tool's own advertisement of
    what it just ran).
  - CI: ``.github/workflows/ci.yml``'s ``lint``/``typecheck`` job step names, plus a scan
    for a ``pytest`` invocation across the tiers that stand in for the local suite
    (``unit-fast``, ``contract-coverage``, ``integration``, ``e2e-python``).

Either side gaining or losing a check flips the set comparison and fails this test — this
is the regression pin bug `prepush-gate-omits-import-boundary-contracts-ci-runs` asks for
(A6.2), complementing the narrower unit-level pin in
``test_ci_preflight_includes_lint_imports.py`` (which proves lint-imports' argv and
fail-closed behaviour, not cross-source parity).

Mutation-sanity (verified by hand while authoring, not committed): commenting out the
``lint_imports`` line in ``checks_for()`` drops "lint-imports" from the LOCAL set and
makes the equality assertion below FAIL with an asymmetric-diff message naming the
missing check; removing the ``lint-imports`` step from ci.yml's ``lint`` job does the
same from the CI side.

Intent: CONTRACT — A6.2 (bug `prepush-gate-omits-import-boundary-contracts-ci-runs`)
Owner: software-engineer
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from dadaia_workspace.features.ci_preflight import checks_for

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CI_YML = _REPO_ROOT / ".github" / "workflows" / "ci.yml"

# The CI jobs that, together, stand in for what the local preflight advertises. Every
# OTHER ci.yml job (importability-smoke, unit-fast-cross, contract-coverage-cross,
# e2e-panel, pr-title, repo-hygiene, backlog-doctor, pr-source-guard,
# security-verdict-gate, verdict-gate) is CI-only scope the local gate never claimed
# equivalence to (module docstring: "ruff format --check, ruff check, mypy --strict,
# pytest" plus lint-imports — never the cross-platform matrix, panel E2E, or the
# governance/PR jobs).
_CI_EQUIVALENCE_JOBS = (
    "lint",
    "typecheck",
    "unit-fast",
    "contract-coverage",
    "integration",
    "e2e-python",
)

# canonical label -> substring that must appear in the LOCAL Check.name for that label.
_LOCAL_MARKERS: dict[str, str] = {
    "ruff-format": "ruff format --check",
    "ruff-check": "ruff check",
    "mypy-strict": "mypy --strict",
    "lint-imports": "lint-imports",
    "pytest": "pytest",
}

# canonical label -> substring that must appear in one of the CI job step run commands
# (or step names — ci.yml names its lint-imports step
# "lint-imports (import-boundary contracts)").
_CI_MARKERS: dict[str, str] = {
    "ruff-format": "ruff format --check",
    "ruff-check": "ruff check",
    "mypy-strict": "mypy --strict",
    "lint-imports": "lint-imports",
    "pytest": "pytest",
}


def _load_ci_jobs() -> dict[str, Any]:
    workflow = yaml.safe_load(_CI_YML.read_text(encoding="utf-8"))
    return cast("dict[str, Any]", workflow["jobs"])


def _ci_job_step_text(jobs: dict[str, Any], job_id: str) -> str:
    """Every step's ``name`` and ``run`` value for ``job_id``, joined into one haystack."""
    job = jobs[job_id]
    parts: list[str] = []
    for step in job.get("steps", []):
        name = step.get("name")
        if name:
            parts.append(str(name))
        run = step.get("run")
        if run:
            parts.append(str(run))
    return "\n".join(parts)


def _local_canonical_set() -> set[str]:
    """The canonical label set derived from ``checks_for()``'s advertised names.

    ``quick=True`` is the exact preflight the pre-push hook runs (``ci preflight
    --quick``); ``Check.name`` is independent of tool resolution (argv differs by
    environment, the name string does not), so no venv/DI faking is needed here.
    """
    names = " | ".join(c.name for c in checks_for(quick=True))
    return {label for label, marker in _LOCAL_MARKERS.items() if marker in names}


def _ci_canonical_set() -> set[str]:
    """The canonical label set derived from ci.yml's equivalence-scoped jobs."""
    jobs = _load_ci_jobs()
    haystack = "\n".join(_ci_job_step_text(jobs, job_id) for job_id in _CI_EQUIVALENCE_JOBS)
    return {label for label, marker in _CI_MARKERS.items() if marker in haystack}


def test_ci_equivalence_jobs_exist() -> None:
    """Sanity: every job this test compares against actually exists in ci.yml — a
    renamed/removed job silently emptying the CI-side haystack must be a loud failure,
    never a false-pass equality on two empty sets."""
    jobs = _load_ci_jobs()
    missing = [job_id for job_id in _CI_EQUIVALENCE_JOBS if job_id not in jobs]
    assert missing == [], f"ci.yml no longer defines job(s) {missing} — update _CI_EQUIVALENCE_JOBS"


def test_preflight_advertised_set_matches_ci_gating_set() -> None:
    """The preflight's advertised check list and CI's gating list are the same set
    (A6.2) — asymmetric on either side is a real regression, never a coincidence."""
    local_set = _local_canonical_set()
    ci_set = _ci_canonical_set()

    only_local = local_set - ci_set
    only_ci = ci_set - local_set

    assert only_local == set() and only_ci == set(), (
        "preflight/CI gating parity broken — the local preflight and ci.yml no longer "
        f"advertise the same check set. local-only: {sorted(only_local)!r} "
        f"(checks_for() claims a check CI does not gate); ci-only: {sorted(only_ci)!r} "
        "(ci.yml gates a check the local preflight omits — the exact shape of bug "
        "prepush-gate-omits-import-boundary-contracts-ci-runs: a push would go green "
        "locally and fail CI). Fix by adding the missing check to whichever side is "
        "short, not by shrinking the other."
    )
    # Both sides must be non-trivial — an empty intersection from a markers-vs-haystack
    # typo must not silently pass as "no diff".
    assert local_set == {"ruff-format", "ruff-check", "mypy-strict", "lint-imports", "pytest"}
