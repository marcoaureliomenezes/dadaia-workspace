"""Intent: CONTRACT — sa-release-json-validated-three-times: `release.py check` is the ONE
release validator (ADR 0077); the doctor delegates to it. Size: SMALL (script subprocess
over tmp trees; the repo's own tree once).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_common import resolve_active_release

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[4]
_SCRIPT = _REPO / "dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py"
_IMPLEMENTED = "2026-09-22T10:00:00Z"


def _run(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(_SCRIPT), *argv], capture_output=True,
                          text=True, check=False)  # fmt: skip


def _check(specs: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = json.loads(
        _run("check", "--specs", str(specs), "--json").stdout
    )
    return findings


def _entry(ts: str, **over: object) -> dict[str, object]:
    return {"ts": ts, "agent": "release.py memory", "kind": "memory", "text": "m",
            "since": "0000001", "until": "0000003", "reviewed": ["a"], "changed": [], **over}  # fmt: skip


def _specs(
    tmp_path: Path, phase: str, log: list[Any], rid: str = "0.5.0", trio: bool = True
) -> Path:
    specs = tmp_path / "specs"
    release_dir = specs / "releases" / rid
    release_dir.mkdir(parents=True, exist_ok=True)
    for name in ("SPEC.md", "PLAN.md", "TASKS.md") if trio else ():
        (release_dir / name).write_text("# x\n\n**Status:** Approved\n", encoding="utf-8")
    (release_dir / "_RELEASE.json").write_text(json.dumps({
        "schema": "release-state-v1", "release": rid, "phase": phase,
        "defined": {"sha": "0000001", "ts": "2026-09-20T10:00:00Z"},
        "implemented": {"sha": "0000002", "ts": _IMPLEMENTED}, "shipped": None, "log": log,
    }), encoding="utf-8")  # fmt: skip
    return specs


_PROSE = {"ts": "2026-09-22T11:00:00Z", "agent": "pm", "kind": "memory", "text": "done"}
_FIRST = _entry("2026-09-22T12:00:00Z")


@pytest.mark.parametrize(
    ("phase", "log", "expected"),
    [
        ("CLOSURE", [], "reconciled no memory"),
        ("CLOSURE", [_PROSE], "lacks since"),
        ("CLOSURE", [_entry("2026-09-21T10:00:00Z")], "reconciled no memory"),
        ("CLOSURE", [_FIRST, {**_PROSE, "ts": "2026-09-22T13:00:00Z"}], "lacks since"),
        ("CLOSURE", [_entry("2026-09-22T12:00:00Z", since="0000002")], "'0000001'"),
        ("CLOSURE", [_FIRST, _entry("2026-09-22T13:00:00Z", until="0000004")], "'0000003'"),
        ("CLOSURE", [_FIRST, _entry("2026-09-22T13:00:00Z", since="0000003")], None),
        ("CLOSURE", [_entry(_IMPLEMENTED)], None),
        ("DEFINITION", [], None),
        ("IMPLEMENTATION", [], None),
    ],
)
def test_closure_memory_record_is_judged_by_the_script(
    tmp_path: Path, phase: str, log: list[Any], expected: str | None
) -> None:
    """The latest memory entry stamped at or after implemented.ts names its window and
    opens at the ledger-derived start; the record rule moved here from the doctor."""
    messages = [f["message"] for f in _check(_specs(tmp_path, phase, log))]
    record = [m for m in messages if "`kind: memory`" in m]
    if expected is None:
        assert record == [], messages
    else:
        assert len(record) == 1 and expected in record[0], messages


def test_a_live_release_in_implementation_missing_its_trio_is_one_finding(tmp_path: Path) -> None:
    findings = _check(_specs(tmp_path, "IMPLEMENTATION", [], trio=False))
    assert [f["code"] for f in findings] == ["LEDGER-RELEASE-SCHEMA"]
    assert "SPEC.md, PLAN.md, TASKS.md" in findings[0]["message"]


def test_the_repos_own_release_tree_checks_clean() -> None:
    assert _run("check", "--specs", str(_REPO / "specs")).returncode == 0


def test_a_legacy_next_dir_is_not_live_and_new_refuses(tmp_path: Path) -> None:
    """sa-release-json-validated-three-times#B3: `next/` is not live; `new` refuses while
    `check` is red (ADR 0077), and doctor and script name the same non-canon `next`."""
    specs = _specs(tmp_path, "DEFINITION", [], rid="next")
    result = _run("new", "0.6.0", "--specs", str(specs))
    assert result.returncode == 1 and "next" in result.stderr
    assert not (specs / "releases" / "0.6.0").exists()
    assert any(f["path"] == "releases/next" for f in _check(specs))
    assert resolve_active_release(specs) == (None, None)
    assert any(
        i.code == "TREE-8" and "releases/next" in str(i.path) for i in SpecsDoctor(specs).check()
    )
