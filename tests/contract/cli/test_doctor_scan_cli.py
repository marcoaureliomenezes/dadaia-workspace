"""Intent: CONTRACT — 0.4.6 AC2, AC4 (the `dadaia doctor` surface: finding lines, score line,
exit code, `--json`, `--fix --expired-only --quiet`); size: SMALL.

The CLI renders what ``DoctorService.scan()``/``fix()`` return — nothing here re-tests the
walk (``tests/unit/test_spec_context_doctor_root.py``); it pins the shapes SPEC §3 names:
one ``WS-<zone>-<verdict> <path>  (<detail>)`` line per non-canonical entry, the section
score line, exit 1 on any slop/expired/missing, the `--json` section shape, and a quiet lane
that speaks only when it deleted something.

0.4.7 T-047-02 folded the three doctors into one: the same findings now render inside the
`workspace` SECTION of ``dadaia doctor`` (`<CODE> <verdict> <message>`, then
``compliance(workspace): …``), and `--json` nests them under ``sections.workspace``. The
walk, the verdict vocabulary and the exit rule are unchanged.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.workspace_layout import Creator, zones_created_by, zones_with_ttl
from dadaia_workspace.features.spec_context.doctor import DoctorService
from tests.fakes import FakeContextStore, FakeGitClient

pytestmark = pytest.mark.contract

_TTL_ZONE = zones_with_ttl()[0]
_EXPIRED_CODE = f"WS-{_TTL_ZONE.name.lstrip('.')}-expired"
_FINDING_LINE = re.compile(
    r"^WS-[a-z.-]+-(slop|expired|missing) (slop|expired|missing) \S+  \(.+\)$"
)
_SCORE_LINE = re.compile(r"^compliance\(workspace\): [0-9]+/[0-9]+ entries canonical \([0-9]+%\)$")


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dadaia = tmp_path / ".dadaia"
    for zone in (*zones_created_by(Creator.INIT), *zones_created_by(Creator.INSTALL)):
        (dadaia / zone.name).mkdir(parents=True, exist_ok=True)
    (dadaia / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}', encoding="utf-8"
    )
    # FR8: a healthy states/ carries the profile; absent it is WS-states-missing.
    (dadaia / "states" / "harness_profile.json").write_text(
        json.dumps({"schema_version": "1", "harnesses": list(L1_ENTRY_HARNESSES)}),
        encoding="utf-8",
    )
    # ... and the install ledger: absent, the harness dirs are never classified.
    (dadaia / "states" / "install_ledger.json").write_text(
        json.dumps({"schema_version": "1", "entries": []}), encoding="utf-8"
    )
    (tmp_path / "repos").mkdir()
    (tmp_path / "AGENTS.md").write_text("# agents", encoding="utf-8")
    venv_bin = dadaia / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True)
    entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n", encoding="utf-8")
    entry.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        container,
        "build_doctor_service",
        lambda root: DoctorService(FakeContextStore(), FakeGitClient(), root),
    )
    return tmp_path


def _plant_expired(workspace: Path) -> Path:
    zone_dir = workspace / ".dadaia" / _TTL_ZONE.name
    zone_dir.mkdir(exist_ok=True)
    stale = zone_dir / "stale"
    stale.write_text("", encoding="utf-8")
    two_days_ago = time.time() - 2 * 86_400
    os.utime(stale, (two_days_ago, two_days_ago))
    return stale


def test_lists_findings_then_the_score_line_and_exits_1(workspace: Path) -> None:
    (workspace / "junk.txt").write_text("", encoding="utf-8")
    _plant_expired(workspace)

    result = CliRunner().invoke(app, ["doctor"])
    lines = result.output.splitlines()

    assert result.exit_code == 1, result.output
    finding_lines = [ln for ln in lines if ln.startswith("WS-")]
    assert len(finding_lines) == 2
    assert all(_FINDING_LINE.match(ln) for ln in finding_lines), finding_lines
    score_lines = [ln for ln in lines if _SCORE_LINE.match(ln)]
    assert len(score_lines) == 1, lines


def test_healthy_workspace_exits_0_with_a_full_score(workspace: Path) -> None:
    result = CliRunner().invoke(app, ["doctor"])
    lines = result.output.splitlines()

    assert result.exit_code == 0, result.output
    assert [ln for ln in lines if _SCORE_LINE.match(ln)][0].endswith("(100%)")
    assert not any(ln.startswith("WS-") for ln in lines)


def test_json_carries_findings_compliance_and_fixed(workspace: Path) -> None:
    (workspace / "junk.txt").write_text("", encoding="utf-8")

    result = CliRunner().invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)

    assert result.exit_code == 1
    assert {"sections", "compliance", "fixed"} <= set(payload)
    workspace_section = payload["sections"]["workspace"]
    assert workspace_section["findings"] == [
        {
            "code": "WS-root-slop",
            "verdict": "slop",
            "message": "junk.txt  (not in the root law or the exceptions)",
            "fix": ".dadaia/.venv/bin/dadaia doctor --fix",
        }
    ]
    assert set(workspace_section["compliance"]) == {"canonical", "total", "percent"}
    assert set(payload["compliance"]) == {"canonical", "total", "percent"}
    assert payload["fixed"] == []


@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0,
    reason="chmod 0o555 denies unlink only for a non-root POSIX user",
)
def test_fix_reports_an_undeletable_entry_exits_1_and_never_raises(workspace: Path) -> None:
    """Bug doctor-fix-aborts-whole-pass-on-first-undeletable-entry: the live symptom was
    ``Error: unexpected PermissionError`` with 0 repairs reported although earlier repairs
    had been applied — the pass must finish, report the skip, and exit 1 for what remains."""
    stale = _plant_expired(workspace)
    locked = workspace / ".dadaia" / _TTL_ZONE.name / "locked"
    locked.mkdir()
    undeletable = locked / "a.js"
    undeletable.write_text("", encoding="utf-8")
    two_days_ago = time.time() - 2 * 86_400
    os.utime(undeletable, (two_days_ago, two_days_ago))
    locked.chmod(0o555)
    try:
        result = CliRunner().invoke(app, ["doctor", "--fix"])
    finally:
        locked.chmod(0o755)

    assert not isinstance(result.exception, OSError), repr(result.exception)
    assert result.exit_code == 1, result.output
    assert not stale.exists()
    assert undeletable.exists()
    assert f"{_EXPIRED_CODE}: deleted '{_TTL_ZONE.name}/stale'" in result.output
    assert f"{_EXPIRED_CODE}: skipped '{_TTL_ZONE.name}/locked/a.js' (errno 13" in result.output


def test_fix_expired_only_quiet_is_the_reaper_lane(workspace: Path) -> None:
    """0.4.7 FR6b: ``--expired-only`` scopes what the REPORT shows, not what the reaper
    does — there is one lane (seed, move slop, expire). The SessionStart hook runs this
    exact command, so slop leaves the working tree there too; it is HELD in ``reaped/``,
    never deleted, and a second run has nothing left to take."""
    (workspace / "junk.txt").write_text("", encoding="utf-8")
    stale = _plant_expired(workspace)

    result = CliRunner().invoke(app, ["doctor", "--fix", "--expired-only", "--quiet"])

    assert result.exit_code == 0, result.output
    assert f"{_EXPIRED_CODE}: deleted '{_TTL_ZONE.name}/stale'" in result.output.splitlines()
    assert not stale.exists()
    assert not (workspace / "junk.txt").exists()
    assert any(p.name == "junk.txt" for p in (workspace / ".dadaia" / "reaped").rglob("junk.txt"))

    again = CliRunner().invoke(app, ["doctor", "--fix", "--expired-only", "--quiet"])
    assert again.exit_code == 0
    assert again.output == ""


def test_fix_moves_slop_to_reaped_and_reports_the_post_fix_score(workspace: Path) -> None:
    (workspace / "junk.txt").write_text("", encoding="utf-8")

    result = CliRunner().invoke(app, ["doctor", "--fix"])
    lines = result.output.splitlines()

    assert result.exit_code == 0, result.output
    assert "WS-root-slop: moved 'junk.txt' -> '.dadaia/reaped/" in result.output
    assert lines[-1].endswith("(100%)")
    assert not (workspace / "junk.txt").exists()


def _plant_hold(workspace: Path) -> Path:
    """One entry HELD in ``reaped/``: off the working tree, inside its 7-day window."""
    held = workspace / ".dadaia" / "reaped" / "20260913" / "x"
    held.parent.mkdir(parents=True, exist_ok=True)
    held.write_text("", encoding="utf-8")
    return held


def test_a_held_entry_is_always_listed_and_never_scored(workspace: Path) -> None:
    """Intent: CONTRACT — 0.4.7 FR6 AC (`dadaia doctor` LISTS what the reaper holds); size: SMALL.

    A hold is the one finding that is neither compliance nor failure: the operator must SEE
    what was moved and how long is left to take it back, while the score stays whole — the
    entry already left the working tree, so it is no longer one of the entries being scored.
    """
    _plant_hold(workspace)

    result = CliRunner().invoke(app, ["doctor"])
    lines = result.output.splitlines()
    held_lines = [ln for ln in lines if ln.startswith("WS-reaped-reaped")]

    assert result.exit_code == 0, result.output
    assert held_lines == ["WS-reaped-reaped reaped reaped/20260913/x  (7d left)"], lines
    assert [ln for ln in lines if _SCORE_LINE.match(ln)][0].endswith("(100%)"), lines


def test_json_lists_a_held_entry_and_keeps_the_score_whole(workspace: Path) -> None:
    """Intent: CONTRACT — 0.4.7 FR6 AC (the `--json` mirror of the held-entry listing); size: SMALL."""
    _plant_hold(workspace)
    healthy = json.loads(CliRunner().invoke(app, ["doctor", "--json"]).output)

    result = CliRunner().invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)
    section = payload["sections"]["workspace"]

    assert result.exit_code == 0, result.output
    (held,) = section["findings"]
    assert (held["code"], held["verdict"]) == ("WS-reaped-reaped", "reaped")
    assert held["message"] == "reaped/20260913/x  (7d left)"
    assert section["compliance"]["percent"] == 100
    # The hold is outside the scored set entirely — it neither helps nor hurts the count.
    assert section["compliance"]["total"] == healthy["sections"]["workspace"]["compliance"]["total"]
