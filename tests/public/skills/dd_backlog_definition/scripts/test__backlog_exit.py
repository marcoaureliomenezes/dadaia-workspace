"""A picked backlog item stays ``picked`` in ``active[]`` and exits once, at closure.

No source or test file names the ``CONSUMED`` token, its ledger module, its record class
or its consumed histo file.

Size: MEDIUM (reads the shipped source tree and runs `git ls-files`; no fixture, no network).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import dadaia_workspace
from dadaia_workspace.core.skill_owner import load_owner
from tests.fixtures.real_git import git
from tests.helpers.oslib import command, read_text, run, write_text
from tests.helpers.suite_files import tracked

_PKG = Path(dadaia_workspace.__file__).resolve().parent

#: Every name the deleted pick-time exit lane went by.
_DEAD_NAMES = (
    "CONSUMED",
    "ConsumedBacklogHistoRecord",
    "consumed_backlog_histo",
    "read_consumed",
    "SPEC-DOC-031",
)
_DEAD_RE = re.compile("|".join(re.escape(name) for name in _DEAD_NAMES))

#: Law and skill text under ``public/`` is outside this contract; it covers code and tests.
_SCOPES = ("core", "features", "cli", "hooks")


def _offenders(root: Path = _PKG.parent) -> list[str]:
    hits: list[str] = []
    files = [
        *(p for scope in _SCOPES for p in (root / "dadaia_workspace" / scope).rglob("*.py")),
        *tracked(root, "tests/*.py"),
    ]
    for path in files:
        if "__pycache__" in path.parts or path.name == Path(__file__).name:
            continue
        for lineno, line in enumerate(read_text(path).splitlines(), 1):
            if _DEAD_RE.search(line):
                hits.append(f"{path.relative_to(root).as_posix()}:{lineno}: {line.strip()}")
    return hits


def test_no_source_or_test_names_the_consumed_lane() -> None:
    offenders = _offenders()
    assert not offenders, (
        "the pick-time CONSUMED exit lane is deleted (0.4.7 FR7, T-047-05): a picked "
        "item stays 'picked' in active[] and exits once, at closure. Still named:\n"
        + "\n".join(offenders)
    )


def test_the_consumed_histo_file_and_ledger_module_are_gone() -> None:
    assert not (_PKG / "features" / "backlog" / "ledger.py").exists(), (
        "features/backlog/ledger.py read the consumed lane and had no producer — deleted"
    )
    specs_dir = _PKG.parent / "specs"
    stale = specs_dir / "backlog" / "_archive" / "consumed_backlog_histo.jsonl"
    assert not stale.exists(), f"{stale} holds stalled provisional records — deleted"


def test_an_untracked_scratch_file_under_tests_is_not_judged(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    (tmp_path / "tests/tmp").mkdir(parents=True)
    write_text(tmp_path / "tests" / "test_kept.py", "X = 'CONSUMED'\n")
    git(tmp_path, "add", "tests/test_kept.py")
    write_text(tmp_path / "tests" / "test_gone.py", "X = 'CONSUMED'\n")
    assert _offenders(tmp_path) == ["tests/test_kept.py:1: X = 'CONSUMED'"]


def test_an_unspawnable_release_script_refuses_with_its_one_fix_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(argv[0])

    owner = load_owner("dd-backlog-definition", "_backlog_exit")
    monkeypatch.setattr(owner, "run", missing)
    spec = tmp_path / "SPEC.md"
    with pytest.raises(owner.Refusal) as refused:
        owner._origin_ids(spec)
    assert refused.value.fix == command(sys.executable, str(owner._RELEASE), "origin", str(spec))


def test_to_bug_reads_the_bug_ledger_through_the_bug_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = load_owner("dd-backlog-definition", "_backlog_exit")
    store = load_owner("dd-bug-resolution", "_bugs_store")
    monkeypatch.setattr(store, "read_records", lambda _path: [{"id": "b-1"}])
    owner._bug(tmp_path, "slug", "to-bug", "b-1")
    with pytest.raises(owner.Refusal, match="names no record"):
        owner._bug(tmp_path, "slug", "to-bug", "b-2")


_BACKLOG = (
    Path(dadaia_workspace.__file__).resolve().parent
    / "public"
    / "skills"
    / "dd-backlog-definition"
    / "scripts"
    / "backlog.py"
)


def test_a_malformed_bug_ledger_refuses_naming_its_line_with_one_fix_line(tmp_path: Path) -> None:
    """A `to-bug` exit over a BUGS.jsonl it cannot read in full refuses naming the line and
    one `sed` fix line, never with a traceback."""
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    write_text(
        specs / "backlog" / "BACKLOG.json",
        json.dumps({"schema": "backlog-v1", "active": [{"id": "an-idea"}]}) + "\n",
    )
    (specs / "bugs").mkdir()
    ledger = specs / "bugs" / "BUGS.jsonl"
    write_text(ledger, json.dumps({"id": "a-bug"}) + "\nnot json\n")
    done = run(
        [sys.executable, str(_BACKLOG), "exit", "an-idea", "--specs", str(specs),
         "--disposition", "to-bug", "--reason", "a-bug"],
        check=False,
    )  # fmt: skip
    assert done.returncode == 1, done.stdout + done.stderr
    assert "Traceback" not in done.stderr
    assert "BUGS.jsonl:2" in done.stderr
    fixes = [ln for ln in (done.stdout + done.stderr).splitlines() if ln.startswith("fix:")]
    assert fixes == [f"fix: {command('sed', '-n', '2p', str(ledger))}"]
