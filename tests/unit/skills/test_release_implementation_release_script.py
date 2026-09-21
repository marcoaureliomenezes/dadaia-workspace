"""Intent: CONTRACT — dd-release-implementation/scripts/release.py owns _RELEASE.json,
the candidate trio and releases_histo.jsonl (0.4.7 c7 T-047-66: the release ledger verbs
move into a stdlib skill script). Size: SMALL.

The script reads its two schemas from ``scripts/schemas/`` BESIDE itself — copies
`public stage` makes — so every test stages the folder exactly as stage does.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_SCRIPTS = _PUBLIC / "skills" / "dd-release-implementation" / "scripts"
_SCHEMAS = (
    _PUBLIC / "schemas" / "releases" / "release-state-v1.schema.json",
    _PUBLIC / "schemas" / "histo" / "histo-record-v1.schema.json",
)
_TRIO = ("SPEC.md", "PLAN.md", "TASKS.md")


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: release.py with both schema copies beside it."""
    staged = tmp_path / "staged" / "scripts"
    (staged / "schemas").mkdir(parents=True)
    for module in sorted(_SCRIPTS.glob("*.py")):
        shutil.copy2(module, staged / module.name)
    for schema in _SCHEMAS:
        shutil.copy2(schema, staged / "schemas" / schema.name)
    return staged / "release.py"


def _run(script: Path, *argv: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
    )


def _state(release_id: str, **over: object) -> dict[str, object]:
    document: dict[str, object] = {
        "schema": "release-state-v1",
        "release": release_id,
        "phase": "DEFINITION",
        "rc": None,
        "defined": None,
        "implemented": None,
        "shipped": None,
        "log": [],
    }
    document.update(over)
    return document


def _release(
    specs: Path, release_id: str, *, tasks: str = "- [x] T-1 — done\n", **over: object
) -> Path:
    """One live release directory with its trio and its state document."""
    release_dir = specs / "releases" / release_id
    release_dir.mkdir(parents=True, exist_ok=True)
    for name in _TRIO:
        body = tasks if name == "TASKS.md" else ""
        release_dir.joinpath(name).write_text(
            f"# {name}\n\n**Status:** Approved\n\n{body}", encoding="utf-8"
        )
    release_dir.joinpath("_RELEASE.json").write_text(
        json.dumps(_state(release_id, **over), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release_dir


def _specs(root: Path) -> Path:
    specs = root / "specs"
    (specs / "releases" / "_archive").mkdir(parents=True, exist_ok=True)
    (specs / "releases" / "_archive" / "releases_histo.jsonl").write_text("", encoding="utf-8")
    return specs


def _read(path: Path) -> dict[str, object]:
    document: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return document


def _tree_hash(root: Path) -> list[tuple[str, str]]:
    """Every file under *root* as (relative posix path, sha256) — the transaction probe."""
    return sorted(
        (
            p.relative_to(root).as_posix(),
            hashlib.sha256(p.read_bytes()).hexdigest(),
        )
        for p in root.rglob("*")
        if p.is_file()
    )


# ── new ───────────────────────────────────────────────────────────────────────


def test_new_writes_the_spec_stub_and_the_state_in_one_act(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    result = _run(script, "new", "0.6.0", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    release_dir = specs / "releases" / "0.6.0"
    assert "**Status:** Draft" in (release_dir / "SPEC.md").read_text(encoding="utf-8")
    state = _read(release_dir / "_RELEASE.json")
    assert state["schema"] == "release-state-v1"
    assert state["phase"] == "DEFINITION"
    assert state["release"] == "0.6.0"
    assert state["rc"] is None


def test_new_refuses_a_second_live_release_with_one_fix_line(script: Path, tmp_path: Path) -> None:
    """ADR 0005: exactly one live release, ever. The refusal writes nothing."""
    specs = _specs(tmp_path)
    _release(specs, "0.5.0")
    before = _tree_hash(specs)
    result = _run(script, "new", "0.6.0", "--specs", str(specs))
    assert result.returncode == 1
    assert "0.5.0" in result.stderr
    fixes = [line for line in result.stderr.splitlines() if line.startswith("fix: ")]
    assert len(fixes) == 1, result.stderr
    assert not (specs / "releases" / "0.6.0").exists()
    assert _tree_hash(specs) == before


def test_new_refuses_a_non_semver_id(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    assert _run(script, "new", "v0.6.0", "--specs", str(specs)).returncode == 1


# ── phase ─────────────────────────────────────────────────────────────────────


def test_phase_implementation_stamps_defined(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0")
    result = _run(script, "phase", "IMPLEMENTATION", "--sha", "abc1234", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    state = _read(specs / "releases" / "0.5.0" / "_RELEASE.json")
    assert state["phase"] == "IMPLEMENTATION"
    assert isinstance(state["defined"], dict)
    assert state["defined"]["sha"] == "abc1234"


def test_phase_closure_stamps_implemented_with_the_candidate_number(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION", rc=2)
    result = _run(script, "phase", "CLOSURE", "--sha", "beef123", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    state = _read(specs / "releases" / "0.5.0" / "_RELEASE.json")
    assert state["phase"] == "CLOSURE"
    assert state["implemented"] == {"sha": "beef123", "rc": 3, "ts": state["implemented"]["ts"]}


def test_phase_refuses_an_out_of_order_transition(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0")
    result = _run(script, "phase", "CLOSURE", "--sha", "abc1234", "--specs", str(specs))
    assert result.returncode == 1
    assert "fix: " in result.stderr
    assert _read(specs / "releases" / "0.5.0" / "_RELEASE.json")["phase"] == "DEFINITION"


def test_phase_implementation_refuses_an_unapproved_trio(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    release_dir = _release(specs, "0.5.0")
    (release_dir / "PLAN.md").write_text("# PLAN.md\n\n**Status:** Draft\n", encoding="utf-8")
    result = _run(script, "phase", "IMPLEMENTATION", "--sha", "abc1234", "--specs", str(specs))
    assert result.returncode == 1
    assert "PLAN.md" in result.stderr


def test_phase_closure_refuses_an_open_task(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION", tasks="- [ ] T-1 — open\n")
    result = _run(script, "phase", "CLOSURE", "--sha", "abc1234", "--specs", str(specs))
    assert result.returncode == 1
    assert "T-1" in result.stderr


def test_phase_refuses_a_malformed_sha(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0")
    assert (
        _run(script, "phase", "IMPLEMENTATION", "--sha", "zz", "--specs", str(specs)).returncode
        == 1
    )


# ── rc-archive ────────────────────────────────────────────────────────────────


def test_rc_archive_moves_the_trio_and_bumps_rc(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    release_dir = _release(specs, "0.5.0", phase="CLOSURE", rc=1)
    (release_dir / "rc-1").mkdir()
    result = _run(script, "rc-archive", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    for name in _TRIO:
        assert not (release_dir / name).exists()
        assert (release_dir / "rc-2" / name).is_file()
    state = _read(release_dir / "_RELEASE.json")
    assert state["rc"] == 2
    assert state["phase"] == "DEFINITION"


def test_rc_archive_refuses_outside_closure(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    result = _run(script, "rc-archive", "--specs", str(specs))
    assert result.returncode == 1
    assert (specs / "releases" / "0.5.0" / "SPEC.md").is_file()


def test_rc_archive_refuses_an_open_task(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="CLOSURE", tasks="- [-] T-9 — reserved\n")
    before = _tree_hash(specs)
    assert _run(script, "rc-archive", "--specs", str(specs)).returncode == 1
    assert _tree_hash(specs) == before


# ── archive ───────────────────────────────────────────────────────────────────


def test_archive_ships_moves_births_and_appends_one_histo_record(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    _release(
        specs,
        "0.5.0",
        phase="CLOSURE",
        rc=1,
        implemented={"sha": "abc1234", "rc": 1, "ts": "2026-01-01T00:00:00Z"},
    )
    result = _run(
        script,
        "archive",
        "0.5.0",
        "--shipped",
        "deadbee",
        "--pr",
        "42",
        "--next",
        "0.5.1",
        "--specs",
        str(specs),
    )
    assert result.returncode == 0, result.stderr
    archived = specs / "releases" / "_archive" / "0.5.0"
    assert (archived / "SPEC.md").is_file()
    state = _read(archived / "_RELEASE.json")
    assert state["phase"] == "ARCHIVED"
    assert state["shipped"]["sha"] == "deadbee"
    assert state["shipped"]["pr"] == 42
    assert (specs / "releases" / "0.5.1" / "_RELEASE.json").is_file()
    histo = (specs / "releases" / "_archive" / "releases_histo.jsonl").read_text(encoding="utf-8")
    records = [json.loads(line) for line in histo.splitlines() if line.strip()]
    assert [r["id"] for r in records] == ["0.5.0"]
    assert records[0]["disposition"] == "delivered"
    assert [line for line in result.stdout.splitlines() if line.startswith("next: git")]


def test_archive_on_an_open_task_leaves_every_file_byte_unchanged(
    script: Path, tmp_path: Path
) -> None:
    """The transaction assertion: a refused archive writes NOTHING, anywhere."""
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="CLOSURE", rc=1, tasks="- [ ] T-7 — still open\n")
    before = _tree_hash(specs)
    result = _run(
        script,
        "archive",
        "0.5.0",
        "--shipped",
        "deadbee",
        "--pr",
        "42",
        "--next",
        "0.5.1",
        "--specs",
        str(specs),
    )
    assert result.returncode == 1
    assert "T-7" in result.stderr
    assert _tree_hash(specs) == before


def test_archive_refuses_a_release_that_is_not_live(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="CLOSURE")
    result = _run(
        script,
        "archive",
        "0.4.9",
        "--shipped",
        "deadbee",
        "--pr",
        "42",
        "--next",
        "0.5.1",
        "--specs",
        str(specs),
    )
    assert result.returncode == 1
    assert "0.5.0" in result.stderr


def test_archive_refuses_a_bad_pr_number(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="CLOSURE")
    result = _run(
        script,
        "archive",
        "0.5.0",
        "--shipped",
        "deadbee",
        "--pr",
        "0",
        "--next",
        "0.5.1",
        "--specs",
        str(specs),
    )
    assert result.returncode == 1


# ── fold ──────────────────────────────────────────────────────────────────────


def _archived(specs: Path, release_id: str, **over: object) -> Path:
    release_dir = specs / "releases" / "_archive" / release_id
    release_dir.mkdir(parents=True, exist_ok=True)
    for name in _TRIO:
        release_dir.joinpath(name).write_text(f"# {name}\n", encoding="utf-8")
    release_dir.joinpath("_RELEASE.json").write_text(
        json.dumps(_state(release_id, phase="ARCHIVED", **over), indent=2) + "\n",
        encoding="utf-8",
    )
    return release_dir


def test_fold_moves_the_trio_into_the_published_versions_next_rc(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.6.0")
    _archived(specs, "0.5.2")
    _archived(specs, "0.4.5", shipped={"sha": "abc1234", "pr": 7, "ts": "2026-01-01T00:00:00Z"})
    (specs / "releases" / "_archive" / "releases_histo.jsonl").write_text(
        json.dumps(
            {
                "id": "0.5.2",
                "ts": "2026-01-02T00:00:00Z",
                "disposition": "delivered",
                "release": "0.5.2",
                "reason": None,
                "summary": "shipped",
                "entry": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = _run(script, "fold", "0.5.2", "--into", "0.4.5", "--specs", str(specs))
    assert result.returncode == 0, result.stderr
    assert not (specs / "releases" / "_archive" / "0.5.2").exists()
    assert (specs / "releases" / "_archive" / "0.4.5" / "rc-1" / "SPEC.md").is_file()
    record = json.loads(
        (specs / "releases" / "_archive" / "releases_histo.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    assert record["release"] == "0.4.5"
    assert "0.4.5" in record["summary"]


def test_fold_refuses_a_target_at_or_above_the_live_release(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.6.0")
    _archived(specs, "0.5.2")
    before = _tree_hash(specs)
    result = _run(script, "fold", "0.5.2", "--into", "0.6.0", "--specs", str(specs))
    assert result.returncode == 1
    assert _tree_hash(specs) == before


def test_fold_refuses_an_unknown_archived_release(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.6.0")
    assert _run(script, "fold", "0.5.2", "--into", "0.4.5", "--specs", str(specs)).returncode == 1


# ── check ─────────────────────────────────────────────────────────────────────


def test_check_is_clean_on_a_valid_tree(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    result = _run(script, "check", "--specs", str(specs))
    assert result.returncode == 0, result.stdout


def test_check_reports_a_live_directory_carrying_the_archived_phase(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="ARCHIVED")
    result = _run(script, "check", "--specs", str(specs))
    assert result.returncode == 1
    assert "LEDGER-RELEASE-SCHEMA error" in result.stdout


def test_check_reports_a_schema_violation_and_emits_json(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    release_dir = _release(specs, "0.5.0")
    release_dir.joinpath("_RELEASE.json").write_text(
        json.dumps({"schema": "release-state-v1", "release": "0.5.0"}) + "\n", encoding="utf-8"
    )
    result = _run(script, "check", "--specs", str(specs), "--json")
    assert result.returncode == 1
    findings = json.loads(result.stdout)
    assert findings and all(f["code"] == "LEDGER-RELEASE-SCHEMA" for f in findings)


def test_check_reports_a_histo_record_that_is_not_valid_json(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    (specs / "releases" / "_archive" / "releases_histo.jsonl").write_text("{\n", encoding="utf-8")
    assert _run(script, "check", "--specs", str(specs)).returncode == 1


def test_check_reports_out_of_order_log_timestamps(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(
        specs,
        "0.5.0",
        phase="IMPLEMENTATION",
        log=[
            {"ts": "2026-02-01T00:00:00Z", "agent": "a", "kind": "note", "text": "later"},
            {"ts": "2026-01-01T00:00:00Z", "agent": "a", "kind": "note", "text": "earlier"},
        ],
    )
    result = _run(script, "check", "--specs", str(specs))
    assert result.returncode == 1
    assert "precedes" in result.stdout


def test_check_finds_the_specs_tree_by_walking_up_from_cwd(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    (tmp_path / ".git").mkdir()
    _release(specs, "0.5.0", phase="IMPLEMENTATION")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert _run(script, "check", cwd=nested).returncode == 0


# ── every refusal carries exactly one runnable `fix:` ─────────────────────────


@pytest.mark.parametrize(
    ("name", "argv"),
    [
        ("bad-sha", ("phase", "IMPLEMENTATION", "--sha", "nope")),
        ("out-of-order", ("phase", "CLOSURE", "--sha", "abc1234")),
        ("unknown-phase", ("phase", "DEFINITION", "--sha", "abc1234")),
        ("not-live", ("archive", "0.4.9", "--shipped", "abc1234", "--pr", "1", "--next", "0.6.0")),
        ("bad-pr", ("archive", "0.5.0", "--shipped", "abc1234", "--pr", "0", "--next", "0.6.0")),
        ("bad-next", ("archive", "0.5.0", "--shipped", "abc1234", "--pr", "1", "--next", "v1")),
        ("second-live", ("new", "0.6.0")),
        ("fold-unknown", ("fold", "0.4.1", "--into", "0.4.0")),
        ("not-closure", ("rc-archive",)),
    ],
)
def test_every_refusal_carries_exactly_one_runnable_fix(
    script: Path, tmp_path: Path, name: str, argv: tuple[str, ...]
) -> None:
    """The block contract the retired CLI verbs used to carry (`test_every_block_carries
    _a_fix.py`): one `fix:` line, naming one executable command, on every refusal."""
    specs = _specs(tmp_path)
    _release(specs, "0.5.0", phase="DEFINITION")
    result = _run(script, *argv, "--specs", str(specs))
    assert result.returncode == 1, result.stdout
    fixes = [line for line in result.stderr.splitlines() if line.startswith("fix: ")]
    assert len(fixes) == 1, f"{name}: {result.stderr}"
    assert fixes[0].removeprefix("fix: ").strip(), name
