"""Metric 6 of `verdict.py stats` exempts a commit by the path it writes. Size: SMALL (real git, tmp repo)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tests.helpers.oslib import read_text, write_text
from tests.helpers.worktree_ws import git, make_workspace

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "dadaia_workspace/public/skills/dd-handoff-emitter/scripts"))  # fmt: skip
import _stats  # noqa: E402
from _refusal import Refusal  # noqa: E402


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


def test_a_code_file_moved_into_audits_is_work(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    _commit(tmp_path, "feat(J1.T1): code " * 20, "src/x.py")
    closure = git(tmp_path, "rev-parse", "HEAD").strip()
    (tmp_path / "specs/audits").mkdir(parents=True)
    git(tmp_path, "mv", "src/x.py", "specs/audits/x.py")
    git(tmp_path, "commit", "-q", "-m", "feat(J1.T2): move")
    assert _stats._after_closure(tmp_path, closure, "HEAD") == "1"


def test_audit_paths_with_a_space_or_a_non_ascii_byte_are_not_work(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    _commit(tmp_path, "docs(memory): closure")
    closure = git(tmp_path, "rev-parse", "HEAD").strip()
    _commit(tmp_path, "docs(audits): spaced", "specs/audits/a b.md")
    _commit(tmp_path, "docs(audits): accented", "specs/audits/açao.md")
    assert _stats._after_closure(tmp_path, closure, "HEAD") == "0"


_CLOSURE = "chore(release): rc-1 phase CLOSURE"


def _closed_candidate(root: Path, *, closure_commit: bool) -> Path:
    """A workspace whose release state stores an `implemented` sha no history holds, with two
    non-block commits after the closure commit when *closure_commit*."""
    make_workspace(root)
    repo, ts = root / "repos/r", "2026-10-12T11:00:00Z"
    state = repo / "specs/releases/0.5.0/_RELEASE.json"
    log = [{"ts": "2026-10-12T09:00:00Z", "agent": "release.py new", "kind": "note", "text": "born"},
           {"ts": ts, "agent": "release.py", "kind": "milestone", "candidate": "rc-1",
            "milestone": "implemented", "sha": "9" * 40, "text": "x"}]  # fmt: skip
    write_text(state, json.dumps({**json.loads(read_text(state)), "log": log}))
    git(repo, "add", "specs")
    _commit(repo, "feat(J1.T1): before")
    if closure_commit:
        _commit(repo, _CLOSURE)
    _commit(repo, "feat(J1.T2): after one")
    _commit(repo, "feat(J1.T3): after two")
    return repo


def _metric_6(root: Path) -> str | None:
    """Metric 6's value, or None when the table refuses."""
    repo = root / "repos/r"
    try:
        table = _stats.table(root, repo / "specs", "0.5.0-rc1")
    except Refusal:
        return None
    return next(ln.split("\t")[1] for ln in table.splitlines() if ln.startswith("6 "))


def test_the_closure_commit_is_found_by_its_subject_when_the_stored_sha_is_orphaned(
    tmp_path: Path,
) -> None:
    _closed_candidate(tmp_path, closure_commit=True)
    assert _metric_6(tmp_path) == "2"


def test_a_vanished_closure_commit_is_never_zero(tmp_path: Path) -> None:
    _closed_candidate(tmp_path, closure_commit=False)
    assert _metric_6(tmp_path) in (None, "n/a")
