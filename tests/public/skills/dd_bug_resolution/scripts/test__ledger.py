"""A ledger write verb that exits non-zero on an injected invalid document changes no file
of its pair (hash before = after). Size: SMALL — each ledger script as a child process
over a tmp specs tree.

Every case injects a schema-invalid (still JSON) document, so the refusal can only come
from the pair check the verb runs over its candidate bytes before writing.
"""

from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.helpers.skill_scripts import stage_skill_scripts

_PUBLIC = Path(__file__).resolve().parents[5] / "dadaia_workspace" / "public"
_HISTO_SCHEMA = json.loads(
    (
        _PUBLIC / "skills/dd-backlog-definition/scripts/schemas/histo-record-v1.schema.json"
    ).read_text()
)
TERMINAL_DISPOSITIONS = tuple(_HISTO_SCHEMA["properties"]["disposition"]["enum"])
_HISTO = (
    '{"disposition": "rejected", "entry": {}, "id": "old", "reason": "r", "ts": "2026-01-01"}\n'
)
_STATE = {"schema": "release-state-v1", "release": "9.9.9", "phase": "SHIPPED"}

#: (script, {specs-relative file: text}, argv after the verb's script path)
_CASES: dict[str, tuple[str, dict[str, str], list[str]]] = {
    "bugs.py update": (
        "dd-bug-resolution/scripts/bugs.py",
        {"bugs/BUGS.jsonl": '{"id": "a-bug", "status": "open"}\n',
         "bugs/_archive/bugs_histo.jsonl": ""},
        ["update", "a-bug", "--set", "caused_by=none"],
    ),
    "backlog.py new": (
        "dd-backlog-definition/scripts/backlog.py",
        {"backlog/BACKLOG.json": '{"schema": "backlog-v1", "active": [{"id": "broken", "status": "Idea"}]}\n',
         "backlog/_archive/backlog_histo.jsonl": _HISTO},
        ["new", "zz"],
    ),
    "audit.py disposition": (
        "dd-audit-project/scripts/audit.py",
        {"audits/a1/FINDINGS.jsonl": '{"id": "f1", "disposition": "resolved"}\n',
         "audits/_archive/audits_histo.jsonl": ""},
        ["disposition", "a1", "f1", "--disposition", "rejected", "--reason", "r"],
    ),
    "audit.py close": (
        "dd-audit-project/scripts/audit.py",
        {"audits/a1/FINDINGS.jsonl": '{"id": "f1", "disposition": "resolved"}\n',
         "audits/_archive/audits_histo.jsonl": ""},
        ["close", "a1", "--sha", "abc1234"],
    ),
    "release.py phase": (
        "dd-release-implementation/scripts/release.py",
        {"releases/9.9.9/_RELEASE.json": json.dumps(_STATE) + "\n",
         "releases/_archive/releases_histo.jsonl": ""},
        ["phase", "CLOSURE", "--sha", "abc1234"],
    ),
}  # fmt: skip


def _stage(root: Path) -> Path:
    """The four skills' scripts with their schema copies beside them, as `public stage`."""
    skills = root / "skills"
    for skill in ("dd-bug-resolution", "dd-backlog-definition", "dd-audit-project",
                  "dd-release-implementation", "dd-spec-navigator"):  # fmt: skip
        stage_skill_scripts(skill, skills / skill / "scripts")
    return skills


def _hashes(specs: Path) -> dict[str, str]:
    return {
        p.relative_to(specs).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(specs.rglob("*"))
        if p.is_file()
    }


def _run(
    tmp_path: Path, script: str, files: dict[str, str], *argv: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, str], dict[str, str]]:
    """`script argv` over `files` seeded in a tmp specs tree: process, hashes before, after."""
    skills, specs = _stage(tmp_path), tmp_path / "specs"
    for rel, text in files.items():
        (specs / rel).parent.mkdir(parents=True, exist_ok=True)
        (specs / rel).write_text(text, encoding="utf-8")
    before = _hashes(specs)
    done = subprocess.run(
        [sys.executable, str(skills / script), *argv, "--specs", str(specs)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    return done, before, _hashes(specs)


@pytest.mark.parametrize("case", sorted(_CASES))
def test_a_write_verb_over_an_invalid_document_refuses_with_the_pair_intact(
    case: str, tmp_path: Path
) -> None:
    script, files, argv = _CASES[case]
    done, before, after = _run(tmp_path, script, files, *argv)
    assert done.returncode != 0, done.stdout
    assert after == before, done.stderr


_R = "releases"
#: (script, {specs-relative file: text}) — together, every finding branch of every `check`.
_BROKEN = [
    ("dd-bug-resolution/scripts/bugs.py", {"bugs/BUGS.jsonl": '{x\n{"id": "a"}\n',
                                           "bugs/_archive/bugs_histo.jsonl": '{x\n{"id": "h"}\n'}),
    ("dd-backlog-definition/scripts/backlog.py", {"backlog/BACKLOG.json": "{x",
                                                  "backlog/_archive/backlog_histo.jsonl": '{x\n{"id": "h"}\n'}),
    ("dd-backlog-definition/scripts/backlog.py", {"backlog/BACKLOG.json": '{"active": 1}'}),
    ("dd-backlog-definition/scripts/backlog.py", {"backlog/BACKLOG.json": json.dumps({
        "schema": "backlog-v1", "active": [{"id": "a", "status": "resolved"}] * 2})}),
    ("dd-audit-project/scripts/audit.py", {"audits/a1/FINDINGS.jsonl": '{x\n{"id": "f"}\n{"id": "f"}\n',
                                           "audits/a2/AUDIT.md": "# A\n",
                                           "audits/_archive/audits_histo.jsonl": '{x\n{"disposition": "open"}\n'}),
    ("dd-release-implementation/scripts/release.py", {f"{_R}/1.0.0/rc-1/SPEC.md": "",
                                                      f"{_R}/foo/_RELEASE.json": "{}",
                                                      f"{_R}/_archive/0.9.0/_RELEASE.json": "{x",
                                                      f"{_R}/_archive/0.8.0/_RELEASE.json": "{}",
                                                      f"{_R}/_archive/releases_histo.jsonl": '{x\n{"id": "h"}\n'}),
    ("dd-release-implementation/scripts/release.py", {f"{_R}/1.0.0/_RELEASE.json": "{x",
                                                      f"{_R}/2.0.0/_RELEASE.json": "{}"}),
    ("dd-spec-navigator/scripts/memory.py", {"memory/product/core/a.md": "no frontmatter\n"}),
    ("dd-spec-navigator/scripts/memory.py", {"memory/product/core/a.md": "---\ntitle: a\ntldr: t\n---\n"}),
]  # fmt: skip


@pytest.mark.parametrize(("script", "files"), _BROKEN)
def test_every_check_finding_carries_its_fix(
    tmp_path: Path, script: str, files: dict[str, str]
) -> None:
    """Every record each ledger script's `check --json` emits carries a non-empty fix."""
    done, _, _ = _run(tmp_path, script, files, "check", "--json")
    records = json.loads(done.stdout)
    assert done.returncode == 1 and records, done.stderr
    assert [r for r in records if not str(r.get("fix", "")).strip()] == [], records


_FINDING = {"id": "a1-F001", "pillar": "bugs", "severity": "HIGH", "refs": ["a:1"], "claim": "c",
            "evidence": "e", "disposition": "open", "release": None, "reason": None}  # fmt: skip
_BUG = {"id": "a", "ts": "2026-09-20T10:00:00Z", "reported_by": "x", "title": "t", "severity": "LOW",
        "surface": "cli", "component": "c", "context": "x", "symptom": "s", "repro": "r",
        "expected": "e", "status": "open", "cause": None, "caused_by": None, "closed_at": None}  # fmt: skip
_NOT_JSON = "line is not valid JSON: Expecting property name enclosed in double quotes"
#: consumer -> (script, one JSONL ledger of its own, its schema finding code)
_LEDGERS = {
    "bugs": ("dd-bug-resolution/scripts/bugs.py", "bugs/BUGS.jsonl", "LEDGER-BUGS-SCHEMA"),
    "backlog": ("dd-backlog-definition/scripts/backlog.py",
                "backlog/_archive/backlog_histo.jsonl", "LEDGER-BACKLOG-SCHEMA"),
    "audit": ("dd-audit-project/scripts/audit.py", "audits/a1/FINDINGS.jsonl", "LEDGER-FINDINGS-SCHEMA"),
    "release": ("dd-release-implementation/scripts/release.py",
                "releases/_archive/releases_histo.jsonl", "LEDGER-RELEASE-SCHEMA"),
}  # fmt: skip


def _check(tmp_path: Path, consumer: str, text: str) -> list[dict[str, Any]]:
    script, rel, _ = _LEDGERS[consumer]
    done, _, _ = _run(tmp_path, script, {rel: text}, "check", "--json")
    assert done.returncode == 1, done.stderr
    return list(json.loads(done.stdout))


@pytest.mark.parametrize("consumer", _LEDGERS)
def test_a_line_that_is_not_json_is_a_schema_finding_at_its_number(tmp_path: Path, consumer: str) -> None:  # fmt: skip
    found = _check(tmp_path, consumer, '{"title": "a\u2028b"}\n{x\n')  # U+2028 stays in line 1
    bad = [(r["code"], r["line"], r["message"]) for r in found if "not valid JSON" in r["message"]]
    assert bad == [(_LEDGERS[consumer][2], 2, _NOT_JSON)]


@pytest.mark.parametrize(
    ("consumer", "record", "message"),
    [
        ("bugs", _BUG, "duplicate record id 'a' (first appended at line 1)"),
        ("audit", _FINDING, "duplicate finding id 'a1-F001'"),
    ],
)
def test_a_duplicate_id_is_one_finding_at_the_second_line(tmp_path: Path, consumer: str, record: dict[str, Any], message: str) -> None:  # fmt: skip
    found = _check(tmp_path, consumer, (json.dumps(record) + "\n") * 2)
    assert [(r["line"], r["message"]) for r in found] == [(2, message)]


#: consumer -> (a valid document, a write verb that changes it)
_WRITES = {
    "bugs": ({"bugs/BUGS.jsonl": json.dumps(_BUG) + "\n"}, ["update", "a", "--set", "caused_by=none"]),
    "backlog": ({"backlog/BACKLOG.json": '{"schema": "backlog-v1", "active": []}\n'}, ["new", "zz"]),
    "audit": ({"audits/a1/FINDINGS.jsonl": json.dumps(_FINDING) + "\n"},
              ["disposition", "a1", "a1-F001", "--disposition", "rejected", "--reason", "r"]),
    "release": ({"releases/9.9.9/_RELEASE.json": json.dumps({**_STATE, "phase": "IMPLEMENTATION", "defined": None, "shipped": None}) + "\n"},
                ["phase", "CLOSURE", "--sha", "abc1234"]),
}  # fmt: skip


@pytest.mark.parametrize("consumer", _WRITES)
def test_an_accepted_write_leaves_no_temp_sibling(tmp_path: Path, consumer: str) -> None:
    files, argv = _WRITES[consumer]
    done, before, after = _run(tmp_path, _LEDGERS[consumer][0], files, *argv)
    assert done.returncode == 0, done.stderr
    assert (after.keys(), after != before) == (before.keys(), True)


def test_the_one_ledger_writer_leaves_no_temp_and_writes_lf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing os.replace leaves no temp sibling and the original byte-unchanged; a write is
    LF."""
    import importlib.util

    source = _PUBLIC / "skills" / "dd-bug-resolution" / "scripts" / "_ledger.py"
    spec = importlib.util.spec_from_file_location("_ledger_under_test", source)
    assert spec is not None and spec.loader is not None
    ledger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger)
    target = tmp_path / "BUGS.jsonl"
    target.write_bytes(b"original\n")
    with monkeypatch.context() as patch:
        patch.setattr("os.replace", lambda *_: (_ for _ in ()).throw(OSError("injected")))
        with pytest.raises(OSError, match="injected"):
            ledger.replace(target, "new\n")
    assert [p.name for p in tmp_path.iterdir()] == ["BUGS.jsonl"]
    assert target.read_bytes() == b"original\n"
    ledger.replace(target, "a\nb\n")
    assert target.read_bytes() == b"a\nb\n"


@pytest.fixture
def script_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """A staged script's module-level name, read by running the script as `public stage`
    ships it; the modules it imports leave with the test."""
    skills, before = _stage(tmp_path), set(sys.modules)
    sibling = [
        str(skills / s / "scripts")
        for s in ("dd-backlog-definition", "dd-bug-resolution", "dd-release-implementation")
    ]
    monkeypatch.setattr(sys, "path", [*sys.path, *sibling])  # as backlog.py puts them
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    yield lambda rel, name="REQUIRED_EVIDENCE": runpy.run_path(str(skills / rel))[name]
    for module in set(sys.modules) - before:
        del sys.modules[module]


@pytest.mark.parametrize(
    ("rel", "name"),
    [
        ("dd-bug-resolution/scripts/_bugs_check.py", "TERMINAL"),
        ("dd-backlog-definition/scripts/_backlog_schema.py", "DISPOSITIONS"),
        ("dd-backlog-definition/scripts/_backlog_schema.py", "TERMINAL"),
        ("dd-audit-project/scripts/_audit_check.py", "DISPOSITIONS"),
    ],
)
def test_every_script_subset_is_drawn_from_the_one_vocabulary(
    script_table: Any, rel: str, name: str
) -> None:
    subset = script_table(rel, name)
    assert set(subset) <= set(TERMINAL_DISPOSITIONS)
    if rel in {
        "dd-bug-resolution/scripts/_bugs_check.py",
        "dd-audit-project/scripts/_audit_check.py",
    }:
        assert "deferred" not in subset


def test_a_shared_disposition_requires_the_same_evidence_in_both_ledgers(
    script_table: Any,
) -> None:
    """The scripts' own tables are the only definition, core carries none, and a word both
    ledgers use requires the same evidence in each."""
    rows = script_table("dd-backlog-definition/scripts/_backlog_exit.py", "EVIDENCE")
    dispositions = script_table("dd-backlog-definition/scripts/_backlog_schema.py", "DISPOSITIONS")
    assert set(rows) == set(dispositions)
    backlog = {word: flag for word, (flag, _verifier) in rows.items()}
    audit = script_table("dd-audit-project/scripts/_audit_check.py")
    shared = {w: (backlog[w], audit[w]) for w in backlog.keys() & audit.keys()}
    assert shared == {"superseded": ("release",) * 2, "rejected": ("reason",) * 2}


def test_the_ledger_walk_skips_a_fenced_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip
    """No dadaia process acts on a fenced root, the privacy lookup included."""
    import importlib.util

    source = _PUBLIC / "skills" / "dd-bug-resolution" / "scripts" / "_ledger.py"
    spec = importlib.util.spec_from_file_location("_ledger_fenced", source)
    assert spec is not None and spec.loader is not None
    ledger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger)
    (tmp_path / ".dadaia/states").mkdir(parents=True)
    (tmp_path / ".dadaia/states/spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "specs").mkdir()
    assert ledger.workspace_of(tmp_path / "specs") == tmp_path.resolve()
    monkeypatch.setenv("DADAIA_FENCED_ROOTS", str(tmp_path))
    assert ledger.workspace_of(tmp_path / "specs") is None
