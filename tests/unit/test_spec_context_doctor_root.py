"""Intent: CONTRACT — 0.4.6 AC2, AC4, AC6, AC7, AC9 (FR3 one scan, FR4 the reaper, FR5 TTLs,
FR8 the profile seed); size: SMALL.

``DoctorService.scan()`` is the ONE registry-driven walk; every entry gets one verdict and one
code ``WS-<zone>-<verdict>``, and ``fix()`` consumes that list in the FR4 order. Expectations
are derived from the registry views, never a spelled zone name.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.workspace_layout import (
    DADAIA_ROOT_FILES,
    INSTANCE_EXCEPTIONS,
    Creator,
    ZoneClass,
    provisioned_zones,
    zones_with_canon,
    zones_with_ttl,
)
from dadaia_workspace.features.spec_context import sweep
from dadaia_workspace.features.spec_context.doctor import (
    DoctorService,
    Finding,
    FindingVerdict,
)
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from tests.fixtures.stores import context_store

_TTL_ZONE = zones_with_ttl()[0]
_STATE_ZONE = next(z for z in zones_with_canon() if z.creator is Creator.INIT)
_OPERATOR_ZONE = next(z for z in workspace_layout.DADAIA_ZONES if z.creator is Creator.OPERATOR)
_INSTALL_ZONE = next(z for z in provisioned_zones() if z.creator is Creator.INSTALL)
_TWO_DAYS_AGO = time.time() - 2 * 86_400


def _make_doctor(root: Path) -> DoctorService:
    return DoctorService(context_store(root / ".dadaia" / "states"), GitSubprocessClient(), root)


def _reaped(root: Path, rel: str) -> Path:
    """Where the reaper holds *rel*: ``.dadaia/reaped/<YYYYMMDD>/<workspace-relative>``."""
    day = datetime.now(tz=UTC).strftime("%Y%m%d")
    return root / ".dadaia" / "reaped" / day / rel


def _init_workspace(root: Path) -> None:
    """The minimal compliant skeleton: every INIT/INSTALL zone present, one root file."""
    dadaia = root / ".dadaia"
    for zone in provisioned_zones():
        (dadaia / zone.name).mkdir(parents=True, exist_ok=True)
    (dadaia / _STATE_ZONE.name / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}', encoding="utf-8"
    )
    _write_ledger(root)
    _profile(root).write_text(
        json.dumps({"schema_version": "1", "harnesses": list(L1_ENTRY_HARNESSES)}),
        encoding="utf-8",
    )
    (root / "repos").mkdir()
    (root / "AGENTS.md").write_text("# agents", encoding="utf-8")


def _profile(root: Path) -> Path:
    return root / ".dadaia" / _STATE_ZONE.name / "harness_profile.json"


def _age(path: Path, epoch: float = _TWO_DAYS_AGO) -> None:
    # Windows implements neither ``follow_symlinks=False`` nor lstat-side utime (bug
    # doctor-root-tests-age-with-utime-follow-symlinks-false-unsupported-on-windows); the
    # one test that must age a link itself skips there.
    if os.utime in os.supports_follow_symlinks:
        os.utime(path, (epoch, epoch), follow_symlinks=False)
    else:
        os.utime(path, (epoch, epoch))


def _by_path(findings: tuple[Finding, ...]) -> dict[str, Finding]:
    return {f.path: f for f in findings}


def _write_ledger(root: Path, *relpaths: str) -> None:
    entries = [{"relpath": rel, "sha256": "0" * 64, "family": "test"} for rel in relpaths]
    (root / ".dadaia" / _STATE_ZONE.name / "install_ledger.json").write_text(
        json.dumps({"schema_version": "1", "entries": entries}), encoding="utf-8"
    )
    for rel in relpaths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("projected", encoding="utf-8")


def test_root_and_dadaia_top_level_classify_every_entry(tmp_path: Path) -> None:
    """sa-gate-allows-root-entries-the-reaper-moves#E2, sa-gate-allows-root-entries-the-reaper-moves#E4,
    sa-gate-allows-root-entries-the-reaper-moves#E6: the doctor side of the parity — unlisted =
    slop, globbed = operator, a non-zone .dadaia/ entry is slop."""
    _init_workspace(tmp_path)
    dadaia = tmp_path / ".dadaia"
    for name in (".claude", ".git", ".ruff_cache", ".dadaia/reports"):
        (tmp_path / name).mkdir()
    (tmp_path / "random_junk.txt").write_text("oops", encoding="utf-8")
    (tmp_path / "shot.png").write_bytes(b"PNG")
    (tmp_path / INSTANCE_EXCEPTIONS).write_text("# comment\n*.png\n", encoding="utf-8")
    for name in (*DADAIA_ROOT_FILES, ".DS_Store"):
        (dadaia / name).write_text("x", encoding="utf-8")
    (dadaia / _OPERATOR_ZONE.name / "some-clone").mkdir(parents=True)

    found = _by_path(_make_doctor(tmp_path).scan())

    assert {n: found[n].verdict for n in ("AGENTS.md", ".claude", ".git")} == dict.fromkeys(
        ("AGENTS.md", ".claude", ".git"), FindingVerdict.CANON
    )
    assert (found["shot.png"].verdict, found["shot.png"].code) == (
        FindingVerdict.OPERATOR,
        "WS-root-operator",
    )
    assert found["random_junk.txt"].code == found[".ruff_cache"].code == "WS-root-slop"
    assert found["random_junk.txt"].fixable is True
    assert "# comment" not in {f.detail for f in found.values()}
    for name in (*DADAIA_ROOT_FILES, _STATE_ZONE.name, _OPERATOR_ZONE.name):
        assert found[name].code == "WS-dadaia-canon"
    assert found["reports"].code == found[".DS_Store"].code == "WS-dadaia-slop"


def test_absent_init_or_install_zone_is_missing_and_fixable(tmp_path: Path) -> None:
    """An absent INSTALL zone is the one MISSING finding; OPERATOR and MANAGED zones are
    never walked, so their aged content is neither reported nor touched by fix()."""
    _init_workspace(tmp_path)
    (tmp_path / ".dadaia" / _INSTALL_ZONE.name).rmdir()
    stale = tmp_path / ".dadaia" / _OPERATOR_ZONE.name / "clone" / "README.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("reference", encoding="utf-8")
    _age(stale)
    (tmp_path / ".dadaia" / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".dadaia" / ".venv" / "lib" / "site.py").write_text("", encoding="utf-8")

    findings = _make_doctor(tmp_path).scan()

    assert [
        (f.code, f.path, f.fixable) for f in findings if f.verdict is FindingVerdict.MISSING
    ] == [(f"WS-{_INSTALL_ZONE.name}-missing", _INSTALL_ZONE.name, True)]
    assert not any(_OPERATOR_ZONE.name in f.code for f in findings)
    assert not any("README.md" in f.path or "site.py" in f.path for f in findings)
    _make_doctor(tmp_path).fix()
    assert stale.read_text(encoding="utf-8") == "reference"


# ---------------------------------------------------------------------------
# Step 4 — the closed-canon zones
# ---------------------------------------------------------------------------


def test_closed_canon_zones_flag_every_non_canon_entry_and_fix_removes_it(tmp_path: Path) -> None:
    """A non-canon entry in a closed-canon zone is slop (the retired ``states/ctx_locks`` and
    ``sessions/runtime`` have no code of their own); fix() leaves a fully canonical scan."""
    _init_workspace(tmp_path)
    dadaia = tmp_path / ".dadaia"
    (dadaia / _STATE_ZONE.name / "ctx_locks").mkdir()
    (dadaia / _STATE_ZONE.name / "ctx_locks" / "stale.lock.json").write_text("{}", "utf-8")
    sessions = next(z for z in zones_with_canon() if z.cls is ZoneClass.PROTECTED)
    (dadaia / sessions.name / "runtime").mkdir(parents=True)
    for zone in zones_with_canon():
        assert zone.canon is not None
        (dadaia / zone.name).mkdir(exist_ok=True)
        (dadaia / zone.name / "stray.bin").write_bytes(b"")
        (dadaia / zone.name / sorted(zone.canon)[0].replace("*", "sample")).write_text("", "utf-8")

    found = _by_path(_make_doctor(tmp_path).scan())

    assert found[f"{_STATE_ZONE.name}/ctx_locks"].code == f"WS-{_STATE_ZONE.name}-slop"
    assert found[f"{sessions.name}/runtime"].code == f"WS-{sessions.name}-slop"
    assert found[f"{_STATE_ZONE.name}/spec_contexts.json"].verdict is FindingVerdict.CANON
    for zone in zones_with_canon():
        assert zone.canon is not None
        assert found[f"{zone.name}/stray.bin"].code == f"WS-{zone.name}-slop"
        sample = sorted(zone.canon)[0].replace("*", "sample")
        assert found[f"{zone.name}/{sample}"].verdict is FindingVerdict.CANON
    _make_doctor(tmp_path).fix()
    assert all(f.canonical for f in _make_doctor(tmp_path).scan())


def test_absent_harness_profile_is_missing_and_fix_seeds_it_from_present_dirs(
    tmp_path: Path,
) -> None:
    """FR8 / AC9: a missing ``harness_profile.json`` is ``WS-states-missing`` (fixable);
    ``fix()`` seeds it through the one store writer with exactly the L1 harnesses whose
    projection dir exists at the root — regenerated from disk, never widened."""
    _init_workspace(tmp_path)
    _profile(tmp_path).unlink()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".codex").mkdir()

    findings = _make_doctor(tmp_path).scan()
    missing = [f for f in findings if f.verdict is FindingVerdict.MISSING]
    assert [(f.code, f.path, f.fixable) for f in missing] == [
        (f"WS-{_STATE_ZONE.name}-missing", f"{_STATE_ZONE.name}/harness_profile.json", True)
    ]

    actions = _make_doctor(tmp_path).fix()

    assert actions == [
        f"WS-{_STATE_ZONE.name}-missing: created '{_STATE_ZONE.name}/harness_profile.json'"
    ]
    assert json.loads(_profile(tmp_path).read_text(encoding="utf-8")) == {
        "schema_version": "1",
        "harnesses": ["claude", "codex"],
    }
    assert not [f for f in _make_doctor(tmp_path).scan() if f.verdict is FindingVerdict.MISSING]


def test_ttl_zones_expire_an_entry_whole_by_its_own_ttl_and_spare_the_zone_law(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """reaper-needs-many-runs-for-a-nested-expired-tree: an expired entry is ONE finding judged
    by its newest content; every TTL zone uses its own code and TTL; bug
    public-install-restores-expired-zone-agents-reblocks-preflight: the projected zone
    ``AGENTS.md`` is never a candidate; bug doctor-ttl-walk-quadratic-on-live-trees: a live
    tree costs <= 2 stats per entry (never one per ancestor) and no finding."""
    _init_workspace(tmp_path)
    for zone in zones_with_ttl():
        (tmp_path / ".dadaia" / zone.name).mkdir(exist_ok=True)
        stale = tmp_path / ".dadaia" / zone.name / "stale"
        stale.write_text("", encoding="utf-8")
        _age(stale, time.time() - (zone.ttl_seconds or 0) - 60)
    zone_dir = tmp_path / ".dadaia" / _TTL_ZONE.name
    old = zone_dir / "claude" / "20260801" / "x.png"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"PNG")
    _age(old)
    (deep := zone_dir.joinpath("claude", *"abcdef")).mkdir(parents=True)
    for level in (deep, *deep.parents[:6]):
        (level / "today.txt").touch()  # claude/a holds 12 live entries, 6 deep
    law = zone_dir / "AGENTS.md"
    law.write_text("# zone law", encoding="utf-8")
    _age(law, time.time() - 400 * 86_400)
    stats: list[Path] = []
    real_stat = Path.stat

    def counting_stat(path: Path, **kwargs: bool) -> os.stat_result:
        stats.append(path)
        return real_stat(path, **kwargs)

    monkeypatch.setattr(Path, "stat", counting_stat)
    found = _by_path(_make_doctor(tmp_path).scan())

    z = _TTL_ZONE.name
    assert len([p for p in stats if p.is_relative_to(deep.parents[4])]) <= 2 * 12
    assert found[f"{z}/claude/20260801"].code == f"WS-{z.lstrip('.')}-expired"
    assert found[f"{z}/claude/20260801"].detail == "(mtime 2d > ttl 1d)"
    assert [p for p in found if p.startswith(f"{z}/")] == [f"{z}/claude/20260801", f"{z}/stale"]
    codes = {f.code for f in found.values()}
    assert {f"WS-{zone.name.lstrip('.')}-expired" for zone in zones_with_ttl()} <= codes
    _make_doctor(tmp_path).fix()
    assert law.exists()


@pytest.mark.skipif(
    os.utime not in os.supports_follow_symlinks,
    reason="ageing a symlink itself needs utime(follow_symlinks=False), absent on Windows",
)
def test_symlinks_are_never_followed_and_only_the_link_is_deleted(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    _init_workspace(ws)
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "keep.txt"
    victim.write_text("keep", encoding="utf-8")
    _age(victim)
    zone_dir = ws / ".dadaia" / _TTL_ZONE.name
    zone_dir.mkdir(exist_ok=True)
    link = zone_dir / "link"
    link.symlink_to(outside, target_is_directory=True)
    _age(link)

    findings = _make_doctor(ws).scan()
    paths = {f.path for f in findings}

    assert f"{_TTL_ZONE.name}/link" in paths
    assert not any("keep.txt" in p for p in paths)

    _make_doctor(ws).fix()

    assert not link.exists() and not link.is_symlink()
    assert victim.read_text(encoding="utf-8") == "keep"


def test_ttl_walk_treats_an_entry_that_vanishes_mid_walk_as_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk: a file or descended-into dir
    removed between ``iterdir`` and ``lstat`` is absent — no finding, no exception."""
    _init_workspace(tmp_path)
    zone_dir = tmp_path / ".dadaia" / _TTL_ZONE.name
    zone_dir.mkdir(exist_ok=True)
    gone_file = zone_dir / "gone.txt"
    gone_file.write_text("", encoding="utf-8")
    gone_dir = zone_dir / "gone_dir"
    gone_dir.mkdir()
    real_walk = sweep.walk

    def racing_walk(directory: Path) -> list[Path]:
        entries = real_walk(directory)
        if directory == zone_dir:
            gone_file.unlink()
        elif directory == gone_dir:
            gone_dir.rmdir()
        return entries

    monkeypatch.setattr(sweep, "walk", racing_walk)

    found = _by_path(_make_doctor(tmp_path).scan())

    assert not [p for p in found if p.startswith(f"{_TTL_ZONE.name}/")]


# ---------------------------------------------------------------------------
# The reaper order, --expired-only
# ---------------------------------------------------------------------------


def test_the_reaper_lane_seeds_moves_slop_and_deletes_only_what_expired(tmp_path: Path) -> None:
    """0.4.7 FR6b: there is no second, smaller lane. One ``fix()`` seeds what is missing,
    MOVES slop into ``reaped/`` (never deletes it) and deletes only TTL-expired entries."""
    _init_workspace(tmp_path)
    (tmp_path / ".dadaia" / _INSTALL_ZONE.name).rmdir()
    junk = tmp_path / "junk.txt"
    junk.write_text("", encoding="utf-8")
    zone_dir = tmp_path / ".dadaia" / _TTL_ZONE.name
    zone_dir.mkdir(exist_ok=True)
    stale = zone_dir / "stale"
    stale.write_text("", encoding="utf-8")
    _age(stale)

    actions = _make_doctor(tmp_path).fix()

    assert not stale.exists()
    assert not junk.exists(), "slop is moved, not left in place"
    assert _reaped(tmp_path, "junk.txt").exists(), "slop is held in reaped/, never deleted"
    assert (tmp_path / ".dadaia" / _INSTALL_ZONE.name).is_dir()
    assert [a.split(":")[0] for a in actions] == [
        f"WS-{_INSTALL_ZONE.name}-missing",
        "WS-root-slop",
        f"WS-{_TTL_ZONE.name.lstrip('.')}-expired",
    ]

    # A second pass has nothing left to take: the held entry is canonical where it sits.
    assert _make_doctor(tmp_path).fix() == []
    assert _reaped(tmp_path, "junk.txt").exists()


def test_fix_skips_and_reports_an_undeletable_entry_and_finishes_the_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug doctor-fix-aborts-whole-pass-on-first-undeletable-entry (class of
    retention-sweep-crashes-on-permission-denied; read-only trees are reapable since
    doctor-reaper-cannot-delete-read-only-trees): an entry refused past the chmod-retry is
    skipped with its errno, stays a finding, and the pass reaches every other entry."""
    _init_workspace(tmp_path)
    zone = tmp_path / ".dadaia" / _TTL_ZONE.name
    locked = zone / "x" / "deps"
    locked.mkdir(parents=True)
    undeletable = locked / "a.js"
    undeletable.write_text("", encoding="utf-8")
    other = zone / "y.txt"
    other.write_text("", encoding="utf-8")
    for path in (undeletable, other, locked, locked.parent):
        _age(path)
    real_unlink = os.unlink

    def refusing_unlink(path: object, *args: object, **kwargs: object) -> None:
        if os.fspath(path) in (str(undeletable), undeletable.name):  # type: ignore[call-overload]
            raise PermissionError(13, "Permission denied", str(path))
        real_unlink(path, *args, **kwargs)  # type: ignore[arg-type]

    doctor = _make_doctor(tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(os, "unlink", refusing_unlink)
        actions = doctor.fix()
    remaining = _by_path(doctor.scan())

    assert not other.exists()
    assert undeletable.exists()
    deleted = [a for a in actions if ": deleted '" in a]
    skipped = [a for a in actions if ": skipped '" in a]
    assert f"WS-{_TTL_ZONE.name}-expired: deleted '{_TTL_ZONE.name}/y.txt'" in deleted
    assert not any(f"'{_TTL_ZONE.name}/x'" in a for a in deleted)
    assert any(f"skipped '{_TTL_ZONE.name}/x' (errno " in a for a in skipped), actions
    assert remaining[f"{_TTL_ZONE.name}/x"].verdict is FindingVerdict.EXPIRED


def test_fix_skips_and_reports_a_failing_seed_and_still_deletes_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk (finding 2): an unwritable
    seed is skipped with its errno in the deletion's shape and the pass still deletes expired."""
    _init_workspace(tmp_path)
    _profile(tmp_path).unlink()
    zone_dir = tmp_path / ".dadaia" / _TTL_ZONE.name
    zone_dir.mkdir(exist_ok=True)
    stale = zone_dir / "stale"
    stale.write_text("", encoding="utf-8")
    _age(stale)

    def denied(*_: object, **__: object) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(JsonHarnessProfileStore, "write", denied)

    actions = _make_doctor(tmp_path).fix()

    assert not _profile(tmp_path).exists()
    assert not stale.exists()
    assert actions == [
        f"WS-{_STATE_ZONE.name}-missing: skipped '{_STATE_ZONE.name}/harness_profile.json'"
        " (errno 13: Permission denied)",
        f"WS-{_TTL_ZONE.name}-expired: deleted '{_TTL_ZONE.name}/stale'",
    ]


@pytest.mark.parametrize("target_inside_workspace", [True, False])
def test_a_symlinked_zone_root_is_never_walked(
    tmp_path: Path, target_inside_workspace: bool
) -> None:
    """Bug doctor-walks-symlinked-zone-root-into-a-repo-tree (CWE-59): a symlinked zone root is
    never walked — no finding, nothing under the target touched (supersedes the finding-6 pin
    of doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk)."""
    ws = tmp_path / "ws"
    ws.mkdir()
    _init_workspace(ws)
    target = (ws / "repos" / "victim") if target_inside_workspace else (tmp_path / "outside")
    target.mkdir(parents=True)
    victim = target / "old.txt"
    victim.write_text("keep", encoding="utf-8")
    _age(victim)
    zone_dir = ws / ".dadaia" / _TTL_ZONE.name
    if zone_dir.exists():
        zone_dir.rmdir()
    zone_dir.symlink_to(target, target_is_directory=True)

    findings = _make_doctor(ws).scan()
    actions = _make_doctor(ws).fix()

    assert not any("old.txt" in f.path for f in findings), [f.path for f in findings]
    assert victim.read_text(encoding="utf-8") == "keep"
    assert zone_dir.is_symlink()
    assert actions == []
