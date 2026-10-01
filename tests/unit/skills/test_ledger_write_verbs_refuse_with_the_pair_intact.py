"""Intent: CONTRACT — sa-ledger-verbs-append-histo-before-validating-the-pair#J4: "Given
any write verb of bugs.py, backlog.py, audit and release scripts and an injected invalid
document, when the verb exits non-zero, then no file of its pair changed (hash before =
after)." Size: SMALL — each ledger script as a child process over a tmp specs tree.

Every case injects a schema-invalid (still JSON) document, so the refusal can only come
from the pair check the verb runs over its candidate bytes before writing.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.helpers.skill_scripts import stage_skill_scripts

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_HISTO_SCHEMA = json.loads((_PUBLIC / "schemas/histo/histo-record-v1.schema.json").read_text())
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
        ["update", "a-bug", "--set", "audited=x"],
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


@pytest.mark.parametrize("case", sorted(_CASES))
def test_a_write_verb_over_an_invalid_document_refuses_with_the_pair_intact(
    case: str, tmp_path: Path
) -> None:
    script, files, argv = _CASES[case]
    skills = _stage(tmp_path)
    specs = tmp_path / "specs"
    for rel, text in files.items():
        (specs / rel).parent.mkdir(parents=True, exist_ok=True)
        (specs / rel).write_text(text, encoding="utf-8")
    before = _hashes(specs)

    done = subprocess.run(
        [sys.executable, str(skills / script), *argv, "--specs", str(specs)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip

    assert done.returncode != 0, done.stdout
    assert _hashes(specs) == before, done.stderr


def test_the_one_ledger_writer_leaves_no_temp_and_writes_lf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.2: a failing
    os.replace leaves no temp sibling and the original byte-unchanged.
    sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.3: a write is LF."""
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


class _Names(dict[str, Any]):
    """A name the module binds elsewhere (a function, an import) reads as its own text."""

    def __missing__(self, key: str) -> str:
        return key


def _script_table(rel: str, name: str = "REQUIRED_EVIDENCE") -> Any:
    """The module's top-level assignments run in order, so a table derived from another
    (`TERMINAL` from `DISPOSITIONS`) reads as the script itself builds it."""
    tree = ast.parse((_PUBLIC / "skills" / rel).read_text(encoding="utf-8"))
    names = _Names()
    for node in tree.body:
        if isinstance(node, ast.Assign):  # one that needs a runtime value is not a table
            with contextlib.suppress(Exception):
                exec(compile(ast.Module([node], []), rel, "exec"), {}, names)  # noqa: S102
    return names[name]


@pytest.mark.parametrize(
    ("rel", "name"),
    [
        ("dd-bug-resolution/scripts/_bugs_check.py", "TERMINAL"),
        ("dd-backlog-definition/scripts/_backlog_schema.py", "DISPOSITIONS"),
        ("dd-backlog-definition/scripts/_backlog_schema.py", "TERMINAL"),
        ("dd-audit-project/scripts/_audit_check.py", "DISPOSITIONS"),
    ],
)
def test_every_script_subset_is_drawn_from_the_one_vocabulary(rel: str, name: str) -> None:
    subset = _script_table(rel, name)
    assert set(subset) <= set(TERMINAL_DISPOSITIONS)


def test_a_shared_disposition_requires_the_same_evidence_in_both_ledgers() -> None:
    """sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.1: the scripts' own
    tables are the only definition, core carries none, and a word both ledgers use
    requires the same evidence in each."""
    rows = _script_table("dd-backlog-definition/scripts/_backlog_exit.py", "EVIDENCE")
    backlog = {word: flag for word, (flag, _verifier) in rows.items()}
    audit = _script_table("dd-audit-project/scripts/_audit_check.py")
    shared = {w: (backlog[w], audit[w]) for w in backlog.keys() & audit.keys()}
    assert shared == {"superseded": ("release",) * 2, "rejected": ("reason",) * 2}
