"""Metric 6 of `verdict.py stats` exempts a commit by the path it writes. Size: SMALL (real git, tmp repo)."""

from __future__ import annotations

import sys
from pathlib import Path

from tests.helpers.oslib import write_text
from tests.helpers.worktree_ws import git

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "dadaia_workspace/public/skills/dd-handoff-emitter/scripts"))  # fmt: skip
import _stats  # noqa: E402


def _commit(repo: Path, message: str, *files: str) -> None:
    for rel in files:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        write_text(repo / rel, message)
        git(repo, "add", rel)
    git(repo, "commit", "-q", "--allow-empty", "-m", message)


def test_commits_writing_only_audits_are_not_non_block_work(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    _commit(tmp_path, "docs(memory): closure")
    closure = git(tmp_path, "rev-parse", "HEAD").strip()
    _commit(tmp_path, "chore(audits): F1 resolved", "specs/audits/a.md")
    _commit(tmp_path, "docs(audits): F2 closed", "specs/audits/b.md")
    _commit(tmp_path, "feat(J1.T1): mixed", "specs/audits/c.md", "src/x.py")
    _commit(tmp_path, "feat(J1.T2): no files")
    assert _stats._after_closure(tmp_path, closure, "HEAD") == "2"
