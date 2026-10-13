"""The five check verbs share one finding renderer and one decode-aware reader.
Size: SMALL.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.skill_scripts import stage_skill_scripts

# verb: (skill, script, code, a tree the verb flags, a file whose bytes are not UTF-8)
_VERBS = {
    "audit": ("dd-audit-project", "audit.py", "LEDGER-FINDINGS-SCHEMA",
              ("audits/_archive/audits_histo.jsonl", b"not json\n"), "audits/20260101-w/FINDINGS.jsonl"),
    "bugs": ("dd-bug-resolution", "bugs.py", "LEDGER-BUGS-SCHEMA",
             ("bugs/BUGS.jsonl", b"not json\n"), "bugs/BUGS.jsonl"),
    "backlog": ("dd-backlog-definition", "backlog.py", "LEDGER-BACKLOG-SCHEMA",
                ("backlog/_archive/backlog_histo.jsonl", b"not json\n"), "backlog/BACKLOG.json"),
    "memory": ("dd-spec-navigator", "memory.py", "LEDGER-MEMORY-SCHEMA",
               ("memory/.keep", b""), "memory/product/area/x.md"),
    "release": ("dd-release-implementation", "release.py", "LEDGER-RELEASE-SCHEMA",
                ("releases/0.5.0/.keep", b""), "releases/0.5.0/_RELEASE.json"),
}  # fmt: skip


def _check(tmp_path: Path, verb: str, planted: tuple[str, bytes]):
    """A runner of ``check`` over a specs tree holding only *planted*."""
    skill, name, *_ = _VERBS[verb]
    script = stage_skill_scripts(skill, tmp_path / "staged" / "scripts") / name
    specs = tmp_path / "repo" / "specs"
    target = specs / planted[0]
    target.parent.mkdir(parents=True)
    target.write_bytes(planted[1])
    return lambda *flags: subprocess.run(
        [sys.executable, str(script), "check", "--specs", str(specs), *flags],
        capture_output=True, check=False, text=True,
    )  # fmt: skip


@pytest.mark.parametrize("verb", _VERBS)
def test_text_mode_prints_each_findings_fix_after_it(tmp_path: Path, verb: str) -> None:
    run = _check(tmp_path, verb, _VERBS[verb][3])
    as_json, as_text = run("--json"), run()

    findings = json.loads(as_json.stdout)
    assert as_text.returncode == 1 and findings
    lines = as_text.stdout.splitlines()
    for finding in findings:
        at = next(i for i, line in enumerate(lines) if finding["message"] in line)
        assert lines[at + 1] == f"fix: {finding['fix']}"


@pytest.mark.parametrize("verb", _VERBS)
def test_a_file_that_is_not_utf8_is_a_finding_of_the_verbs_own_code(
    tmp_path: Path, verb: str
) -> None:
    code, relative = _VERBS[verb][2], _VERBS[verb][4]
    done = _check(tmp_path, verb, (relative, b"\xff\xfe\n"))("--json")

    assert done.returncode == 1 and "Traceback" not in done.stderr
    (finding,) = json.loads(done.stdout)
    assert (finding["code"], finding["verdict"], finding["path"]) == (code, "error", relative)
    assert "git" in finding["fix"] and relative in finding["fix"]
