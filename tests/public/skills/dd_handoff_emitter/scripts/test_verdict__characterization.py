"""Characterization net for the public ``verdict.py`` seam owned by CP1."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.harness_env import suite_env
from tests.helpers.skill_scripts import stage_skill_scripts
from tests.helpers.worktree_ws import commit, diff_hash, git, make_workspace, run

pytestmark = pytest.mark.slow(reason="runs the public scripts over a real Git worktree")

_BODY = {
    "self_pull": {"refs": ["specs/memory/ARCHITECTURE.md"]},
    "artifact": {"type": "other"},
    "metrics": {"finding_count": 0},
}
_NOW = "2026-10-09T12:34:56Z"


def test_verdict_writes_the_exact_bound_handoff(tmp_path: Path) -> None:
    (root := tmp_path / "workspace").mkdir()
    make_workspace(root)
    for skill in (
        "dd-handoff-emitter",
        "dd-gitflow-default",
        "dd-bug-resolution",
        "dd-release-implementation",
    ):
        stage_skill_scripts(skill, root / ".agents/skills" / skill / "scripts")
    repo = root / "repos/r"
    git(repo, "checkout", "-q", "feature/0.5.0")
    name = "0.5.0-rc1/define"
    assert run(root, "new", "r", name).returncode == 0
    tree = root / "worktrees/r" / name
    head = commit(tree, "specs/note.md", "reviewed\n")
    script = root / ".agents/skills/dd-handoff-emitter/scripts/verdict.py"

    bootstrap = (
        "import sys\nfrom datetime import datetime\nfrom pathlib import Path\n"
        "sys.path.insert(0, str(Path(sys.argv.pop(1))))\n"
        "import verdict\n"
        "class Clock:\n"
        " @staticmethod\n"
        f" def now(tz): return datetime.fromisoformat({_NOW!r}.replace('Z', '+00:00'))\n"
        "verdict.datetime = Clock\n"
        "raise SystemExit(verdict.main(sys.argv[1:]))"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            bootstrap,
            str(script.parent),
            str(tree),
            "--sha",
            head,
            "--context",
            "catalog",
            "--slug",
            "characterization",
            "--verdict",
            "APPROVED",
            "--reason",
            "characterized",
        ],
        cwd=root,
        env=suite_env(os.environ, root),
        input=json.dumps(_BODY),
        capture_output=True,
        text=True,
        check=False,
    )

    assert (result.returncode, result.stderr) == (0, "")
    target = (
        root
        / ".dadaia/handoff/catalog/2026-10-09T123456Z-dd-code-reviewer-characterization.handoff.json"
    )
    assert result.stdout == f"{target}\n"
    assert target.parent == root / ".dadaia/handoff/catalog"
    assert target.name == "2026-10-09T123456Z-dd-code-reviewer-characterization.handoff.json"
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document == {
        "schema_version": "handoff-v1.2",
        "agent": "dd-code-reviewer",
        "context": "catalog",
        "produced_at": "2026-10-09T12:34:56Z",
        "verdict": "APPROVED",
        "verdict_reason": "characterized",
        "scope": f"wt/{name}@{head}",
        "reviewed_sha": head,
        "diff_sha256": diff_hash(root, head),
        **_BODY,
    }
    assert sorted((root / ".dadaia/handoff").glob("**/*.handoff.json")) == [target]
