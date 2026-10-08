"""shallow-clone-history-finding-fix-line-never-clears#history: a
history read that a shallow clone cannot answer names the missing history, and its fix
line, run verbatim, clears the refusal.

size: MEDIUM — real git clones over file:// and the real release script's `drift` verb.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core import cli_line
from tests.helpers.release_state import PLAN
from tests.public.skills.dd_release_implementation.scripts.test_release import (
    script,  # noqa: F401  (the staged-skill fixture)
)

pytestmark = pytest.mark.slow(reason="real git clones")


def _git(cwd: Path, *argv: str) -> str:
    done = subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _commit(repo: Path, name: str) -> str:
    (repo / name).write_text(name, "utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", name)
    return _git(repo, "rev-parse", "HEAD")


def _origin(tmp: Path) -> Path:
    """A CLOSURE release whose memory entry spans c1..c2, HEAD one commit later."""
    origin = tmp / "origin"
    (origin / "specs" / "memory" / "product").mkdir(parents=True)
    (origin / "specs" / "memory" / "product" / "catalog.json").write_text(
        '{"features": []}\n', "utf-8"
    )
    _git(tmp, "init", "-q", "origin")
    _git(origin, "config", "user.email", "t@example.invalid")
    _git(origin, "config", "user.name", "t")
    c1, c2 = _commit(origin, "a.txt"), _commit(origin, "b.txt")
    release = origin / "specs" / "releases" / "9.9.9"
    (release / "rc-1").mkdir(parents=True)
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (release / "rc-1" / name).write_text(
            f"# x\n\n{PLAN if name == 'PLAN.md' else '**Origin:** operator-demand'}"
            + ("\n\n## Bug window review\n" if name == "SPEC.md" else ""),
            "utf-8",
        )
    ts = "2026-01-01T00:00:00Z"
    state = {
        "schema": "release-state-v1", "release": "9.9.9", "phase": "CLOSURE",
        "defined": {"sha": c1, "ts": ts}, "implemented": {"sha": c2, "ts": ts},
        "shipped": None,
        "log": [{"ts": ts, "agent": "release.py memory", "kind": "memory", "text": "m",
                 "since": c1, "until": c2, "reviewed": [], "changed": []}],
    }  # fmt: skip
    (release / "_RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", "utf-8")
    _commit(origin, "c.txt")
    return origin


def _drift(release: Path, specs: Path) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, str(release), "drift", "--specs", str(specs)]
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def test_a_shallow_clone_finding_names_the_history_and_its_fix_clears_it(
    script: Path,  # noqa: F811
    tmp_path: Path,
) -> None:
    clone = tmp_path / "my ws" / "repos" / "checkout"  # the fix quotes its spaced path
    _git(tmp_path, "clone", "-q", "--depth", "1", f"file://{_origin(tmp_path)}", str(clone))

    refused = _drift(script, clone / "specs")

    assert refused.returncode == 1
    assert "shallow" in refused.stderr
    [fix] = [
        line.removeprefix("fix: ")
        for line in refused.stderr.splitlines()
        if line.startswith("fix: ")
    ]
    assert shlex.split(fix) == shlex.split(cli_line.git_line(clone, "fetch", "--unshallow"))
    subprocess.run(shlex.split(fix), check=True, capture_output=True)
    cleared = _drift(script, clone / "specs")
    assert (cleared.returncode, cleared.stderr) == (0, "")
