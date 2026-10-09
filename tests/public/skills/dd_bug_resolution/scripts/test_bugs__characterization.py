"""Characterization net for the six public ``bugs.py`` seams owned by CP3."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.harness_env import suite_env
from tests.helpers.skill_scripts import stage_skill_scripts

pytestmark = [
    pytest.mark.medium,
    pytest.mark.slow(reason="runs six public-script subprocesses over a real Git fixture"),
]

_OPENED = "2026-10-09T10:00:00Z"
_CLOSED = "2026-10-09T12:00:00Z"
_FIX_SHA = "a" * 40


def _open(bug_id: str) -> dict[str, object]:
    return {
        "id": bug_id,
        "ts": _OPENED,
        "reported_by": "fixture",
        "title": f"Title {bug_id}",
        "severity": "LOW",
        "surface": "src",
        "component": "writer",
        "context": "characterization",
        "symptom": f"Symptom {bug_id}",
        "repro": "python -m fixture",
        "expected": "Expected behavior",
        "status": "open",
        "cause": None,
        "caused_by": None,
        "closed_at": None,
    }


def _bytes(*records: dict[str, object]) -> bytes:
    return "".join(
        json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" for record in records
    ).encode()


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.invalid",
            *args,
        ],
        cwd=repo,
        env=suite_env(os.environ, repo),
        capture_output=True,
        text=True,
        check=True,
    )


def _run(
    script: Path, repo: Path, *args: str, fixed_clock: bool = False
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(script), *args]
    if fixed_clock:
        bootstrap = (
            "import sys; from pathlib import Path; "
            "sys.path.insert(0, str(Path(sys.argv.pop(1)))); "
            "import bugs; "
            f"bugs.tr.now_iso = lambda: {_CLOSED!r}; "
            "raise SystemExit(bugs.main(sys.argv[1:]))"
        )
        command = [sys.executable, "-c", bootstrap, str(script.parent), *args]
    return subprocess.run(
        command,
        cwd=repo,
        env=suite_env(os.environ, repo),
        capture_output=True,
        text=True,
        check=False,
    )


def test_all_public_bug_verbs_pin_output_and_each_ledger_write(tmp_path: Path) -> None:
    stage_skill_scripts(
        "dd-release-implementation", tmp_path / "skills/dd-release-implementation/scripts"
    )
    script = (
        stage_skill_scripts("dd-bug-resolution", tmp_path / "skills/dd-bug-resolution/scripts")
        / "bugs.py"
    )
    repo = tmp_path / "repo"
    specs = repo / "specs"
    ledger = specs / "bugs/BUGS.jsonl"
    ledger.parent.mkdir(parents=True)
    source = repo / "src/module.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")
    replacement = _open("replacement")
    rejected = _open("to-reject")
    resolved = _open("to-resolve")
    superseded = _open("to-supersede")
    ledger.write_bytes(_bytes(replacement, rejected, resolved, superseded))
    repo.mkdir(exist_ok=True)
    _git(repo.parent, "init", "-q", str(repo))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "fixture")

    appended = {
        **_open("appended"),
        "reported_by": "characterizer",
        "title": "Appended bug",
        "severity": "MEDIUM",
        "component": "bugs.py",
        "symptom": "Append symptom",
        "repro": "python -m append",
        "expected": "Append succeeds",
        "correlates": [],
    }
    append = _run(
        script,
        repo,
        "append",
        "--bug-id",
        "appended",
        "--reported-by",
        "characterizer",
        "--ts",
        _OPENED,
        "--title",
        "Appended bug",
        "--severity",
        "MEDIUM",
        "--surface",
        "src",
        "--component",
        "bugs.py",
        "--context",
        "characterization",
        "--symptom",
        "Append symptom",
        "--repro",
        "python -m append",
        "--expected",
        "Append succeeds",
        "--correlates",
        "none",
        "--specs",
        str(specs),
    )
    after_append = _bytes(replacement, rejected, resolved, superseded, appended)
    assert (append.returncode, append.stdout, append.stderr) == (
        0,
        "correlation candidates on 'src': replacement, to-reject, to-resolve, "
        f"to-supersede\n[ok] registered appended -> {specs}\n",
        "",
    )
    assert ledger.read_bytes() == after_append

    status = _run(script, repo, "status", "--specs", str(specs))
    assert (status.returncode, status.stdout, status.stderr) == (
        0,
        "appended\topen\tMEDIUM\n"
        "replacement\topen\tLOW\n"
        "to-reject\topen\tLOW\n"
        "to-resolve\topen\tLOW\n"
        "to-supersede\topen\tLOW\n"
        "[ok] 5 open bug(s).\n",
        "",
    )
    assert ledger.read_bytes() == after_append

    resolved = {
        **resolved,
        "cause": "Root cause",
        "caused_by": "none",
        "closed_at": _CLOSED,
        "fix_sha": _FIX_SHA,
        "solution": "Fixed once",
        "status": "resolved",
    }
    resolve = _run(
        script,
        repo,
        "resolve",
        "to-resolve",
        "--cause",
        "Root cause",
        "--caused-by",
        "none",
        "--solution",
        "Fixed once",
        "--fix-sha",
        _FIX_SHA,
        "--specs",
        str(specs),
        fixed_clock=True,
    )
    assert (resolve.returncode, resolve.stdout, resolve.stderr) == (
        0,
        "[ok] resolved to-resolve\n",
        "",
    )
    assert ledger.read_bytes() == _bytes(replacement, rejected, resolved, superseded, appended)

    superseded = {
        **superseded,
        "closed_at": _CLOSED,
        "status": "superseded",
        "superseded_by": "replacement",
    }
    supersede = _run(
        script,
        repo,
        "supersede",
        "to-supersede",
        "--by",
        "replacement",
        "--specs",
        str(specs),
        fixed_clock=True,
    )
    assert (supersede.returncode, supersede.stdout, supersede.stderr) == (
        0,
        "[ok] superseded to-supersede\n",
        "",
    )
    assert ledger.read_bytes() == _bytes(replacement, rejected, resolved, superseded, appended)

    rejected = {
        **rejected,
        "cause": "Not a defect",
        "closed_at": _CLOSED,
        "status": "rejected",
    }
    reject = _run(
        script,
        repo,
        "reject",
        "to-reject",
        "--reason",
        "Not a defect",
        "--specs",
        str(specs),
        fixed_clock=True,
    )
    assert (reject.returncode, reject.stdout, reject.stderr) == (
        0,
        "[ok] rejected to-reject\n",
        "",
    )
    assert ledger.read_bytes() == _bytes(replacement, rejected, resolved, superseded, appended)

    archive = _run(
        script,
        repo,
        "archive",
        "to-reject",
        "to-resolve",
        "to-supersede",
        "--specs",
        str(specs),
    )
    assert (archive.returncode, archive.stdout, archive.stderr) == (
        0,
        "[ok] archived 3 record(s), 2 kept.\n",
        "",
    )
    assert ledger.read_bytes() == _bytes(replacement, appended)
    assert (specs / "bugs/_archive/bugs_histo.jsonl").read_bytes() == _bytes(
        rejected, resolved, superseded
    )
