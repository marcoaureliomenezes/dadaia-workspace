"""`release.py check` is the ONE
release validator; the doctor delegates to it. Size: SMALL (script subprocess
over tmp trees; the repo's own tree once).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.cli_line import shell_line
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_common import resolve_active_release
from dadaia_workspace.features.specs.doctor_release import ReleaseValidator
from dadaia_workspace.features.specs.specs_tree import SpecsTree
from tests.helpers.oslib import run as os_run
from tests.helpers.oslib import write_text
from tests.helpers.release_state import PLAN

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / "dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py"
_IMPLEMENTED = "2026-09-22T10:00:00Z"


def _run(*argv: str) -> subprocess.CompletedProcess[str]:
    return os_run([sys.executable, str(_SCRIPT), *argv], check=False)  # fmt: skip


def _check(specs: Path) -> list[dict[str, Any]]:
    return list(json.loads(_run("check", "--specs", str(specs), "--json").stdout))


def _entry(ts: str, **over: object) -> dict[str, object]:
    return {"ts": ts, "agent": "release.py memory", "kind": "memory", "text": "m",
            "since": "0000001", "until": "0000003", "reviewed": ["a"], "changed": [], **over}  # fmt: skip


def _specs(
    tmp_path: Path, phase: str, log: list[Any], rid: str = "0.5.0", trio: bool = True
) -> Path:
    specs = tmp_path / "specs"
    release_dir = specs / "releases" / rid
    (release_dir / "rc-1").mkdir(parents=True, exist_ok=True)
    for name in ("SPEC.md", "PLAN.md", "TASKS.md") if trio else ():
        write_text(
            release_dir / "rc-1" / name,
            f"# x\n\n**Status:** Approved\n\n{PLAN if name == 'PLAN.md' else ''}",
        )
    write_text(release_dir / "_RELEASE.json", json.dumps({
        "schema": "release-state-v1", "release": rid, "phase": phase,
        "defined": {"sha": "0000001", "ts": "2026-09-20T10:00:00Z"},
        "implemented": {"sha": "0000002", "ts": _IMPLEMENTED}, "shipped": None, "log": log,
    }))  # fmt: skip
    return specs


_FIRST = _entry("2026-09-22T12:00:00Z")


@pytest.mark.parametrize(
    ("phase", "log", "expected"),
    [
        ("CLOSURE", [], "reconciled no memory"),
        ("CLOSURE", [_entry("2026-09-21T10:00:00Z")], "reconciled no memory"),
        ("CLOSURE", [_FIRST, _entry("2026-09-22T13:00:00Z", since="0000003")], None),
        ("CLOSURE", [_entry(_IMPLEMENTED)], None),
        ("DEFINITION", [], None),
        ("IMPLEMENTATION", [], None),
    ],
)
def test_closure_memory_record_is_judged_by_the_script(
    tmp_path: Path, phase: str, log: list[Any], expected: str | None
) -> None:
    """A memory entry stamped at or after implemented.ts exists; its fix names the real
    script and --specs, and no placeholder."""
    specs = _specs(tmp_path, phase, log)
    record = [f for f in _check(specs) if "`kind: memory`" in f["message"]]
    run = (sys.executable, str(_SCRIPT))
    where = ("--specs", str(specs.resolve()))
    fix = (
        f"Agent action: run `{shell_line(*run, 'drift', *where)}`, judge its worklist, then run "
        f"`{shell_line(*run, 'memory', *where)}` with the atom slugs the memory pass reviewed as "
        "--reviewed and changed as --changed"
    )
    if expected is None:
        assert record == []
    else:
        assert len(record) == 1 and expected in record[0]["message"], record
        assert record[0]["fix"] == fix, record


def test_a_live_release_in_implementation_missing_its_trio_is_one_finding(tmp_path: Path) -> None:
    findings = _check(_specs(tmp_path, "IMPLEMENTATION", [], trio=False))
    assert [f["code"] for f in findings] == ["LEDGER-RELEASE-SCHEMA"]


def test_release_doctor_judges_status_only_on_the_two_candidate_documents(
    tmp_path: Path,
) -> None:
    specs = _specs(tmp_path, "IMPLEMENTATION", [])
    candidate = specs / "releases/0.5.0/rc-1"
    write_text(
        candidate.joinpath("SPEC.md"),
        "# S\n\n**Status:** Approved\n**Origin:** customer-conversation\n\n"
        "## Bug window review\n\n## User-added section\n",
    )
    write_text(
        candidate.joinpath("TASKS.md"),
        "# historical task index\n\n**Status:** Not a candidate status\n",
    )

    validator = ReleaseValidator(specs)

    assert validator.check_active_release_artifacts() == []


def test_the_repos_own_release_tree_checks_clean() -> None:
    assert _run("check", "--specs", str(_REPO / "specs")).returncode == 0


def test_a_legacy_next_dir_is_not_live_and_new_refuses(tmp_path: Path) -> None:
    """`next/` is not live; `new` refuses while
    `check` is red, and doctor and script name the same non-canon `next`."""
    specs = _specs(tmp_path, "DEFINITION", [], rid="next")
    result = _run("new", "0.6.0", "--specs", str(specs))
    assert result.returncode == 1 and "next" in result.stderr
    assert not (specs / "releases" / "0.6.0").exists()
    [fix] = [f["fix"] for f in _check(specs) if f["path"] == "releases/next"]  # tree8-and-027
    move = f"{(specs / 'releases/next').resolve()} into its canon shape (a bare M.m.p id)"
    assert fix == f"Agent action: move {move}, or out of specs/"
    assert resolve_active_release(specs) == (None, None)
    assert any("/next/" in i.message for i in SpecsDoctor(specs).check() if i.code == "TREE-8")


def test_doctor_names_the_candidate_release_py_names(tmp_path: Path) -> None:
    """A milestone makes the first candidate the live one; the empty folder after it is not, for doctor or script."""
    milestone = {"ts": "2026-09-21T10:00:00Z", "agent": "release.py", "kind": "milestone",
                 "candidate": "rc-1", "milestone": "implemented", "sha": "0000002", "text": "rc-1 implemented."}  # fmt: skip
    specs = _specs(tmp_path, "IMPLEMENTATION", [milestone])
    (specs / "releases/0.5.0/rc-2").mkdir()
    release_py = load_owner("dd-release-implementation", "_release_store").live_release(specs)
    assert release_py.candidate == specs / "releases/0.5.0/rc-1"
    assert SpecsTree(specs).active_release.candidate == release_py.candidate


_GRAMMAR = load_owner("dd-bug-resolution", "_grammar")
_STATUS_ROWS = [
    ("# SPEC\n\n**Status:**   Approved\n", "Approved"),
    ("# SPEC\n\n**Status:** Approved (pending)\n", "Approved (pending)"),
    ("# TASKS\n\n**Status:** approved\n" + "- t\n" * 170, "approved"),
    ("# PLAN\n" + "text\n" * 36 + "**Status:** Approved\n", "Approved"),
    ("# SPEC\n\n**Status:** Draft\n\n**Status:** Approved\n", "Draft"),
    ("# SPEC\n\n- **Status:** Approved\n", None),
    ("# SPEC\n\n> **Status:** Approved\n", None),
    ("# SPEC\n\nthe line reads **Status:** Approved here\n", None),
    ("# SPEC\n\nno status here\n", None),
]


def test_the_status_vocabulary_is_the_canonical_triple_in_the_kernel() -> None:
    assert {"Draft", "In review", "Approved"} == _GRAMMAR.CANONICAL_STATUS
    assert (_GRAMMAR.DRAFT, _GRAMMAR.IN_REVIEW, _GRAMMAR.APPROVED) == (
        "Draft",
        "In review",
        "Approved",
    )


@pytest.mark.parametrize(("text", "expected"), _STATUS_ROWS)
def test_both_status_readers_return_the_same_token(text: str, expected: str | None) -> None:
    """The first anchored line counts anywhere; a bullet, a blockquote and a mid-line quote
    never count; absent is None; the kernel and the release script agree."""
    script = load_owner("dd-release-implementation", "_release_schema").extract_status
    assert _GRAMMAR.extract_status(text) == script(text) == expected
