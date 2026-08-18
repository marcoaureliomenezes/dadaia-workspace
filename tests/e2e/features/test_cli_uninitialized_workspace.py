"""A CLI verb run outside an initialized workspace must fail CLEANLY.

Bug doctor-uninitialized-workspace-traceback (found by the sample-consumer Consumer
consumer, recipe F-22): `dadaia doctor`, `dadaia public doctor`, and `dadaia reports
doctor` raised WorkspaceNotInitializedError (a DadaiaError), which Typer rendered as a
full Python/Rich TRACEBACK — and two of them even exited 0 despite it. A CLI must
surface a concise, actionable error and a NON-ZERO exit, never a traceback. server/plugin
already did this per-command; this pins the whole class via the global entrypoint handler.

Intent: CONTRACT — bug doctor-uninitialized-workspace-traceback
Owner: software-engineer
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_VERBS = [
    ["doctor"],
    ["public", "doctor"],
    ["reports", "doctor"],
]


def _cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120.0,
    )


@pytest.mark.parametrize("verb", _VERBS, ids=lambda v: " ".join(v))
def test_verb_in_uninitialized_workspace_fails_cleanly(tmp_path: Path, verb: list[str]) -> None:
    result = _cli(tmp_path, *verb)
    combined = result.stdout + result.stderr
    assert "Traceback (most recent call last)" not in combined, (
        f"`dadaia {' '.join(verb)}` printed a Python traceback:\n{combined}"
    )
    assert result.returncode != 0, (
        f"`dadaia {' '.join(verb)}` exited 0 in an uninitialized workspace:\n{combined}"
    )
    # The message must orient the operator toward `dadaia init`.
    assert "init" in combined.lower(), combined
