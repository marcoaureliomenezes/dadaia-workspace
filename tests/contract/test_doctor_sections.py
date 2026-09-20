"""One `dadaia doctor`: three sections over one rule registry (0.4.7 FR5 / T-047-02).

Intent: CONTRACT — T-047-02: `dadaia doctor` renders `workspace`, `specs` and
`ledgers` in that order, one line `<CODE> <verdict> <message>` per finding, a
`compliance(<section>)` line per section and one `compliance(total)` line; the
`specs` section carries the release-tree rule (bug
`archived-release-state-invalid-and-unparseable-doctor-silent`), so a tree holding
the pre-Wave-0 0.4.6 document scores below 100 % and exits 1; and the two commands
this one replaces (`specs doctor`, `backlog doctor`) no longer exist.
Size: SMALL — Typer CliRunner over tmp_path trees plus one in-process run over this
repo's own specs/; no subprocess, no network.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.anchors import derive_cli_anchors
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
    result = _run("--specs-dir", str(_REPO_ROOT / "specs"), "--source-root", str(_REPO_ROOT))
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        assert line.startswith("fix: ") or re.match(r"^[A-Za-z][A-Za-z0-9-]+ [a-z]+ ", line), line


def test_json_carries_every_section() -> None:
    result = _run(
        "--specs-dir", str(_REPO_ROOT / "specs"), "--source-root", str(_REPO_ROOT), "--json"
    )
    payload = json.loads(result.stdout)
    assert set(payload["sections"]) == set(_SECTIONS)
    for name in _SECTIONS:
        section = payload["sections"][name]
        for finding in section["findings"]:
            assert set(finding) >= {"code", "verdict", "message"}
    assert "compliance" not in payload
    assert "fixed" in payload


def _pre_wave0_046_document() -> dict[str, Any]:
    """The 0.4.6 archived state as committed before Wave 0 — `shipped` without `pr`
    (`git show 7db9553c^:specs/releases/_archive/0.4.6/_RELEASE.json`)."""
    return {
        "schema": "release-state-v1",
        "release": "0.4.6",
        "phase": "ARCHIVED",
        "rc": 3,
        "defined": {"sha": "a" * 40, "ts": "2026-09-01T00:00:00Z"},
        "implemented": {"sha": "b" * 40, "rc": 3, "ts": "2026-09-05T00:00:00Z"},
        "shipped": {"sha": "c" * 40, "ts": "2026-09-06T15:05:36Z"},
        "log": [
            {
                "ts": "2026-09-01T00:00:00Z",
                "agent": "product-engineer",
                "kind": "note",
                "text": "x",
            }
        ],
    }


def test_pre_wave0_release_document_makes_the_specs_section_non_compliant(
    tmp_path: Path,
) -> None:
    """(b) the invalid archived document every doctor was silent about is a
    RELEASE-TREE-* error and the run exits 1."""
    specs = tmp_path / "specs"
    archived = specs / "releases" / "_archive" / "0.4.6"
    archived.mkdir(parents=True)
    (archived / "_RELEASE.json").write_text(
        json.dumps(_pre_wave0_046_document(), indent=2) + "\n", encoding="utf-8"
    )

    result = _run("--specs-dir", str(specs), "--source-root", str(_REPO_ROOT), "--json")
    payload = json.loads(result.stdout)
    specs_section = payload["sections"]["specs"]

    codes = [f["code"] for f in specs_section["findings"]]
    assert any(c.startswith("RELEASE-TREE-") for c in codes), codes
    assert result.exit_code == 1


def test_specs_doctor_and_backlog_doctor_commands_are_gone() -> None:
    """(c) the two replaced commands are DELETED, not aliased — no hidden survivor in
    the Typer tree, and therefore none in the backlog subject registry's CLI anchors."""
    anchors = derive_cli_anchors()
    assert "specs doctor" not in anchors
    assert "backlog doctor" not in anchors
    assert "doctor" in anchors
    for group, verb in (("specs", "doctor"), ("backlog", "doctor")):
        result = _runner.invoke(app, [group, verb, "--help"])
        assert result.exit_code != 0, f"`dadaia {group} {verb}` still resolves"
