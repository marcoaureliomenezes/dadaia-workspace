"""The doctor's `ledgers` section delegates to each ledger's skill script.

Intent: CONTRACT — 0.4.7 AC3.1.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.ledger_scripts import LEDGER_SCRIPTS, script_findings


def test_an_uninstalled_script_is_one_finding_naming_public_install(tmp_path: Path) -> None:
    """A script that cannot run is one error finding per ledger whose fix names `public install`."""
    specs = tmp_path / "bare" / "specs"
    specs.mkdir(parents=True)
    findings = script_findings(specs, runner=_BrokenRunner())
    assert {f.code for f in findings} == {s.code for s in LEDGER_SCRIPTS}
    assert all(f.error and "public install" in f.fix for f in findings)


class _BrokenRunner:
    def run(self, argv: object, *, cwd: object = None, timeout: float | None = None) -> object:
        class _Result:
            returncode = 2
            stdout = "Traceback (most recent call last):"
            stderr = ""

        return _Result()
