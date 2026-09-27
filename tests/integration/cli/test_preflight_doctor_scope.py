"""The preflight's doctor step judges what CI's Compliance job judges — the repo's specs and
ledgers — never the workspace enclosing the checkout.

Intent: CONTRACT — preflight-doctor-judges-instance-state-ci-never-sees; size: MEDIUM (real
subprocess doctor over a tmp workspace).
"""

from __future__ import annotations

import os
from pathlib import Path

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


def test_an_expired_entry_of_the_enclosing_workspace_never_fails_the_doctor_step(
    tmp_path: Path,
) -> None:
    """RED: the step used to resolve the enclosing workspace and fail on its WS-* hygiene."""
    code, output = _doctor_step(_checkout_inside_a_stale_workspace(tmp_path))
    assert code == 0, output
    assert "WS-" not in output


def test_a_specs_error_in_the_repo_still_fails_the_doctor_step(tmp_path: Path) -> None:
    checkout = _checkout_inside_a_stale_workspace(tmp_path)
    (checkout / "specs" / "constitution.md").unlink()
    code, output = _doctor_step(checkout)
    assert code == 1, output
    assert "constitution.md" in output
