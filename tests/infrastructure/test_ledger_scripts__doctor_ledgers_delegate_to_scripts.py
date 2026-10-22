"""The doctor's `ledgers` section delegates to each ledger's skill script."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.infrastructure.ledger_scripts import LEDGER_SCRIPTS, script_findings
from tests.helpers.oslib import write_text


def test_an_uninstalled_script_is_one_finding_carrying_the_owners_projected_act(
    tmp_path: Path,
) -> None:
    """A script that cannot run is one error finding per ledger whose fix is the owner's act
    for a projected file, taken from the specs' own workspace."""
    write_text(tmp_path / ".dadaia" / "states" / "spec_contexts.json", "{}")
    specs = tmp_path / "specs"
    specs.mkdir()
    findings = script_findings(specs, runner=_BrokenRunner())
    assert {f.code for f in findings} == {s.code for s in LEDGER_SCRIPTS}
    want = load_owner("dd-bug-resolution", "_jsonl").reinstall_fix(specs, projected=True)
    assert all(f.error and f.fix == want for f in findings)


def test_outside_a_workspace_the_unrunnable_fix_is_the_init_act(tmp_path: Path) -> None:
    specs = tmp_path / "bare" / "specs"
    specs.mkdir(parents=True)
    findings = script_findings(specs, runner=_BrokenRunner())
    assert {f.fix for f in findings} == {
        "Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument"
    }


class _BrokenRunner:
    def run(self, argv: object, *, cwd: object = None, timeout: float | None = None) -> object:
        class _Result:
            returncode = 2
            stdout = "Traceback (most recent call last):"
            stderr = ""

        return _Result()


def test_a_script_refusal_forwards_its_own_fix_line(tmp_path: Path) -> None:
    """A script that refuses with its own `fix:` line has that line on the finding, not
    `public install`."""
    specs = tmp_path / "bare" / "specs"
    specs.mkdir(parents=True)
    findings = script_findings(specs, runner=_RefusingRunner())
    assert {f.fix for f in findings} == {"python3 do-the-thing"}


class _RefusingRunner:
    def run(self, argv: object, *, cwd: object = None, timeout: float | None = None) -> object:
        class _Result:
            returncode = 1
            stdout = ""
            stderr = "no specs tree\nfix: python3 do-the-thing\n"

        return _Result()
