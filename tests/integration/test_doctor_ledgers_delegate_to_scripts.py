"""Intent: CONTRACT — 0.4.7 FR3/AC3.1 (T-047-68): the doctor's `ledgers` section
delegates to each ledger's skill script instead of re-implementing its schema.

A hand-corrupted `BUGS.jsonl` in a tmp workspace must yield exactly ONE
`LEDGER-BUGS-SCHEMA` line, and its `fix:` must name the script that owns the ledger —
not a retired `dadaia bugs` verb, and not a second validator living in the doctor.

size: MEDIUM — it runs the real scripts as subprocesses, which is the seam under test.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app as cli_app
from dadaia_workspace.infrastructure.ledger_scripts import LEDGER_SCRIPTS, script_findings
from dadaia_workspace.infrastructure.public_assets import _SKILL_SCRIPT_SCHEMAS

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"
_runner = CliRunner()


def _install_skills(workspace: Path) -> None:
    """Build the installed skills tree the way `public install` does:
    every script plus the shipped schema copied beside it."""
    skills = workspace / ".agents" / "skills"
    for script in LEDGER_SCRIPTS:
        shutil.copytree(
            _PUBLIC / "skills" / script.skill / "scripts",
            skills / script.skill / "scripts",
            dirs_exist_ok=True,
        )
    for schema_rel, scripts_rel in _SKILL_SCRIPT_SCHEMAS:
        destination = skills.parent / scripts_rel / Path(schema_rel).name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_PUBLIC / schema_rel, destination)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    _install_skills(tmp_path)
    (tmp_path / "specs" / "bugs").mkdir(parents=True)
    return tmp_path


def _corrupt(workspace: Path) -> None:
    (workspace / "specs" / "bugs" / "BUGS.jsonl").write_text("{not a record\n", encoding="utf-8")


def test_a_corrupted_bugs_ledger_yields_one_finding_whose_fix_names_the_script(
    workspace: Path,
) -> None:
    _corrupt(workspace)
    findings = script_findings(workspace / "specs")
    bugs = [f for f in findings if f.code == "LEDGER-BUGS-SCHEMA"]
    assert len(bugs) == 1, findings
    assert bugs[0].error
    assert "bugs.py" in bugs[0].fix, bugs[0].fix
    assert "dadaia bugs" not in bugs[0].fix


def test_an_uninstalled_script_is_one_finding_naming_public_install(tmp_path: Path) -> None:
    """A script that cannot run is ONE finding with a runnable fix — never a traceback
    and never silence (the structural cause of the doctor bug family: a record class
    nobody reads)."""
    specs = tmp_path / "bare" / "specs"
    specs.mkdir(parents=True)
    findings = script_findings(specs, runner=_BrokenRunner())
    assert {f.code for f in findings} == {s.code for s in LEDGER_SCRIPTS}
    assert all(f.error and "public install" in f.fix for f in findings)


class _BrokenRunner:
    """A script that answers outside the `check` contract (exit 2, no JSON)."""

    def run(self, argv: object, *, cwd: object = None, timeout: float | None = None) -> object:
        class _Result:
            returncode = 2
            stdout = "Traceback (most recent call last):"
            stderr = ""

        return _Result()


def test_the_doctor_prints_the_delegated_finding(workspace: Path) -> None:
    _corrupt(workspace)
    run = _runner.invoke(cli_app, ["doctor", "--specs-dir", str(workspace / "specs")])
    lines = [line for line in run.output.splitlines() if line.startswith("LEDGER-BUGS-SCHEMA")]
    assert len(lines) == 1, run.output
    assert run.exit_code == 1
