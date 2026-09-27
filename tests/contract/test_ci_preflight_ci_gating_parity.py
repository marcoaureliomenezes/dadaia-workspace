"""Preflight-vs-CI gating parity contract (bug `prepush-gate-omits-import-boundary-
contracts-ci-runs`, FR6/A6.2).

`dadaia ci preflight` is the locally runnable subset of ci.yml (ADR 0078): every
check it names is gated in some ci.yml job and every locally runnable ci.yml check
(lint, types, import contracts, tests, the coverage floor, the doctor, repo hygiene) is
in ``checks_for()``. Both sides are derived: LOCAL from each ``Check``'s name and argv,
CI from the step names and ``run`` bodies of every ci.yml job.

Mutation-sanity (verified by hand while authoring, not committed): commenting out the
``lint_imports`` line in ``checks_for()`` drops "lint-imports" from the LOCAL set and
makes the equality assertion below FAIL with an asymmetric-diff message naming the
missing check; removing the ``lint-imports`` step from ci.yml's ``lint`` job does the
same from the CI side.

Intent: CONTRACT — A6.2 (bug `prepush-gate-omits-import-boundary-contracts-ci-runs`);
sa-doctor-job-not-a-required-check#B3
Owner: dd-software-engineer
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

# canonical label -> substring that must appear in the LOCAL Check.name for that label.
_LOCAL_MARKERS: dict[str, str] = {
    "ruff-format": "ruff format --check",
    "ruff-check": "ruff check",
    "mypy-strict": "mypy --strict",
    "lint-imports": "lint-imports",
    "pytest": "pytest",
    "coverage-floor": "--cov-fail-under=80",
    "doctor": "doctor --specs-dir specs --source-root .",
    "repo-hygiene": "check_no_repo_local_claude.sh",
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
    "coverage-floor": "--cov-fail-under=80",
    "doctor": "dadaia doctor --specs-dir specs --source-root .",
    "repo-hygiene": "check_no_repo_local_claude.sh",
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
    names = " | ".join(f"{c.name} {' '.join(c.argv)}" for c in checks_for(quick=True))
    return {label for label, marker in _LOCAL_MARKERS.items() if marker in names}


def _ci_canonical_set() -> set[str]:
    """The canonical label set derived from every ci.yml job."""
    jobs = _load_ci_jobs()
    haystack = "\n".join(_ci_job_step_text(jobs, job_id) for job_id in jobs)
    return {label for label, marker in _CI_MARKERS.items() if marker in haystack}


def test_preflight_advertised_set_matches_ci_gating_set() -> None:
    """sa-doctor-job-not-a-required-check#B3: checks_for() carries every locally runnable
    ci.yml check — the coverage floor, the doctor and repo hygiene included (A6.2)."""
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
    assert local_set == set(_LOCAL_MARKERS)


def test_consumer_law_never_prescribes_the_library_preflight() -> None:
    """sa-doctor-job-not-a-required-check#B5: `ci preflight` refuses outside the library, so
    the consumer law (dd-gitflow-default, dd-release-implementation) sends an agent to its
    own repo's checks, never to that verb."""
    skills = _REPO_ROOT / "dadaia_workspace" / "public" / "skills"
    law = [
        p
        for s in ("dd-gitflow-default", "dd-release-implementation")
        for p in (skills / s).rglob("*.md")
    ]
    offenders = [str(p) for p in law if "ci preflight" in p.read_text(encoding="utf-8")]
    assert offenders == []
