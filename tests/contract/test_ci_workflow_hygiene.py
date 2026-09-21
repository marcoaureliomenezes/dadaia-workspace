"""Intent: CONTRACT — T-047-82: the release workflow publishes the built skills
repository and fails closed on the missing SKILLS_REPO_TOKEN secret, with the token
never interpolated outside the push remote URL. Size: SMALL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.contract

_RELEASE_YML = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "release.yml"
_TOKEN = "SKILLS_REPO_TOKEN"
_REMOTE_PREFIX = "https://x-access-token:"


def _jobs() -> dict[str, Any]:
    return dict(yaml.safe_load(_RELEASE_YML.read_text(encoding="utf-8"))["jobs"])


def _skills_job() -> tuple[str, dict[str, Any]]:
    candidates = [
        (name, job)
        for name, job in _jobs().items()
        if any("build-skills-repo.py" in (step.get("run") or "") for step in job.get("steps") or [])
    ]
    assert len(candidates) == 1, (
        f"expected exactly one release job building the skills repository, got {[n for n, _ in candidates]}"
    )
    return candidates[0]


def test_skills_repo_job_runs_after_publish_and_builds_the_repository() -> None:
    name, job = _skills_job()
    needs = job.get("needs") or []
    needs = [needs] if isinstance(needs, str) else list(needs)
    assert "publish" in needs, f"job {name} must depend on the publish job, needs={needs}"
    build = next(s for s in job["steps"] if "build-skills-repo.py" in (s.get("run") or ""))
    assert "dadaia_workspace/public/scripts/build-skills-repo.py" in build["run"]
    assert job.get("permissions") == {"contents": "read"}, (
        f"job {name} must declare minimal permissions; got {job.get('permissions')}"
    )


def test_missing_skills_repo_token_fails_closed_with_one_error_annotation() -> None:
    name, job = _skills_job()
    assert (job.get("env") or {}).get(_TOKEN) == "${{ secrets." + _TOKEN + " }}"
    guards = [s for s in job["steps"] if f"env.{_TOKEN} == ''" in str(s.get("if") or "")]
    assert len(guards) == 1, (
        f"job {name} must carry exactly one fail-closed guard, got {len(guards)}"
    )
    run = guards[0]["run"]
    assert run.count("::error::") == 1, f"the guard must emit exactly one annotation: {run!r}"
    assert _TOKEN in run and "exit 1" in run


def test_the_token_is_interpolated_only_in_the_push_remote_url() -> None:
    offenders: list[str] = []
    for job_name, job in _jobs().items():
        for step in job.get("steps") or []:
            for line in (step.get("run") or "").splitlines():
                if _TOKEN not in line:
                    continue
                guard = f"env.{_TOKEN} == ''" in str(step.get("if") or "")
                if guard or f"{_REMOTE_PREFIX}${{{_TOKEN}}}" in line:
                    continue
                offenders.append(f"{job_name}: {line.strip()}")
    assert offenders == [], (
        f"{_TOKEN} may appear only inside the {_REMOTE_PREFIX} remote URL or the "
        f"fail-closed guard — never echoed or logged: {offenders}"
    )


def test_no_run_body_of_the_skills_job_interpolates_a_workflow_expression() -> None:
    """A workflow expression pasted into a shell body is the template-injection shape;
    the version travels through the job env and is read as "$VERSION"."""
    name, job = _skills_job()
    offenders = [
        (step.get("name"), line.strip())
        for step in job["steps"]
        for line in (step.get("run") or "").splitlines()
        if "${{" in line
    ]
    assert offenders == [], (
        f"job {name} must pass every workflow expression through env:, not a run body: {offenders}"
    )
