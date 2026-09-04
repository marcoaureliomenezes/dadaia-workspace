"""Intent: CONTRACT — 0.4.6 AC2, AC4, AC6, AC7, AC9 (FR3 one scan, FR4 the reaper, FR5 TTLs,
FR6 exceptions migration, FR8 the profile seed); size: SMALL.

``DoctorService.scan()`` is the ONE walk over the workspace instance, driven by the zone
registry (``core.workspace_layout.DADAIA_ZONES``): root, harness dirs, the ``.dadaia/`` top
level, the closed-canon zones, the TTL zones — in that order. Every scanned entry gets one
finding verdict (``canon | operator | slop | expired | missing``) and one finding code
``WS-<zone>-<verdict>``; ``fix()`` consumes the same list in the fixed FR4 order.

The six-bug ``.dadaia/`` ledger (workspace-doctor-root4-false-positive-dadaia-hooks ..
dadaia-reconcile-quarantines-sanctioned-references-clone) edited bare name lists; these
tests never spell a zone name the registry does not export — every expectation is derived
from the registry views, so a row added or retired there re-derives the expectation.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.workspace_layout import (
    DADAIA_ROOT_FILES,
    INSTANCE_EXCEPTIONS,
    Creator,
    ZoneClass,
    zones_created_by,
    zones_with_canon,
    zones_with_ttl,
)
from dadaia_workspace.features.spec_context.doctor import (
    DoctorService,
    Finding,
    FindingVerdict,
    compliance,
)
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from tests.fakes import FakeContextStore, FakeGitClient

_TTL_ZONE = zones_with_ttl()[0]
_STATE_ZONE = next(z for z in zones_with_canon() if z.creator is Creator.INIT)
_OPERATOR_ZONE = next(z for z in workspace_layout.DADAIA_ZONES if z.creator is Creator.OPERATOR)
_INSTALL_ZONE = zones_created_by(Creator.INSTALL)[0]
_TWO_DAYS_AGO = time.time() - 2 * 86_400


def _make_doctor(root: Path) -> DoctorService:
    return DoctorService(FakeContextStore(), FakeGitClient(), root)


def _init_workspace(root: Path) -> None:
    """The minimal compliant skeleton: every INIT/INSTALL zone present, one root file."""
    dadaia = root / ".dadaia"
    for zone in (*zones_created_by(Creator.INIT), *zones_created_by(Creator.INSTALL)):
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
    os.utime(path, (epoch, epoch), follow_symlinks=False)


def _by_path(findings: tuple[Finding, ...]) -> dict[str, Finding]:
    return {f.path: f for f in findings}


def _codes(findings: tuple[Finding, ...]) -> set[str]:
    return {f.code for f in findings}


def _write_ledger(root: Path, *relpaths: str) -> None:
    entries = [{"relpath": rel, "sha256": "0" * 64, "family": "test"} for rel in relpaths]
    (root / ".dadaia" / _STATE_ZONE.name / "install_ledger.json").write_text(
        json.dumps({"schema_version": "1", "entries": entries}), encoding="utf-8"
    )
    for rel in relpaths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("projected", encoding="utf-8")


# ---------------------------------------------------------------------------
# Step 1 — the workspace root
# ---------------------------------------------------------------------------


def test_root_walk_classifies_every_entry(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / "random_junk.txt").write_text("oops", encoding="utf-8")
    (tmp_path / ".ruff_cache").mkdir()
    (tmp_path / "shot.png").write_bytes(b"PNG")
    (tmp_path / INSTANCE_EXCEPTIONS).write_text("# comment\n*.png\n", encoding="utf-8")

    found = _by_path(_make_doctor(tmp_path).scan())

    assert found["AGENTS.md"].verdict is FindingVerdict.CANON
    assert found[".claude"].verdict is FindingVerdict.CANON
    assert found["shot.png"].verdict is FindingVerdict.OPERATOR
    assert found["shot.png"].code == "WS-root-operator"
    assert found["random_junk.txt"].code == "WS-root-slop"
    assert found["random_junk.txt"].fixable is True
    assert found[".ruff_cache"].code == "WS-root-slop"
    assert found[".git"].verdict is FindingVerdict.CANON
    assert "# comment" not in {f.detail for f in found.values()}


def test_fix_migrates_root_exceptions_into_instance_exceptions(tmp_path: Path) -> None:
    """FR6 / AC7: ``root_exceptions.txt`` present and ``INSTANCE_EXCEPTIONS`` absent ⇒ ``fix()``
    writes the parsed globs (comments dropped, deduplicated, directory slash dropped, order
    kept) to the new file and unlinks the old one. Before the migration the legacy file is
    read by nobody: it is plain closed-canon slop and its globs suppress nothing."""
    _init_workspace(tmp_path)
    (tmp_path / "shot.png").write_bytes(b"PNG")
    (tmp_path / "z_img").mkdir()
    legacy = tmp_path / ".dadaia" / _STATE_ZONE.name / "root_exceptions.txt"
    legacy.write_text(
        "# operator files\n*.png\n\n.mcp.json\n# infra\n.mcp.json\nz_img/\n.mcp.json\nz_img\n",
        encoding="utf-8",
    )
    new = tmp_path / INSTANCE_EXCEPTIONS

    before = _by_path(_make_doctor(tmp_path).scan())
    assert before["shot.png"].verdict is FindingVerdict.SLOP
    assert before[f"{_STATE_ZONE.name}/root_exceptions.txt"].code == f"WS-{_STATE_ZONE.name}-slop"

    actions = _make_doctor(tmp_path).fix(expired_only=True)

    assert not legacy.exists()
    assert new.read_text(encoding="utf-8") == "*.png\n.mcp.json\nz_img\n"
    assert [a for a in actions if "root_exceptions.txt" in a] == [
        "EXCEPTIONS-MIGRATION: migrated 'root_exceptions.txt' -> 'instance_exceptions.txt' (3 globs)"
    ]
    after = _by_path(_make_doctor(tmp_path).scan())
    assert after["shot.png"].verdict is FindingVerdict.OPERATOR
    assert after["z_img"].verdict is FindingVerdict.OPERATOR
    assert after[f"{_STATE_ZONE.name}/instance_exceptions.txt"].verdict is FindingVerdict.CANON


def test_fix_never_overwrites_an_existing_instance_exceptions_file(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    legacy = tmp_path / ".dadaia" / _STATE_ZONE.name / "root_exceptions.txt"
    legacy.write_text("*.png\n", encoding="utf-8")
    new = tmp_path / INSTANCE_EXCEPTIONS
    new.write_text("*.jpg\n", encoding="utf-8")

    _make_doctor(tmp_path).fix()

    assert new.read_text(encoding="utf-8") == "*.jpg\n"
    assert not legacy.exists()


# ---------------------------------------------------------------------------
# Step 2 — the harness dirs (projection targets come from the install ledger)
# ---------------------------------------------------------------------------


def test_harness_dirs_projection_target_or_exception_else_slop(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    _write_ledger(
        tmp_path,
        ".claude/agents/pm.md",
        ".claude/skills/dd-x/SKILL.md",
        ".agents/skills/dd-x/SKILL.md",
    )
    (tmp_path / ".claude" / "agents" / "my-own.md").write_text("mine", encoding="utf-8")
    (tmp_path / ".claude" / "commands").mkdir()
    (tmp_path / ".claude" / "settings.local.json").write_text("{}", encoding="utf-8")
    private = tmp_path / ".claude" / "skills" / "private-skill"
    private.mkdir(parents=True)
    (private / "SKILL.md").write_text("---\nname: private-skill\n---\n", encoding="utf-8")
    excepted = tmp_path / ".agents" / "skills" / "godot-mcp"
    excepted.mkdir(parents=True)
    (excepted / "SKILL.md").write_text("x", encoding="utf-8")
    (tmp_path / INSTANCE_EXCEPTIONS).write_text("godot-*\n", encoding="utf-8")

    found = _by_path(_make_doctor(tmp_path).scan())

    assert found[".claude/agents/pm.md"].code == "WS-claude-canon"
    assert found[".agents/skills/dd-x/SKILL.md"].code == "WS-agents-canon"
    assert found[".claude/agents/my-own.md"].code == "WS-claude-slop"
    assert found[".claude/settings.local.json"].code == "WS-claude-slop"
    # A directory holding no projection target is ONE finding, never recursed into.
    assert found[".claude/skills/private-skill"].code == "WS-claude-slop"
    assert ".claude/skills/private-skill/SKILL.md" not in found
    assert found[".claude/commands"].code == "WS-claude-slop"
    assert found[".agents/skills/godot-mcp"].code == "WS-agents-operator"
    # A directory that holds a target is a path, not an entry.
    assert ".claude/agents" not in found
    assert ".claude/skills" not in found


def test_harness_dirs_are_scoped_by_the_persisted_profile(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    (tmp_path / ".codex" / "stray").mkdir(parents=True)
    (tmp_path / ".kimi-code" / "stray").mkdir(parents=True)
    profile = tmp_path / ".dadaia" / _STATE_ZONE.name / "harness_profile.json"

    assert {"WS-codex-slop", "WS-kimi-code-slop"} <= _codes(_make_doctor(tmp_path).scan())

    profile.write_text(
        json.dumps({"schema_version": "1", "harnesses": ["codex"]}), encoding="utf-8"
    )
    codes = _codes(_make_doctor(tmp_path).scan())
    assert "WS-codex-slop" in codes
    assert "WS-kimi-code-slop" not in codes


@pytest.mark.parametrize("ledger_state", ["absent", "corrupt"])
def test_unreadable_install_ledger_reports_itself_and_never_reclassifies_projections(
    tmp_path: Path, ledger_state: str
) -> None:
    """Bug doctor-unreadable-install-ledger-classifies-projections-as-slop: the store's
    contract (a missing or corrupt record degrades to inaction, never deletion) holds
    downstream — ONE non-fixable ``WS-states-missing`` finding, no harness-dir entry
    classified, and ``fix()`` deletes nothing under the harness dirs."""
    _init_workspace(tmp_path)
    projected = tmp_path / ".claude" / "agents" / "pm.md"
    projected.parent.mkdir(parents=True)
    projected.write_text("projected", encoding="utf-8")
    ledger = tmp_path / ".dadaia" / _STATE_ZONE.name / "install_ledger.json"
    if ledger_state == "corrupt":
        ledger.write_text("{not json", encoding="utf-8")
    else:
        ledger.unlink()

    doctor = _make_doctor(tmp_path)
    findings = doctor.scan()

    ledger_path = f"{_STATE_ZONE.name}/install_ledger.json"
    reported = [f for f in findings if f.path == ledger_path and not f.canonical]
    assert [(f.code, f.verdict, f.fixable, f.detail) for f in reported] == [
        (
            f"WS-{_STATE_ZONE.name}-missing",
            FindingVerdict.MISSING,
            False,
            "(run dadaia public install)",
        )
    ]
    assert not any(f.path.startswith(".claude/") for f in findings)

    actions = doctor.fix()

    assert projected.read_text(encoding="utf-8") == "projected"
    assert not any("install_ledger.json" in action for action in actions)
    assert not (tmp_path / ".dadaia" / _STATE_ZONE.name / "install_ledger.json").is_dir()


def test_exception_globs_match_workspace_relative_paths_inside_harness_dirs(
    tmp_path: Path,
) -> None:
    """FR6: a glob matches on the entry basename OR its workspace-relative path, at the root
    and inside the harness dirs — ``.claude/settings.local.json`` and
    ``.codex/skills/godot-*`` both suppress the slop finding."""
    _init_workspace(tmp_path)
    _write_ledger(tmp_path, ".claude/agents/pm.md", ".codex/skills/dd-x/SKILL.md")
    (tmp_path / ".claude" / "settings.local.json").write_text("{}", encoding="utf-8")
    godot = tmp_path / ".codex" / "skills" / "godot-mcp"
    godot.mkdir(parents=True)
    (godot / "SKILL.md").write_text("x", encoding="utf-8")
    (tmp_path / INSTANCE_EXCEPTIONS).write_text(
        ".claude/settings.local.json\n.codex/skills/godot-*\n", encoding="utf-8"
    )

    found = _by_path(_make_doctor(tmp_path).scan())

    assert found[".claude/settings.local.json"].code == "WS-claude-operator"
    assert found[".codex/skills/godot-mcp"].code == "WS-codex-operator"
    assert not [f for f in found.values() if f.verdict is FindingVerdict.SLOP]


# ---------------------------------------------------------------------------
# Step 3 — the .dadaia/ top level
# ---------------------------------------------------------------------------


def test_dadaia_top_level_zone_or_root_file_else_slop(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    dadaia = tmp_path / ".dadaia"
    for name in DADAIA_ROOT_FILES:
        (dadaia / name).write_text("x", encoding="utf-8")
    (dadaia / "reports").mkdir()
    (dadaia / ".DS_Store").write_text("", encoding="utf-8")
    (dadaia / _OPERATOR_ZONE.name / "some-clone").mkdir(parents=True)

    found = _by_path(_make_doctor(tmp_path).scan())

    for name in DADAIA_ROOT_FILES:
        assert found[name].code == "WS-dadaia-canon"
    assert found[_STATE_ZONE.name].code == "WS-dadaia-canon"
    assert found[_OPERATOR_ZONE.name].code == "WS-dadaia-canon"
    assert found["reports"].code == "WS-dadaia-slop"
    assert found[".DS_Store"].code == "WS-dadaia-slop"


def test_absent_init_or_install_zone_is_missing_and_fixable(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    (tmp_path / ".dadaia" / _INSTALL_ZONE.name).rmdir()

    findings = _make_doctor(tmp_path).scan()
    missing = [f for f in findings if f.verdict is FindingVerdict.MISSING]

    assert [(f.code, f.path, f.fixable) for f in missing] == [
        (f"WS-{_INSTALL_ZONE.name}-missing", _INSTALL_ZONE.name, True)
    ]
    # OPERATOR and MANAGED zones are never reported missing — they are never walked.
    assert not any(_OPERATOR_ZONE.name in f.code for f in findings)


# ---------------------------------------------------------------------------
# Step 4 — the closed-canon zones
# ---------------------------------------------------------------------------


def test_closed_canon_zones_flag_every_non_canon_entry(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    dadaia = tmp_path / ".dadaia"
    (dadaia / _STATE_ZONE.name / "ctx_locks").mkdir()
    for zone in zones_with_canon():
        assert zone.canon is not None
        (dadaia / zone.name).mkdir(exist_ok=True)
        (dadaia / zone.name / "stray.bin").write_bytes(b"")
        first_glob = sorted(zone.canon)[0]
        (dadaia / zone.name / first_glob.replace("*", "sample")).write_text("", encoding="utf-8")

    found = _by_path(_make_doctor(tmp_path).scan())

    assert found[f"{_STATE_ZONE.name}/ctx_locks"].code == f"WS-{_STATE_ZONE.name}-slop"
    assert found[f"{_STATE_ZONE.name}/spec_contexts.json"].verdict is FindingVerdict.CANON
    for zone in zones_with_canon():
        assert zone.canon is not None
        assert found[f"{zone.name}/stray.bin"].code == f"WS-{zone.name}-slop"
        sample = sorted(zone.canon)[0].replace("*", "sample")
        assert found[f"{zone.name}/{sample}"].verdict is FindingVerdict.CANON


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

    actions = _make_doctor(tmp_path).fix(expired_only=True)

    assert actions == [
        f"WS-{_STATE_ZONE.name}-missing: created '{_STATE_ZONE.name}/harness_profile.json'"
    ]
    assert json.loads(_profile(tmp_path).read_text(encoding="utf-8")) == {
        "schema_version": "1",
        "harnesses": ["claude", "codex"],
    }
    assert not [f for f in _make_doctor(tmp_path).scan() if f.verdict is FindingVerdict.MISSING]


# ---------------------------------------------------------------------------
# Step 5 — the TTL zones
# ---------------------------------------------------------------------------


def test_ttl_zone_expires_by_mtime_and_the_emptied_directory(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    zone_dir = tmp_path / ".dadaia" / _TTL_ZONE.name
    old_dir = zone_dir / "claude" / "20260801"
    old_dir.mkdir(parents=True)
    old = old_dir / "x.png"
    old.write_bytes(b"PNG")
    _age(old)
    fresh = zone_dir / "claude" / "today.txt"
    fresh.write_text("fresh", encoding="utf-8")

    found = _by_path(_make_doctor(tmp_path).scan())
    code = f"WS-{_TTL_ZONE.name.lstrip('.')}-expired"

    assert found[f"{_TTL_ZONE.name}/claude/20260801/x.png"].code == code
    assert found[f"{_TTL_ZONE.name}/claude/20260801/x.png"].detail == "(mtime 2d > ttl 1d)"
    assert found[f"{_TTL_ZONE.name}/claude/20260801"].code == code
    assert found[f"{_TTL_ZONE.name}/claude/20260801"].detail == "(emptied by expiry)"
    assert found[f"{_TTL_ZONE.name}/claude/today.txt"].verdict is FindingVerdict.CANON
    assert f"{_TTL_ZONE.name}/claude" not in found


def test_every_ttl_zone_uses_its_own_code_and_ttl(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    for zone in zones_with_ttl():
        zone_dir = tmp_path / ".dadaia" / zone.name
        zone_dir.mkdir(exist_ok=True)
        stale = zone_dir / "stale"
        stale.write_text("", encoding="utf-8")
        _age(stale)

    codes = _codes(_make_doctor(tmp_path).scan())

    assert {f"WS-{zone.name.lstrip('.')}-expired" for zone in zones_with_ttl()} <= codes


def test_zone_agents_md_is_never_a_ttl_candidate(tmp_path: Path) -> None:
    """Bug public-install-restores-expired-zone-agents-reblocks-preflight: the projected ``AGENTS.md`` inside
    a TTL zone is canon by projection, whatever its mtime."""
    _init_workspace(tmp_path)
    zone_dir = tmp_path / ".dadaia" / _TTL_ZONE.name
    zone_dir.mkdir(exist_ok=True)
    law = zone_dir / "AGENTS.md"
    law.write_text("# zone law", encoding="utf-8")
    _age(law, time.time() - 400 * 86_400)

    found = _by_path(_make_doctor(tmp_path).scan())

    assert found[f"{_TTL_ZONE.name}/AGENTS.md"].verdict is FindingVerdict.CANON
    assert not _make_doctor(tmp_path).fix(expired_only=True)
    assert law.exists()


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

    _make_doctor(ws).fix(expired_only=True)

    assert not link.exists() and not link.is_symlink()
    assert victim.read_text(encoding="utf-8") == "keep"


def test_ttl_walk_treats_an_entry_that_vanishes_mid_walk_as_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk: an entry a parallel reaper
    removes between ``iterdir`` and ``lstat`` — a file, or an empty directory the walk has
    already descended into — is simply absent: no finding, no exception, and every other
    entry is still classified."""
    _init_workspace(tmp_path)
    zone_dir = tmp_path / ".dadaia" / _TTL_ZONE.name
    zone_dir.mkdir(exist_ok=True)
    gone_file = zone_dir / "gone.txt"
    gone_file.write_text("", encoding="utf-8")
    gone_dir = zone_dir / "gone_dir"
    gone_dir.mkdir()
    (zone_dir / "kept.txt").write_text("", encoding="utf-8")
    real_entries = DoctorService._entries

    def racing_entries(directory: Path) -> list[Path]:
        entries = real_entries(directory)
        if directory == zone_dir:
            gone_file.unlink()
        elif directory == gone_dir:
            gone_dir.rmdir()
        return entries

    monkeypatch.setattr(DoctorService, "_entries", staticmethod(racing_entries))

    found = _by_path(_make_doctor(tmp_path).scan())

    assert found[f"{_TTL_ZONE.name}/kept.txt"].verdict is FindingVerdict.CANON
    assert f"{_TTL_ZONE.name}/gone.txt" not in found
    assert f"{_TTL_ZONE.name}/gone_dir" not in found


def test_operator_and_managed_zones_are_never_walked(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    clone = tmp_path / ".dadaia" / _OPERATOR_ZONE.name / "clone"
    clone.mkdir(parents=True)
    stale = clone / "README.md"
    stale.write_text("reference", encoding="utf-8")
    _age(stale)
    venv = tmp_path / ".dadaia" / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "site.py").write_text("", encoding="utf-8")

    findings = _make_doctor(tmp_path).scan()

    assert not any("README.md" in f.path or "site.py" in f.path for f in findings)
    _make_doctor(tmp_path).fix()
    assert stale.read_text(encoding="utf-8") == "reference"


# ---------------------------------------------------------------------------
# The score, the reaper order, --expired-only
# ---------------------------------------------------------------------------


def test_compliance_counts_canon_and_operator_over_every_entry(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    (tmp_path / "junk").mkdir()
    (tmp_path / "shot.png").write_bytes(b"")
    (tmp_path / INSTANCE_EXCEPTIONS).write_text("*.png\n", encoding="utf-8")

    findings = _make_doctor(tmp_path).scan()
    score = compliance(findings)

    non_canonical = [f for f in findings if f.verdict is FindingVerdict.SLOP]
    assert [f.path for f in non_canonical] == ["junk"]
    assert score.total == len(findings)
    assert score.canonical == len(findings) - 1
    assert score.percent == round(100 * score.canonical / score.total)


def test_fix_expired_only_stops_before_slop(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    (tmp_path / ".dadaia" / _INSTALL_ZONE.name).rmdir()
    junk = tmp_path / "junk.txt"
    junk.write_text("", encoding="utf-8")
    zone_dir = tmp_path / ".dadaia" / _TTL_ZONE.name
    zone_dir.mkdir(exist_ok=True)
    stale = zone_dir / "stale"
    stale.write_text("", encoding="utf-8")
    _age(stale)

    actions = _make_doctor(tmp_path).fix(expired_only=True)

    assert not stale.exists()
    assert junk.exists()
    assert (tmp_path / ".dadaia" / _INSTALL_ZONE.name).is_dir()
    assert [a.split(":")[0] for a in actions] == [
        f"WS-{_INSTALL_ZONE.name}-missing",
        f"WS-{_TTL_ZONE.name.lstrip('.')}-expired",
    ]

    actions = _make_doctor(tmp_path).fix()

    assert not junk.exists()
    assert actions == ["WS-root-slop: deleted 'junk.txt'"]


@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0,
    reason="chmod 0o555 denies unlink only for a non-root POSIX user",
)
def test_fix_skips_and_reports_an_undeletable_entry_and_finishes_the_pass(
    tmp_path: Path,
) -> None:
    """Bug doctor-fix-aborts-whole-pass-on-first-undeletable-entry (same class as
    retention-sweep-crashes-on-permission-denied, 903f8b89): an entry the process cannot
    delete is skipped and reported with its errno, the pass reaches every other entry, the
    returned actions name only what was actually deleted, and the entry stays a finding."""
    _init_workspace(tmp_path)
    zone = tmp_path / ".dadaia" / _TTL_ZONE.name
    locked = zone / "x" / "deps"
    locked.mkdir(parents=True)
    undeletable = locked / "a.js"
    undeletable.write_text("", encoding="utf-8")
    other = zone / "x" / "other.txt"
    other.write_text("", encoding="utf-8")
    for path in (undeletable, other, locked, locked.parent):
        _age(path)
    locked.chmod(0o555)
    try:
        doctor = _make_doctor(tmp_path)
        actions = doctor.fix()
        remaining = _by_path(doctor.scan())
    finally:
        locked.chmod(0o755)

    assert not other.exists()
    assert undeletable.exists()
    deleted = [a for a in actions if ": deleted '" in a]
    skipped = [a for a in actions if ": skipped '" in a]
    assert f"WS-{_TTL_ZONE.name}-expired: deleted '{_TTL_ZONE.name}/x/other.txt'" in deleted
    assert not any("a.js" in a for a in deleted)
    assert any(f"'{_TTL_ZONE.name}/x/deps/a.js' (errno 13" in a for a in skipped), actions
    assert remaining[f"{_TTL_ZONE.name}/x/deps/a.js"].verdict is FindingVerdict.EXPIRED


def test_fix_skips_and_reports_a_failing_migration_or_seed_and_still_deletes_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk (finding 2, same
    skip-and-report family as doctor-fix-aborts-whole-pass-on-first-undeletable-entry): a
    migration or seed the process cannot write is skipped and reported with its errno in the
    same ``<code>: skipped '<path>' (errno N: …)`` shape as a deletion, and the pass still
    reaches 'delete expired'."""
    _init_workspace(tmp_path)
    legacy = tmp_path / ".dadaia" / _STATE_ZONE.name / "root_exceptions.txt"
    legacy.write_text("*.png\n", encoding="utf-8")
    _profile(tmp_path).unlink()
    zone_dir = tmp_path / ".dadaia" / _TTL_ZONE.name
    zone_dir.mkdir(exist_ok=True)
    stale = zone_dir / "stale"
    stale.write_text("", encoding="utf-8")
    _age(stale)

    def denied(*_: object, **__: object) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "write_text", denied)
    monkeypatch.setattr(JsonHarnessProfileStore, "write", denied)

    actions = _make_doctor(tmp_path).fix(expired_only=True)

    assert legacy.exists()
    assert not (tmp_path / INSTANCE_EXCEPTIONS).exists()
    assert not _profile(tmp_path).exists()
    assert not stale.exists()
    assert [a.split(": ", 1)[1].split(" (")[0] for a in actions] == [
        "skipped 'root_exceptions.txt'",
        f"skipped '{_STATE_ZONE.name}/harness_profile.json'",
        f"deleted '{_TTL_ZONE.name}/stale'",
    ]
    assert all("(errno 13: Permission denied)" in a for a in actions[:2]), actions
    assert actions[1].startswith(f"WS-{_STATE_ZONE.name}-missing: ")
    assert actions[2] == f"WS-{_TTL_ZONE.name}-expired: deleted '{_TTL_ZONE.name}/stale'"


@pytest.mark.parametrize("target_inside_workspace", [True, False])
def test_a_symlinked_zone_root_is_never_walked(
    tmp_path: Path, target_inside_workspace: bool
) -> None:
    """Bug doctor-walks-symlinked-zone-root-into-a-repo-tree (CWE-59): a zone root that is
    itself a symlink used to be walked — ``iterdir`` follows the link — and every entry of the
    target passed the per-entry containment guard because its parent resolves inside the
    workspace (``.dadaia/handoff -> ../repos/<victim>`` yielded ``WS-handoff-expired`` on a
    repo file the SessionStart ``--fix --expired-only`` lane then unlinked). ``_entries`` now
    refuses to walk a symlinked root: no per-entry finding, nothing under the target touched.
    Supersedes the finding-6 pin of doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk,
    whose per-entry refusal only covered a target OUTSIDE the workspace."""
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
    actions = _make_doctor(ws).fix(expired_only=True)

    assert not any("old.txt" in f.path for f in findings), [f.path for f in findings]
    assert victim.read_text(encoding="utf-8") == "keep"
    assert zone_dir.is_symlink()
    assert actions == []


def test_fix_removes_state_and_session_slop_recursively(tmp_path: Path) -> None:
    """The retired lock/pointer state (``states/ctx_locks``, ``sessions/runtime``) is plain
    closed-canon slop now — no code of its own."""
    _init_workspace(tmp_path)
    locks = tmp_path / ".dadaia" / _STATE_ZONE.name / "ctx_locks"
    locks.mkdir()
    (locks / "stale.lock.json").write_text("{}", encoding="utf-8")
    sessions = next(z for z in zones_with_canon() if z.cls is ZoneClass.PROTECTED)
    pointer = tmp_path / ".dadaia" / sessions.name / "runtime"
    pointer.mkdir(parents=True)

    doctor = _make_doctor(tmp_path)
    assert {f"WS-{_STATE_ZONE.name}-slop", f"WS-{sessions.name}-slop"} <= _codes(doctor.scan())
    doctor.fix()

    assert not locks.exists()
    assert not pointer.exists()
    assert compliance(_make_doctor(tmp_path).scan()).percent == 100
