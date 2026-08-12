"""Every CI/release pytest --cov step must redirect COVERAGE_FILE out of the checkout.

Bug release-workflow-coverage-file-in-checkout: pyproject's coverage ``data_file`` was
removed in T-018-07 with the contract that WORKFLOWS redirect the data file to the
runner temp dir. ci.yml honoured it; release.yml's contract-coverage job did not, so
``.coverage`` landed inside the repo checkout on every release run — the exact
artifact class the "repos stay clean" law forbids. Two hand-maintained workflow files
drifted apart; this contract pins them together.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def test_every_pytest_cov_step_redirects_coverage_file() -> None:
    offenders: list[str] = []
    workflow_files = sorted(_WORKFLOWS_DIR.glob("*.yml"))
    assert workflow_files, f"no workflow files found under {_WORKFLOWS_DIR}"
    for workflow_path in workflow_files:
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        for job_name, job in (workflow.get("jobs") or {}).items():
            job_env = job.get("env") or {}
            for step in job.get("steps") or []:
                run = step.get("run") or ""
                if "pytest" not in run or "--cov" not in run:
                    continue
                step_env = step.get("env") or {}
                coverage_file = step_env.get("COVERAGE_FILE") or job_env.get("COVERAGE_FILE")
                if not coverage_file or "runner.temp" not in str(coverage_file):
                    offenders.append(f"{workflow_path.name}:{job_name}")
    assert offenders == [], (
        "pytest --cov steps without a COVERAGE_FILE redirect to runner.temp — "
        f".coverage would be written into the checkout: {offenders}"
    )
