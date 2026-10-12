"""The specs section's own behaviours at the CLI: a legacy state-file name is never
clobbered, an untraced Origin id is cleared by its printed fix, and the SessionStart lane
re-creates missing level-1 entries. The fix-line proofs of every specs rule live in
``tests/core/test_cli_line__fix_line_contract.py``.

size: MEDIUM.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.commands.doctor import _build_specs_doctor, _ledgers_section
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.core.workspace_layout import LEVEL1_SEEDS, occupied, provisioned_zones
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.features.backlog.test_doctor import _active_entry
from tests.features.specs.test_doctor import _make_clean_specs_tree
from tests.fixtures.harness_env import run_bash, suite_env
from tests.fixtures.stores import context_store

_RELEASE = "1.2.3"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _plant_legacy_state_name(root: Path) -> None:
    """The legacy state-file name, renamed by `doctor --fix`."""
    state = root / "specs" / "releases" / _RELEASE / "_RELEASE.json"
    state.rename(state.with_name("RELEASE.json"))


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        env=suite_env(
            {}, root, overrides={"PATH": "/usr/bin:/bin", "GIT_CONFIG_GLOBAL": "/dev/null"}
        ),
    )


@pytest.fixture(scope="module")
def clean_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A git-backed fixture tree, built once per module: a fix line may legitimately be a
    `git rm`/`git mv`."""
    root = tmp_path_factory.mktemp("clean")
    _make_clean_specs_tree(root, _RELEASE)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "fixture")
    return root


@pytest.fixture
def repo(tmp_path: Path, clean_repo: Path) -> Path:
    """This test's own copy of the clean tree — every plant and fix mutates it."""
    shutil.copytree(clean_repo, tmp_path, symlinks=True, dirs_exist_ok=True)
    return tmp_path


def _doctor(root: Path) -> SpecsDoctor:
    """The specs doctor the CLI builds for *root* (templates, public tree, repo root)."""
    doctor = _build_specs_doctor(root / "specs", None)
    assert doctor is not None
    return doctor


def test_spec_doc_046_never_clobbers_a_canonical_state_file(repo: Path) -> None:
    """ADR 0007: with both names on disk SPEC-DOC-046 is silent, and a fix stamped before
    `_RELEASE.json` appeared re-checks and renames nothing."""
    release = repo / "specs" / "releases" / _RELEASE
    _plant_legacy_state_name(repo)
    doctor = _doctor(repo)
    [stale] = [i for i in doctor.check() if i.code == "SPEC-DOC-046"]
    (release / "_RELEASE.json").write_text("{}", encoding="utf-8")
    assert [i for i in doctor.check() if i.code == "SPEC-DOC-046"] == []
    doctor.fix([stale])
    assert (release / "RELEASE.json").is_file()
    assert (release / "_RELEASE.json").read_text(encoding="utf-8") == "{}"


def test_an_untraced_origin_id_is_cleared_by_its_printed_fix(repo: Path) -> None:
    """AC3.2 (review F4; SPEC-DOC-048's row re-homed): after the sweep, a carried entry with
    no exit is an error on the real Origin line; its printed fix writes the pointer back."""
    specs = repo / "specs"
    _write(specs / "backlog/BACKLOG.json", json.dumps(
        {"schema": "backlog-v1", "active": [_active_entry("carried", "c", "candidate")]}))  # fmt: skip
    spec = specs / "releases" / _RELEASE / "rc-1" / "SPEC.md"
    spec.write_text(spec.read_text("utf-8").replace("operator-demand", "backlog:carried"), "utf-8")

    def origin_errors() -> list[SectionFinding]:
        found = _ledgers_section(None, specs).findings
        rows = [f for f in found if "Origin" in f.message]
        assert all(f.error for f in rows), rows  # a listing row never reaches the doctor
        return rows

    assert origin_errors() == []  # before the sweep the carried id is only listed
    state = specs / "releases" / _RELEASE / "_RELEASE.json"
    sweep = {"ts": "2026-01-01T00:00:00Z", "agent": "a", "kind": "dispositions", "text": "t"}
    state.write_text(json.dumps({**json.loads(state.read_text("utf-8")), "log": [sweep]}))

    [before] = origin_errors()
    assert before.message.startswith(f"releases/{_RELEASE}/rc-1/SPEC.md:5 "), before.message
    run_bash(before.fix, cwd=repo, check=True)
    assert origin_errors() == []


def _plant_file(entry: Path, _outside: Path) -> None:
    entry.write_text("# mine\n", encoding="utf-8")


def _plant_link(entry: Path, outside: Path) -> None:
    entry.symlink_to(outside)


def _identity(entry: Path) -> tuple[int, str]:
    """lstat identity: the inode plus the link target or the content — never followed."""
    body = os.readlink(entry) if entry.is_symlink() else entry.read_text(encoding="utf-8")
    return entry.lstat().st_ino, body


@pytest.mark.parametrize(
    ("present", "plant"),
    [(".dadaiaignore", _plant_file), ("prompt.md", _plant_file), ("prompt.md", _plant_link)],
    ids=["dadaiaignore", "prompt", "dangling-link"],
)
def test_the_session_lane_re_creates_missing_core_and_rewrites_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    present: str,
    plant: Callable[[Path, Path], None],
) -> None:
    """AC2.4 (ADR 0096): the SessionStart lane re-creates a missing level-1
    entry (`.dadaiaignore`, `prompt.md`, every provisioned zone) and rewrites no present one —
    a dangling link is present, never written through."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside" / "pwned.md"
    outside.parent.mkdir()
    plant(tmp_path / present, outside)
    planted = _identity(tmp_path / present)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        container,
        "build_doctor_service",
        lambda root: DoctorService(
            context_store(root / ".dadaia/states"), GitSubprocessClient(), root
        ),
    )

    lane = CliRunner().invoke(app, ["doctor", "--fix", "--expired-only", "--quiet"])

    assert lane.exit_code == 0, lane.output
    assert all(occupied(tmp_path / name) for name in LEVEL1_SEEDS) and not outside.exists()
    assert all((tmp_path / ".dadaia" / zone.name).is_dir() for zone in provisioned_zones())
    assert _identity(tmp_path / present) == planted
