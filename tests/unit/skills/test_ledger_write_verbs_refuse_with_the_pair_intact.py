"""Intent: CONTRACT — sa-ledger-verbs-append-histo-before-validating-the-pair#J4: "Given
any write verb of bugs.py, backlog.py, audit and release scripts and an injected invalid
document, when the verb exits non-zero, then no file of its pair changed (hash before =
after)." Size: SMALL — each ledger script as a child process over a tmp specs tree.

Every case injects a schema-invalid (still JSON) document, so the refusal can only come
from the pair check the verb runs over its candidate bytes before writing.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import _SKILL_SCRIPT_SCHEMAS

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
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
        shutil.copytree(_PUBLIC / "skills" / skill / "scripts", skills / skill / "scripts")
    for schema_rel, scripts_rel in _SKILL_SCRIPT_SCHEMAS:
        (root / scripts_rel).mkdir(parents=True, exist_ok=True)
        shutil.copy2(_PUBLIC / schema_rel, root / scripts_rel / Path(schema_rel).name)
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
