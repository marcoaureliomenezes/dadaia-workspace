"""A skill entry point prints UTF-8 whatever codec the host pipe defaults to (cp1252 on Windows)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tests.helpers.oslib import run

_SKILLS = Path(__file__).resolve().parents[5] / "dadaia_workspace" / "public" / "skills"
_ENTRIES = [
    "dd-bug-resolution/scripts/bugs.py",
    "dd-spec-navigator/scripts/memory.py",
    "dd-audit-project/scripts/audit.py",
    "dd-backlog-definition/scripts/backlog.py",
    "dd-release-implementation/scripts/release.py",
]
_VERB = {"bugs.py": "status", "memory.py": "check", "audit.py": "check"}


_ENV = {**os.environ, "PYTHONIOENCODING": "cp1252"}


@pytest.mark.parametrize("entry", _ENTRIES)
def test_a_refusal_naming_a_non_cp1252_path_prints_it_as_utf8(entry: str) -> None:
    script, given = _SKILLS / entry, "no-\u2192"
    done = run(
        [sys.executable, "-B", str(script), _VERB.get(script.name, "check"), "--specs", given],
        env=_ENV,
    )
    assert done.returncode == 1
    assert f"no specs tree at {Path(given)} " in done.stderr


def test_verdict_prints_a_non_cp1252_word_of_its_own_usage_error_as_utf8() -> None:
    script = _SKILLS / "dd-handoff-emitter/scripts/verdict.py"
    argv = [
        "x",
        "--sha",
        "1",
        "--context",
        "c",
        "--slug",
        "s",
        "--verdict",
        "\u2192",
        "--reason",
        "r",
    ]
    done = run([sys.executable, "-B", str(script), *argv], env=_ENV)
    assert done.returncode == 2
    assert "invalid choice: '\u2192'" in done.stderr
