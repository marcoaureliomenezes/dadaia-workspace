"""The preflight's doctor step judges what CI's Compliance job judges — the repo's specs and
ledgers — never the workspace enclosing the checkout.

Intent: CONTRACT — preflight-doctor-judges-instance-state-ci-never-sees; size: MEDIUM (real
subprocess doctor over a tmp workspace).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dadaia_workspace.features.ci_preflight import checks_for, subprocess_runner
from dadaia_workspace.features.specs.canon import scaffold
from dadaia_workspace.infrastructure.ledger_scripts import script_repairs


def _checkout_inside_a_stale_workspace(tmp_path: Path) -> Path:
    """A workspace holding an expired tmp entry, and a checkout with a clean specs tree."""
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text('{"schema_version": "2", "contexts": []}\n')
    stale = tmp_path / ".dadaia" / "tmp" / "zz-probe" / "20200101"
    stale.mkdir(parents=True)
    (stale / "scratch.txt").write_text("old probe\n", encoding="utf-8")
    for path in (stale / "scratch.txt", stale, stale.parent):
        os.utime(path, (0, 0))
    checkout = tmp_path / "repos" / "lib"
    scaffold(checkout / "specs", project_name="lib")
    script_repairs(checkout / "specs")
    return checkout


def _doctor_step(checkout: Path) -> tuple[int, str]:
    doctor = next(check for check in checks_for(quick=True) if check.name == "dadaia doctor")
    return subprocess_runner(checkout)(doctor.argv)


@pytest.mark.parametrize(
    ("break_specs", "code"), [(False, 0), (True, 1)], ids=["clean-repo", "specs-error"]
)
def test_the_doctor_step_judges_the_repo_never_the_enclosing_workspace(
    tmp_path: Path, break_specs: bool, code: int
) -> None:
    """RED: the step used to resolve the enclosing workspace and fail on its WS-* hygiene;
    a specs error in the repo itself still fails it."""
    checkout = _checkout_inside_a_stale_workspace(tmp_path)
    if break_specs:
        (checkout / "specs" / "constitution.md").unlink()
    exit_code, output = _doctor_step(checkout)
    assert exit_code == code and "WS-" not in output, output
    assert break_specs is ("constitution.md" in output)
