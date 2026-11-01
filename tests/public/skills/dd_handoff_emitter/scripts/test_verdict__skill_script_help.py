"""Every skill script's `--help` description is its docstring's first paragraph, whole and alone."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.helpers.oslib import run
from tests.helpers.skill_scripts import stage_skill_scripts


@pytest.mark.parametrize(
    ("skill", "script", "sentence", "rest"),
    [
        ("dd-audit-project", "audit.py", "and validate the audit.", ""),
        ("dd-backlog-definition", "backlog.py", "append-only exit ledger, stdlib only.", ""),
        ("dd-gitflow-default", "worktree.py", "restores it from that bundle.", ""),
        (
            "dd-handoff-emitter",
            "verdict.py",
            "diff it judged; `verdict.py stats <rc>` prints the readout.",
            "",
        ),
        (
            "dd-spec-navigator",
            "memory.py",
            "The memory catalog's ONE writer: catalog.json and the Feature catalog of index.md, from the atoms.",
            "",
        ),
        ("dd-release-implementation", "release.py", "and SPEC stub, stdlib only.", ""),
        ("dd-bug-resolution", "bugs.py", "`specs/bugs/BUGS.jsonl`, stdlib only.", ""),
        (
            "dd-cli-library",
            "registry.py",
            "Dev-server port registry — stdlib only, one JSON file.",
            "written atomically",
        ),
    ],
)
def test_help_prints_the_whole_first_sentence(
    tmp_path: Path, skill: str, script: str, sentence: str, rest: str
) -> None:
    staged = stage_skill_scripts(skill, tmp_path / "skills" / skill / "scripts")

    out = run([sys.executable, str(staged / script), "--help"], check=False).stdout

    text = " ".join(out.split())
    assert sentence in text
    assert not rest or rest not in text
