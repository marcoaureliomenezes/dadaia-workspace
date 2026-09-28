"""Intent: CONTRACT — 0.4.6 AC2, AC4 (`dadaia doctor` workspace section: finding lines, exit code,
`--json`, `--fix --expired-only --quiet`, holds in reaped/, expiry); size: SMALL.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
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
from dadaia_workspace.features.spec_context import sweep
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
    (dadaia / "states" / "harness_profile.json").write_text(
        json.dumps({"schema_version": "1", "harnesses": list(L1_ENTRY_HARNESSES)}),
        encoding="utf-8",
    )
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


def _touch(path: Path, days: float) -> None:
    stamp = time.time() - days * 86_400
    os.utime(path, (stamp, stamp))


def _plant_expired(workspace: Path) -> Path:
    stale = workspace / ".dadaia" / _TTL_ZONE.name / "stale"
    stale.parent.mkdir(exist_ok=True)
    stale.write_text("", encoding="utf-8")
    _touch(stale, 2)
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
    """Zero contexts prints the one ONBOARDING info finding and its fix line, exit 0."""
    result = CliRunner().invoke(app, ["doctor"])
    lines = result.output.splitlines()

    assert result.exit_code == 0, result.output
    assert [line.split(" ", 2)[:2] for line in lines[:1]] == [["ONBOARDING", "info"]], lines
    assert len(lines) == 2 and lines[1].startswith("fix: "), lines


def _scan(findings: list[dict[str, str]]) -> list[dict[str, str]]:
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
    """doctor-fix-aborts-whole-pass-on-first-undeletable-entry: the pass finishes, reports the skip, exits 1."""
    stale = _plant_expired(workspace)
    locked = workspace / ".dadaia" / _TTL_ZONE.name / "locked"
    locked.mkdir()
    undeletable = locked / "a.js"
    undeletable.write_text("", encoding="utf-8")
    _touch(undeletable, 2)
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
    assert f"{_EXPIRED_CODE}: skipped '{_TTL_ZONE.name}/locked' (errno " in result.output


def test_fix_expired_only_quiet_is_the_reaper_lane(workspace: Path) -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B5, #B4, #B3: one reaper lane — expired deleted, slop held
    in reaped/, a second quiet run prints nothing."""
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


def test_a_held_entry_is_always_listed_and_never_fails(workspace: Path) -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B7: a hold is listed with its days left (text and
    `--json`) and exits 0."""
    held = workspace / ".dadaia" / "reaped" / "20260913" / "x"
    held.parent.mkdir(parents=True)
    held.write_text("", encoding="utf-8")

    text = CliRunner().invoke(app, ["doctor"])
    as_json = CliRunner().invoke(app, ["doctor", "--json"])

    assert (text.exit_code, as_json.exit_code) == (0, 0), text.output
    assert [ln for ln in text.output.splitlines() if ln.startswith("WS-reaped-reaped")] == [
        "WS-reaped-reaped reaped reaped/20260913/x  (7d left)"
    ]
    (finding,) = _scan(json.loads(as_json.output)["sections"]["workspace"]["findings"])
    assert (finding["code"], finding["verdict"], finding["message"]) == (
        "WS-reaped-reaped",
        "reaped",
        "reaped/20260913/x  (7d left)",
    )


class _FrozenClock(datetime):
    @classmethod
    def now(cls, tz: tzinfo | None = None) -> _FrozenClock:  # type: ignore[override]
        return cls(2026, 9, 27, 12, 0, 0, tzinfo=UTC)


def test_two_same_second_reaps_of_one_origin_leave_two_intact_holds(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B1, sa-reaper-destroys-its-own-hold-before-ttl#B2: two reaps in
    one frozen second leave the first hold byte-intact and a second distinct hold."""
    monkeypatch.setattr(sweep, "datetime", _FrozenClock)
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
    """sa-reaper-destroys-its-own-hold-before-ttl#B3: an 8-day hold is deleted (WS-reaped-expired); a 6-day one survives."""
    old = workspace / ".dadaia" / "reaped" / "20260901" / "old"
    young = workspace / ".dadaia" / "reaped" / "20260921" / "young"
    for path, days in ((old, 8), (young, 6)):
        path.parent.mkdir(parents=True)
        path.write_text("x", encoding="utf-8")
        _touch(path, days)
        _touch(path.parent, days)

    result = CliRunner().invoke(app, ["doctor", "--fix"])

    assert "WS-reaped-expired" in result.output, result.output
    assert not old.exists()
    assert young.read_text(encoding="utf-8") == "x"


def test_a_hold_of_old_files_counts_from_the_move(workspace: Path) -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B3: a hold of 30-day-old files ages from the move, dying at 8 days."""
    stray = workspace / "stray"
    (stray / "deep").mkdir(parents=True)
    (stray / "a.md").write_text("a", encoding="utf-8")
    (stray / "deep" / "b.md").write_text("b", encoding="utf-8")
    for path in (stray / "deep" / "b.md", stray / "a.md", stray / "deep", stray):
        _touch(path, 30)

    assert CliRunner().invoke(app, ["doctor", "--fix"]).exit_code == 0
    (held,) = (workspace / ".dadaia" / "reaped").glob("*/stray")
    again = CliRunner().invoke(app, ["doctor", "--fix", "--expired-only"])

    assert again.exit_code == 0, again.output
    assert (held / "a.md").read_text(encoding="utf-8") == "a"
    assert (held / "deep" / "b.md").read_text(encoding="utf-8") == "b"

    for path in (held / "deep" / "b.md", held / "a.md", held / "deep", held):
        _touch(path, 8)
    CliRunner().invoke(app, ["doctor", "--fix"])

    assert not held.exists()


_OPERATOR_HARNESS_FILES = {
    ".claude/settings.local.json": b'{"permissions": {"allow": ["Bash(ls)"]}}\n',
    ".claude/skills/dm-x/SKILL.md": b"---\nname: dm-x\n---\n",
}


def test_fix_leaves_operator_files_in_a_harness_dir_byte_identical(workspace: Path) -> None:
    """sa-doctor-reaps-harness-owned-entries#H1: operator files in .claude/ stay byte-identical; no WS-claude-slop."""
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
    """sa-doctor-reaps-harness-owned-entries#H2, sa-doctor-reaps-harness-owned-entries#H3: an unledgered tree in any
    harness dir is no finding and ``--fix`` moves nothing."""
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
    """sa-doctor-reaps-harness-owned-entries#H5: with no readable ledger ``--fix`` touches no harness file."""
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


def _age(top: Path) -> None:
    for dirpath, dirnames, filenames in os.walk(top, topdown=False):
        for name in [*filenames, *dirnames]:
            _touch(Path(dirpath) / name, 3)
    _touch(top, 3)


def _expired(workspace: Path) -> list[str]:
    payload = json.loads(CliRunner().invoke(app, ["doctor", "--json"]).output)
    findings = payload["sections"]["workspace"]["findings"]
    return [f["message"] for f in findings if f["code"] == "WS-tmp-expired"]


def test_a_nested_expired_tree_is_gone_after_one_expired_only_run(workspace: Path) -> None:
    """reaper-needs-many-runs-for-a-nested-expired-tree: an entry ages by its newest file, so one run reaps it whole."""
    day = workspace / ".dadaia" / "tmp" / "a" / "20260920"
    for n in range(4):
        deep = day / "tree" / f"d{n}" / "e" / "f"
        deep.mkdir(parents=True)
        (deep / "leaf.txt").write_text("x", encoding="utf-8")
        (day / "tree" / f"d{n}" / "mid.txt").write_text("x", encoding="utf-8")
    _age(workspace / ".dadaia" / "tmp" / "a")
    # An interrupted earlier pass leaves an emptied directory with a fresh mtime.
    (day / "tree" / "emptied-today").mkdir()

    result = CliRunner().invoke(app, ["doctor", "--fix", "--expired-only"])

    assert result.exit_code == 0, result.output
    assert not (workspace / ".dadaia" / "tmp" / "a").exists()
    assert _expired(workspace) == []


def _git(cwd: Path, *args: str) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


def test_an_expired_entry_holding_a_worktree_carries_a_fix_that_clears_it(
    workspace: Path,
) -> None:
    """tmp-expired-worktree-fix-line-never-clears: the fix, run verbatim, removes the worktree and the entry reaps."""
    day = workspace / ".dadaia" / "tmp" / "a" / "20260920"
    repo = day / "r"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    (repo / "f.txt").write_text("f", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-q", "-m", "init")
    _git(repo, "worktree", "add", "-q", "-b", "wt/a", str(day / "wt"))
    _age(workspace / ".dadaia" / "tmp" / "a")

    payload = json.loads(CliRunner().invoke(app, ["doctor", "--json"]).output)
    (finding,) = [
        f for f in payload["sections"]["workspace"]["findings"] if f["code"] == "WS-tmp-expired"
    ]
    done = subprocess.run(finding["fix"], shell=True, cwd=workspace, check=False)
    CliRunner().invoke(app, ["doctor", "--fix", "--expired-only"])

    assert done.returncode == 0
    assert _expired(workspace) == []
    assert not (workspace / ".dadaia" / "tmp" / "a").exists()


@pytest.mark.parametrize(
    ("rel", "body", "reported"),
    [
        pytest.param(
            "tmp/reconciler-last-x",
            "2026-09-26T00:00:00+00:00",
            "WS-tmp-expired: deleted 'tmp/reconciler-last-x'",
            id="sa-expiry-has-two-clocks#45.1-marker",
        ),
        pytest.param(
            "handoff/ctx/old.handoff.json",
            '{"produced_at": "2099-01-01T00:00:00Z"}',
            "WS-handoff-expired: deleted 'handoff/ctx/old.handoff.json'",
            id="sa-expiry-has-two-clocks#45.2-handoff",
        ),
    ],
)
def test_an_expired_marker_is_reaped_by_the_zone_walk(
    workspace: Path, rel: str, body: str, reported: str
) -> None:
    """sa-expiry-has-two-clocks#45.1, #45.2: an entry one second past its zone TTL by mtime is reaped by the one
    zone walk whatever its content says; a fresh handoff with an old produced_at is kept."""
    old = workspace / ".dadaia" / rel
    fresh = workspace / ".dadaia" / "handoff" / "ctx" / "fresh.handoff.json"
    fresh.parent.mkdir(parents=True, exist_ok=True)
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text(body, encoding="utf-8")
    fresh.write_text('{"produced_at": "2026-09-24T00:00:00Z"}', encoding="utf-8")
    _touch(old, 86_401 / 86_400)

    result = CliRunner().invoke(app, ["doctor", "--fix", "--expired-only"])

    assert reported in result.output, result.output
    assert not old.exists()
    assert fresh.exists()


def test_a_retired_cache_zone_is_held_by_the_reaper_never_orphaned(workspace: Path) -> None:
    """sa-tool-caches-land-outside-the-cache-zone#B40-3: a retired .dadaia/.cache/ is reported slop and held in reaped/."""
    cache = workspace / ".dadaia" / ".cache" / "ruff" / "x"
    cache.parent.mkdir(parents=True)
    cache.write_text("x", encoding="utf-8")

    scan = CliRunner().invoke(app, ["doctor"])
    fixed = CliRunner().invoke(app, ["doctor", "--fix"])

    assert "WS-dadaia-slop slop .cache  (not in the root law or the exceptions)" in scan.output
    assert not (workspace / ".dadaia" / ".cache").exists(), fixed.output
    assert [
        p.read_text(encoding="utf-8") for p in (workspace / ".dadaia" / "reaped").rglob("x")
    ] == ["x"]
