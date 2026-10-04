"""One `dadaia doctor`: three sections over one rule registry (0.4.7 FR5 / T-047-02).

T-047-02: `dadaia doctor` renders `workspace`, `specs` and
`ledgers` in that order, one line `<CODE> <verdict> <message>` per finding; a release
state defect is release.py check's one finding (ADR 0077); and the two commands this one
replaces (`specs doctor`, `backlog doctor`) no longer exist.
Size: SMALL — Typer CliRunner over tmp_path trees plus one in-process run over this
repo's own specs/; no subprocess, no network.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.help_digest import command_paths
from dadaia_workspace.cli.main import app

pytestmark = pytest.mark.contract

_runner = CliRunner()
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SECTIONS = ("workspace", "specs", "ledgers")


def _run(*args: str) -> Any:
    return _runner.invoke(app, ["doctor", *args])


def test_every_human_line_is_a_finding_or_its_fix() -> None:
    """Every stdout line is `<CODE> <verdict> <message>` or a `fix: <command>` line —
    no score line, no header, nothing else."""
    result = _run("--specs-dir", str(_REPO_ROOT / "specs"))
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        assert line.startswith("fix: ") or re.match(r"^[A-Za-z][A-Za-z0-9-]+ [a-z]+ ", line), line


def test_json_carries_every_section() -> None:
    result = _run("--specs-dir", str(_REPO_ROOT / "specs"), "--json")
    payload = json.loads(result.stdout)
    assert set(payload["sections"]) == set(_SECTIONS)
    for name in _SECTIONS:
        section = payload["sections"][name]
        for finding in section["findings"]:
            assert set(finding) >= {"code", "verdict", "message"}
    assert "compliance" not in payload
    assert "fixed" in payload


def _live_release(specs: Path, **over: Any) -> Path:
    """A live 0.5.0 in DEFINITION, one field broken by the caller."""
    release_dir = specs / "releases" / "0.5.0"
    release_dir.mkdir(parents=True)
    state = {"schema": "release-state-v1", "release": "0.5.0", "phase": "DEFINITION",
             "defined": None, "implemented": None, "shipped": None, "log": [], **over}  # fmt: skip
    (release_dir / "_RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", "utf-8")
    return release_dir / "_RELEASE.json"


def _release_findings(specs: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """(the doctor's findings naming the release state, every specs-section code)."""
    payload = json.loads(_run("--specs-dir", str(specs), "--json").stdout)
    sections = payload["sections"]
    named = [f for s in sections.values() for f in s["findings"] if "_RELEASE.json" in f["message"]]
    return named, [f["code"] for f in sections["specs"]["findings"]]


def test_a_mis_cased_phase_is_one_finding_whose_fix_clears_it(tmp_path: Path) -> None:
    """sa-release-json-validated-three-times#B1: phase 'closure' yields exactly one
    finding, whose fix is ADR 0158's `Operator action:` naming the file, the keys its message names and the law
    (AC4.5); the repair clears it."""
    state = _live_release(tmp_path / "specs", phase="closure")
    named, _ = _release_findings(tmp_path / "specs")
    assert len(named) == 1 and named[0]["code"] == "LEDGER-RELEASE-SCHEMA", named
    assert named[0]["fix"].startswith(
        f"Operator action: {state.resolve()} fails at the keys this finding names "
    ), named
    assert f"`git log -p -- {state.resolve()}`" in named[0]["fix"], named
    state.write_text(state.read_text("utf-8").replace('"closure"', '"CLOSURE"'), "utf-8")
    assert not [f for f in _release_findings(tmp_path / "specs")[0] if "'closure'" in f["message"]]


@pytest.mark.parametrize(
    "over",
    [
        {"release": 5},
        {"extra": 1},
        {"phase": "WORKING"},
        {"defined": {"sha": "x"}},
        {
            "log": [
                {"ts": "2", "agent": "a", "kind": "note", "text": "t"},
                {"ts": "1", "agent": "a", "kind": "note", "text": "t"},
            ]
        },
    ],  # fmt: skip
)
def test_doctor_release_findings_are_the_scripts(tmp_path: Path, over: dict[str, Any]) -> None:
    """sa-release-json-validated-three-times#B2: the doctor's release findings are
    release.py check's (LEDGER-RELEASE-SCHEMA); no RELEASE-TREE-* or SPEC-DOC-003/009."""
    _live_release(tmp_path / "specs", **over)
    named, specs_codes = _release_findings(tmp_path / "specs")
    script = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "dadaia_workspace/public/skills/dd-release-implementation"
                             "/scripts/release.py"), "check", "--specs", str(tmp_path / "specs"),
         "--json"], capture_output=True, text=True, check=False)  # fmt: skip
    expected = [f"{f['path']}:{f['line']} {f['message']}" for f in json.loads(script.stdout)]
    assert expected and [f["message"] for f in named] == expected
    assert {f["code"] for f in named} == {"LEDGER-RELEASE-SCHEMA"}
    assert not [
        c
        for c in specs_codes
        if c.startswith("RELEASE-TREE") or c in ("SPEC-DOC-003", "SPEC-DOC-009")
    ]


def test_specs_doctor_and_backlog_doctor_commands_are_gone() -> None:
    """(c) the two replaced commands are DELETED, not aliased — no hidden survivor in
    the Typer tree, and therefore none in the backlog subject registry's CLI anchors."""
    anchors = {" ".join(p) for p in command_paths()}
    assert "specs doctor" not in anchors
    assert "backlog doctor" not in anchors
    assert "doctor" in anchors
    for group, verb in (("specs", "doctor"), ("backlog", "doctor")):
        result = _runner.invoke(app, [group, verb, "--help"])
        assert result.exit_code != 0, f"`dadaia {group} {verb}` still resolves"
