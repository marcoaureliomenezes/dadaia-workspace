"""Intent: CONTRACT — dd-bug-resolution/scripts/bugs.py owns BUGS.jsonl validation
(0.4.7 c7 T-047-63: the ledger verbs move into stdlib skill scripts). Size: SMALL.

The script reads its schema from ``scripts/schemas/`` BESIDE itself — a copy `public
stage` makes. Every test here therefore stages the pair into a tmp dir exactly as
stage does, which is also what proves the copy is the only path the script has.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_SOURCE = _PUBLIC / "skills" / "dd-bug-resolution" / "scripts" / "bugs.py"
_SCHEMA = _PUBLIC / "schemas" / "bugs" / "bug-record-v1.schema.json"

_OPEN_RECORD: dict[str, object] = {
    "id": "a-bug",
    "ts": "2026-09-20T10:00:00Z",
    "reported_by": "software-engineer",
    "title": "t",
    "severity": "LOW",
    "surface": "cli",
    "component": "c",
    "context": "ctx",
    "symptom": "s",
    "repro": "r",
    "expected": "e",
    "status": "open",
    "cause": None,
    "caused_by": None,
    "resolved_release": None,
    "audited": None,
    "closed_at": None,
}


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: bugs.py with its schema copy beside it."""
    staged = tmp_path / "staged" / "scripts"
    (staged / "schemas").mkdir(parents=True)
    shutil.copy2(_SOURCE, staged / "bugs.py")
    shutil.copy2(_SCHEMA, staged / "schemas" / _SCHEMA.name)
    return staged / "bugs.py"


def _ledger(root: Path, *records: dict[str, object]) -> Path:
    specs = root / "specs"
    (specs / "bugs").mkdir(parents=True, exist_ok=True)
    (specs / "bugs" / "BUGS.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )
    return specs


def _run(script: Path, *argv: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
    )


def test_clean_ledger_exits_zero(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.strip() == "" or "error" not in done.stdout


def test_record_missing_an_immutable_core_field_is_one_error_line(
    script: Path, tmp_path: Path
) -> None:
    broken = {k: v for k, v in _OPEN_RECORD.items() if k != "symptom"}
    specs = _ledger(tmp_path, broken)
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 1
    lines = [ln for ln in done.stdout.splitlines() if ln.strip()]
    assert len(lines) == 1, lines
    assert lines[0].startswith("LEDGER-BUGS-SCHEMA error ")
    assert "symptom" in lines[0] and "bugs/BUGS.jsonl:1" in lines[0]


@pytest.mark.parametrize(
    ("mutation", "needle"),
    [
        ({"status": "resolved"}, "closed_at"),
        ({"closed_at": "2026-09-20"}, "closed_at"),
        ({"severity": "URGENT"}, "severity"),
        ({"ts": "yesterday"}, "ts"),
        ({"root_cause": "retired key"}, "root_cause"),
    ],
)
def test_invariant_violations_are_reported(
    script: Path, tmp_path: Path, mutation: dict[str, object], needle: str
) -> None:
    specs = _ledger(tmp_path, {**_OPEN_RECORD, **mutation})
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 1
    assert needle in done.stdout


def test_closed_at_before_ts_is_refused(script: Path, tmp_path: Path) -> None:
    record = {
        **_OPEN_RECORD,
        "status": "resolved",
        "closed_at": "2020-01-01T00:00:00Z",
        "solution": "s",
    }
    done = _run(script, "check", "--specs", str(_ledger(tmp_path, record)))
    assert done.returncode == 1
    assert "precedes" in done.stdout


def test_duplicate_ids_are_refused(script: Path, tmp_path: Path) -> None:
    done = _run(script, "check", "--specs", str(_ledger(tmp_path, _OPEN_RECORD, _OPEN_RECORD)))
    assert done.returncode == 1
    assert "duplicate" in done.stdout


def test_json_output_carries_one_object_per_finding(script: Path, tmp_path: Path) -> None:
    broken = {k: v for k, v in _OPEN_RECORD.items() if k != "symptom"}
    done = _run(script, "check", "--specs", str(_ledger(tmp_path, broken)), "--json")
    assert done.returncode == 1
    payload = json.loads(done.stdout)
    assert len(payload) == 1
    assert payload[0]["code"] == "LEDGER-BUGS-SCHEMA"
    assert payload[0]["verdict"] == "error"
    assert payload[0]["line"] == 1


def test_missing_specs_above_cwd_is_refused_with_one_fix_line(script: Path, tmp_path: Path) -> None:
    """No `specs/` at or above cwd whose parent holds `.git` — the default resolution
    refuses rather than guessing, and says exactly how to proceed."""
    lonely = tmp_path / "nowhere"
    lonely.mkdir()
    done = _run(script, "check", cwd=lonely)
    assert done.returncode == 1
    fixes = [ln for ln in (done.stdout + done.stderr).splitlines() if ln.startswith("fix:")]
    assert len(fixes) == 1
    assert "--specs" in fixes[0]


def test_specs_default_resolves_the_nearest_git_rooted_specs_tree(
    script: Path, tmp_path: Path
) -> None:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    _ledger(root, _OPEN_RECORD)
    deep = root / "a" / "b"
    deep.mkdir(parents=True)
    assert _run(script, "check", cwd=deep).returncode == 0


def test_absent_ledger_is_not_a_finding(script: Path, tmp_path: Path) -> None:
    """A young specs tree has no bugs file yet — same posture as the doctor's."""
    specs = tmp_path / "specs"
    specs.mkdir()
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_script_is_executable_and_has_a_shebang() -> None:
    assert os.access(_SOURCE, os.X_OK)
    assert _SOURCE.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n")
