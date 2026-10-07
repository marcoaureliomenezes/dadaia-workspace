"""0.4.6 AC2, AC4, AC6, AC7, AC9 (FR3 one scan, FR4 the reaper, FR5 TTLs,
FR8 the profile seed); size: SMALL.

``DoctorService.scan()`` is the ONE registry-driven walk; every entry gets one verdict and one
code ``WS-<zone>-<verdict>``, and ``fix()`` consumes that list in the FR4 order. Expectations
are derived from the registry views, never a spelled zone name.
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
    DADAIAIGNORE,
    LEVEL1_SEEDS,
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
from tests.fixtures.stores import context_store

_TTL_ZONE = next(z for z in zones_with_ttl() if z.cls is ZoneClass.EPHEMERAL)
_STATE_ZONE = next(z for z in zones_with_canon() if z.creator is Creator.INIT)
_OPERATOR_ZONE = next(z for z in workspace_layout.DADAIA_ZONES if z.creator is Creator.OPERATOR)
_INSTALL_ZONE = next(z for z in provisioned_zones() if z.creator is Creator.INSTALL)
_TWO_DAYS_AGO = time.time() - 2 * 86_400


def _make_doctor(root: Path) -> DoctorService:
    return DoctorService(context_store(root / ".dadaia" / "states"), GitSubprocessClient(), root)


def _init_workspace(root: Path) -> None:
    """The minimal compliant skeleton: every INIT/INSTALL zone present, the level-1 seeds."""
    for name in LEVEL1_SEEDS:
        (root / name).write_text("", encoding="utf-8")
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


_REGISTRY = json.dumps({"contexts": [
    {"name": "alpha", "state": "ALIVE", "repo_slug": "main-r", "associated_repos": [{"slug": "assoc-r"}]},
    {"name": "gone", "state": "DEAD", "repo_slug": "dead-r"},
]})  # fmt: skip
_PLACES = {
    "random_junk.txt": "WS-root-slop", ".ruff_cache": "WS-root-slop", "shot.png": "WS-root-operator",
    "AGENTS.md": "WS-root-canon", ".claude": "WS-root-canon", ".git": "WS-root-slop",
    "junk": "WS-dadaia-slop", ".DS_Store": "WS-dadaia-slop", "kept.png": "WS-dadaia-operator",
    **{n: "WS-dadaia-canon" for n in (*DADAIA_ROOT_FILES, _STATE_ZONE.name, _OPERATOR_ZONE.name)},
    "repos/alpha": "WS-repos-slop", "repos/kept": "WS-repos-operator",
    **{f"repos/{r}": "WS-repos-canon" for r in ("main-r", "assoc-r", "dead-r")},
    "worktrees/dead-r": "WS-worktrees-slop", "worktrees/kept": "WS-worktrees-operator",
    "worktrees/assoc-r": "WS-worktrees-canon", "worktrees/AGENTS.md": "WS-worktrees-canon",
}  # fmt: skip


@pytest.mark.parametrize(
    ("registry", "expected"),
    [
        pytest.param(_REGISTRY, _PLACES, id="registered"),
        *(pytest.param(text, {"repos/alpha": "WS-repos-canon", "worktrees/dead-r": "WS-worktrees-canon"}, id=f"unreadable-registry-{text}")
          for text in ("{", '{"contexts": 5}')),
    ],
)  # fmt: skip
def test_four_places_classify_every_entry(
    tmp_path: Path, registry: str, expected: dict[str, str]
) -> None:
    """T-050-116 (ADR 0132), sa-gate-allows-root-entries-the-reaper-moves#E2, #E4, #E6: one walk
    over the root, ``.dadaia/``, ``repos/`` and ``worktrees/`` — unlisted = slop, globbed =
    operator; repo slugs, never context names, DEAD ones under ``repos/`` only; an unreadable
    registry keeps every ``repos/<r>`` and ``worktrees/<r>``."""
    _init_workspace(tmp_path)
    dadaia = tmp_path / ".dadaia"
    (dadaia / _STATE_ZONE.name / "spec_contexts.json").write_text(registry, encoding="utf-8")
    for name in (
        ".claude",
        ".git",
        ".ruff_cache",
        ".dadaia/junk",
        ".dadaia/" + _OPERATOR_ZONE.name,
    ):
        (tmp_path / name).mkdir()
    for name in ("alpha", "kept", "main-r", "assoc-r", "dead-r"):
        (tmp_path / "repos" / name).mkdir()
    for name in ("dead-r", "kept", "assoc-r"):
        (tmp_path / "worktrees" / name).mkdir(parents=True)
    for name in ("random_junk.txt", "shot.png", "worktrees/AGENTS.md"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    for name in (*DADAIA_ROOT_FILES, ".DS_Store", "kept.png"):
        (dadaia / name).write_text("x", encoding="utf-8")
    (tmp_path / DADAIAIGNORE).write_text(
        "# comment\n*.png\n.dadaia/*.png\nrepos/kept\nworktrees/kept\n", encoding="utf-8"
    )

    found = _make_doctor(tmp_path).scan()

    assert {p: c for p, c in ((f.path, f.code) for f in found) if p in expected} == expected
    assert "# comment" not in {f.detail for f in found}


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
    ``sessions/runtime`` have no code of their own), and so is an unreadable session record
    (corrupt-session-record-never-collected, AC1.4); fix() holds them and leaves a fully
    canonical scan."""
    _init_workspace(tmp_path)
    dadaia = tmp_path / ".dadaia"
    (dadaia / _STATE_ZONE.name / "ctx_locks").mkdir()
    (dadaia / _STATE_ZONE.name / "ctx_locks" / "stale.lock.json").write_text("{}", "utf-8")
    sessions = next(z for z in zones_with_canon() if z.cls is ZoneClass.PROTECTED)
    (dadaia / sessions.name / "runtime").mkdir(parents=True)
    (dadaia / sessions.name / "corrupt.json").write_text("{", "utf-8")  # canon name, unreadable
    for zone in zones_with_canon():
        assert zone.canon is not None
        (dadaia / zone.name).mkdir(exist_ok=True)
        (dadaia / zone.name / "stray.bin").write_bytes(b"")
        (dadaia / zone.name / sorted(zone.canon)[0].replace("*", "sample")).write_text(
            "{}", "utf-8"
        )

    found = _by_path(_make_doctor(tmp_path).scan())

    assert found[f"{_STATE_ZONE.name}/ctx_locks"].code == f"WS-{_STATE_ZONE.name}-slop"
    assert found[f"{sessions.name}/runtime"].code == f"WS-{sessions.name}-slop"
    assert found[f"{sessions.name}/corrupt.json"].code == f"WS-{sessions.name}-slop"  # AC1.4
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
    (stale := zone_dir / "stale.txt").touch()
    _age(stale)  # the positive control: a walk that saw nothing would miss it
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

    assert [p for p in found if p.startswith(f"{_TTL_ZONE.name}/")] == [
        f"{_TTL_ZONE.name}/stale.txt"
    ]


# ---------------------------------------------------------------------------
# The reaper never aborts a pass
# ---------------------------------------------------------------------------


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
    (ws / ".dadaia" / _STATE_ZONE.name / "spec_contexts.json").write_text(_REGISTRY, "utf-8")
    target = (ws / "repos" / "main-r") if target_inside_workspace else (tmp_path / "outside")
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


def test_fix_migrates_the_legacy_exceptions_and_never_touches_operator_files(
    tmp_path: Path,
) -> None:
    """ADRs 0092, 0093, 0145: a missing ``.dadaiaignore`` is seeded 1:1 from the legacy
    file, which is then slop and held; an invalid line is reported and never fixed. ADR 0146:
    a root ``.env`` is a non-fixable finding the reaper never moves."""
    _init_workspace(tmp_path)
    (tmp_path / DADAIAIGNORE).unlink()
    legacy = tmp_path / ".dadaia/states/instance_exceptions.txt"
    legacy.write_text("*.png\n!keep\n", encoding="utf-8")
    (tmp_path / "shot.png").write_bytes(b"PNG")  # admitted only by the migrated line
    (tmp_path / ".env").write_text("K=v\n", encoding="utf-8")
    assert _by_path(_make_doctor(tmp_path).scan())[DADAIAIGNORE].verdict is FindingVerdict.MISSING
    _make_doctor(tmp_path).fix()
    assert (tmp_path / DADAIAIGNORE).read_text(encoding="utf-8") == "*.png\n!keep\n"
    assert not legacy.exists()
    assert (tmp_path / "shot.png").exists()  # judged after the seed, never reaped
    found = [f for f in _make_doctor(tmp_path).scan() if f.verdict is FindingVerdict.SLOP]
    (invalid,) = [f for f in found if f.path == DADAIAIGNORE]
    (env,) = [f for f in found if f.path == ".env"]
    assert not invalid.fixable and "!keep" in invalid.detail
    assert not env.fixable and "outside the workspace" in env.detail
    _make_doctor(tmp_path).fix()
    assert (tmp_path / DADAIAIGNORE).is_file() and (tmp_path / ".env").is_file()


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="root-allows-git-and-gitignore-though-root-is-never-a-repo")  # fmt: skip
def test_fix_on_a_root_holding_a_git_dir_moves_nothing(tmp_path: Path) -> None:
    """A root ``.git/`` is a finding the reaper never moves: it is a repository's history, so
    the finding is unfixable and names the operator's act."""
    _init_workspace(tmp_path)
    (tmp_path / ".git").mkdir()
    head = tmp_path / ".git" / "HEAD"
    head.write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git,) = [f for f in _make_doctor(tmp_path).scan() if f.path == ".git"]
    assert git.verdict is FindingVerdict.SLOP and not git.fixable
    assert git.fix.startswith("Operator action:")
    _make_doctor(tmp_path).fix()
    assert head.read_text(encoding="utf-8") == "ref: refs/heads/main\n"
