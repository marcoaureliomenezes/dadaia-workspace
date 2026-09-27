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
from datetime import UTC, datetime, tzinfo
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.harness_registry import HARNESS_PROJECTION_DIRS, L1_ENTRY_HARNESSES
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.workspace_layout import provisioned_zones, zones_with_ttl
from dadaia_workspace.features.spec_context import doctor
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.stores import context_store

pytestmark = pytest.mark.contract

_TTL_ZONE = zones_with_ttl()[0]
_EXPIRED_CODE = f"WS-{_TTL_ZONE.name.lstrip('.')}-expired"
_FINDING_LINE = re.compile(
    r"^WS-[a-z.-]+-(slop|expired|missing) (slop|expired|missing) \S+  \(.+\)$"
)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dadaia = tmp_path / ".dadaia"
    for zone in provisioned_zones():
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
        lambda root: DoctorService(
            context_store(root / ".dadaia" / "states"), GitSubprocessClient(), root
        ),
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


def test_lists_findings_and_exits_1(workspace: Path) -> None:
    (workspace / "junk.txt").write_text("", encoding="utf-8")
    _plant_expired(workspace)

    result = CliRunner().invoke(app, ["doctor"])
    lines = result.output.splitlines()

    assert result.exit_code == 1, result.output
    finding_lines = [ln for ln in lines if ln.startswith("WS-")]
    assert len(finding_lines) == 2
    assert all(_FINDING_LINE.match(ln) for ln in finding_lines), finding_lines
    assert not any(ln.startswith("compliance(") for ln in lines), lines


def test_healthy_workspace_exits_0_and_prints_only_the_next_step(workspace: Path) -> None:
    """0.4.8 R2: zero contexts is no longer silent — the one onboarding info finding."""
    result = CliRunner().invoke(app, ["doctor"])
    lines = result.output.splitlines()

    assert result.exit_code == 0, result.output
    assert [line.split(" ", 2)[:2] for line in lines[:1]] == [["ONBOARDING", "info"]], lines
    assert len(lines) == 2 and lines[1].startswith("fix: "), lines


def _scan(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    """The zone-scan findings — the onboarding step is test_doctor_onboarding's business."""
    return [f for f in findings if f["code"] != "ONBOARDING"]


def test_json_carries_findings_and_fixed(workspace: Path) -> None:
    (workspace / "junk.txt").write_text("", encoding="utf-8")

    result = CliRunner().invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)

    assert result.exit_code == 1
    assert {"sections", "fixed"} <= set(payload) and "compliance" not in payload
    workspace_section = payload["sections"]["workspace"]
    assert _scan(workspace_section["findings"]) == [
        {
            "code": "WS-root-slop",
            "verdict": "slop",
            "message": "junk.txt  (not in the root law or the exceptions)",
            "fix": fix_line(workspace, "doctor", "--fix"),
        }
    ]
    assert "compliance" not in workspace_section
    assert payload["fixed"] == []


def test_fix_reports_an_undeletable_entry_exits_1_and_never_raises(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug doctor-fix-aborts-whole-pass-on-first-undeletable-entry: the live symptom was
    ``Error: unexpected PermissionError`` with 0 repairs reported although earlier repairs
    had been applied — the pass must finish, report the skip, and exit 1 for what remains.
    The refusal is planted at the unlink boundary: a read-only tree is reapable since bug
    doctor-reaper-cannot-delete-read-only-trees."""
    stale = _plant_expired(workspace)
    locked = workspace / ".dadaia" / _TTL_ZONE.name / "locked"
    locked.mkdir()
    undeletable = locked / "a.js"
    undeletable.write_text("", encoding="utf-8")
    two_days_ago = time.time() - 2 * 86_400
    os.utime(undeletable, (two_days_ago, two_days_ago))
    real_unlink = os.unlink

    def refusing_unlink(path: object, *args: object, **kwargs: object) -> None:
        if os.fspath(path) in (str(undeletable), undeletable.name):  # type: ignore[call-overload]
            raise PermissionError(13, "Permission denied", str(path))
        real_unlink(path, *args, **kwargs)  # type: ignore[arg-type]

    with monkeypatch.context() as patch:
        patch.setattr(os, "unlink", refusing_unlink)
        result = CliRunner().invoke(app, ["doctor", "--fix"])

    assert not isinstance(result.exception, OSError), repr(result.exception)
    assert result.exit_code == 1, result.output
    assert not stale.exists()
    assert undeletable.exists()
    assert f"{_EXPIRED_CODE}: deleted '{_TTL_ZONE.name}/stale'" in result.output
    assert f"{_EXPIRED_CODE}: skipped '{_TTL_ZONE.name}/locked/a.js' (errno 13" in result.output


def test_fix_expired_only_quiet_is_the_reaper_lane(workspace: Path) -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B5, #B4, #B3.

    0.4.7 FR6b: ``--expired-only`` scopes what the REPORT shows, not what the reaper
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


def _plant_hold(workspace: Path) -> Path:
    """One entry HELD in ``reaped/``: off the working tree, inside its 7-day window."""
    held = workspace / ".dadaia" / "reaped" / "20260913" / "x"
    held.parent.mkdir(parents=True, exist_ok=True)
    held.write_text("", encoding="utf-8")
    return held


def test_a_held_entry_is_always_listed_and_never_fails(workspace: Path) -> None:
    """Intent: CONTRACT — sa-reaper-destroys-its-own-hold-before-ttl#B7; size: SMALL.

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


def test_json_lists_a_held_entry_and_does_not_fail(workspace: Path) -> None:
    """Intent: CONTRACT — sa-reaper-destroys-its-own-hold-before-ttl#B7 (`--json`); size: SMALL."""
    _plant_hold(workspace)

    result = CliRunner().invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)
    section = payload["sections"]["workspace"]

    assert result.exit_code == 0, result.output
    (held,) = _scan(section["findings"])
    assert (held["code"], held["verdict"]) == ("WS-reaped-reaped", "reaped")
    assert held["message"] == "reaped/20260913/x  (7d left)"


class _FrozenClock(datetime):
    @classmethod
    def now(cls, tz: tzinfo | None = None) -> _FrozenClock:  # type: ignore[override]
        return cls(2026, 9, 27, 12, 0, 0, tzinfo=UTC)


def test_two_same_second_reaps_of_one_origin_leave_two_intact_holds(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B1, sa-reaper-destroys-its-own-hold-before-ttl#B2: the origin is reaped,
    re-created with new content and reaped again inside one frozen second; the first hold
    keeps every byte and a second, distinct hold carries the new content."""
    monkeypatch.setattr(doctor, "datetime", _FrozenClock)
    skill = workspace / "stray"
    skill.mkdir()
    (skill / "SKILL.md").write_bytes(b"v1\n")
    (skill / "refs.md").write_bytes(b"refs\n")
    assert CliRunner().invoke(app, ["doctor", "--fix"]).exit_code == 0
    skill.mkdir()
    (skill / "SKILL.md").write_bytes(b"v2\n")
    assert CliRunner().invoke(app, ["doctor", "--fix"]).exit_code == 0

    day = workspace / ".dadaia" / "reaped" / "20260927"
    assert sorted(p.name for p in day.iterdir()) == ["stray", "stray-1"]
    assert (day / "stray" / "SKILL.md").read_bytes() == b"v1\n"
    assert (day / "stray" / "refs.md").read_bytes() == b"refs\n"
    assert (day / "stray-1" / "SKILL.md").read_bytes() == b"v2\n"


def test_fix_deletes_a_hold_past_seven_days_and_keeps_a_younger_one(workspace: Path) -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B3: an 8-day hold is deleted and reported
    WS-reaped-expired; a 6-day hold survives."""
    old = workspace / ".dadaia" / "reaped" / "20260901" / "old"
    young = workspace / ".dadaia" / "reaped" / "20260921" / "young"
    for path, days in ((old, 8), (young, 6)):
        path.parent.mkdir(parents=True)
        path.write_text("x", encoding="utf-8")
        stamp = time.time() - days * 86_400
        os.utime(path, (stamp, stamp))
        os.utime(path.parent, (stamp, stamp))

    result = CliRunner().invoke(app, ["doctor", "--fix"])

    assert "WS-reaped-expired" in result.output, result.output
    assert not old.exists()
    assert young.read_text(encoding="utf-8") == "x"


_OPERATOR_HARNESS_FILES = {
    ".claude/settings.local.json": b'{"permissions": {"allow": ["Bash(ls)"]}}\n',
    ".claude/skills/dm-x/SKILL.md": b"---\nname: dm-x\n---\n",
}


def test_fix_leaves_operator_files_in_a_harness_dir_byte_identical(workspace: Path) -> None:
    """sa-doctor-reaps-harness-owned-entries#H1: files outside the ledger and every glob
    are byte-identical after ``doctor --fix``, which exits 0 with no WS-claude-slop."""
    for rel, body in _OPERATOR_HARNESS_FILES.items():
        (workspace / rel).parent.mkdir(parents=True, exist_ok=True)
        (workspace / rel).write_bytes(body)

    result = CliRunner().invoke(app, ["doctor", "--fix"])

    assert result.exit_code == 0, result.output
    assert "WS-claude-slop" not in result.output
    for rel, body in _OPERATOR_HARNESS_FILES.items():
        assert (workspace / rel).read_bytes() == body, rel


@pytest.mark.parametrize(
    "harness_dir", sorted({d for dirs in HARNESS_PROJECTION_DIRS.values() for d in dirs})
)
def test_no_harness_dir_entry_is_ever_slop_or_moved(workspace: Path, harness_dir: str) -> None:
    """sa-doctor-reaps-harness-owned-entries#H2, sa-doctor-reaps-harness-owned-entries#H3 (``.github`` carries
    ``hooks/stray.json`` and ``workflows/ci.yml``): a tree outside the ledger under any
    registered harness dir yields no finding for it and ``--fix`` moves nothing."""
    planted = {
        f"{harness_dir}/hooks/stray.json": b"{}\n",
        f"{harness_dir}/workflows/ci.yml": b"on: push\n",
        f"{harness_dir}/deep/a/b/notes.md": b"mine\n",
    }
    for rel, body in planted.items():
        (workspace / rel).parent.mkdir(parents=True, exist_ok=True)
        (workspace / rel).write_bytes(body)

    scan = json.loads(CliRunner().invoke(app, ["doctor", "--json"]).output)
    fix = CliRunner().invoke(app, ["doctor", "--fix"])

    messages = [f["message"] for f in scan["sections"]["workspace"]["findings"]]
    assert not [m for m in messages if m.startswith(harness_dir)], messages
    assert fix.exit_code == 0, fix.output
    for rel, body in planted.items():
        assert (workspace / rel).read_bytes() == body, rel


@pytest.mark.parametrize("ledger_state", ["absent", "corrupt"])
def test_fix_changes_nothing_in_a_harness_dir_without_a_readable_ledger(
    workspace: Path, ledger_state: str
) -> None:
    """sa-doctor-reaps-harness-owned-entries#H5."""
    ledger = workspace / ".dadaia" / "states" / "install_ledger.json"
    if ledger_state == "corrupt":
        ledger.write_text("{not json", encoding="utf-8")
    else:
        ledger.unlink()
    projected = workspace / ".claude" / "agents" / "pm.md"
    projected.parent.mkdir(parents=True)
    projected.write_text("projected", encoding="utf-8")

    CliRunner().invoke(app, ["doctor", "--fix"])

    assert projected.read_text(encoding="utf-8") == "projected"
    assert sorted(p.name for p in (workspace / ".claude").rglob("*")) == ["agents", "pm.md"]
