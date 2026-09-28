"""Intent: CONTRACT — 0.4.7 FR3/AC3.1 (T-047-68): the doctor's `ledgers` section
delegates to each ledger's skill script instead of re-implementing its schema.

size: SMALL — a fake runner answers outside the `check` contract.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.ledger_scripts import LEDGER_SCRIPTS, script_findings


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
