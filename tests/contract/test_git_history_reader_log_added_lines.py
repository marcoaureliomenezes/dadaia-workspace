"""``GitSubprocessClient.log_added_lines`` against a real, throwaway git repository.

Intent: CONTRACT — 0.5.0 A3.10. Size: SMALL.

The ONE test in the whole T-050-09 write set that needs a synthetic git repository
(FR3's own placement rule: "the one test that still needs a synthetic git repository ...
is placed in ``tests/contract/``, never ``tests/unit/``" — its subprocess/I/O cost is
exactly the profile that aggravates the still-open
``windows-xdist-workers-crash-on-unit-fast-tier``). Drives a real repo under pytest
``tmp_path`` (never inside the source tree), mirroring
``tests/unit/infrastructure/test_git_subprocess_diff.py``'s own throwaway-repo pattern.

Proves the ruling's precision (AR-1 §3.4): ``touched_paths`` is the commit's WHOLE,
unrestricted changed-path set (needed for the ``exact`` marker), paired with the
PATHSPEC-RESTRICTED ``added_lines`` — one commit that adds a bug line AND a non-``specs/``
file (``exact``), one that adds a bug line and touches nothing else (``ledger-only``).

bug ``git-history-walk-omits-full-history-hides-ledger-commits``: a second synthetic
repo below (``test_log_added_lines_sees_a_commit_history_simplification_would_otherwise_hide``)
builds — with plumbing (``commit-tree``), never relying on an auto-merge's guess — a
merge commit whose tree for the pathspec is byte-identical to its FIRST parent, with a
SECOND parent (a since-deleted branch tip) that really did touch the pathspec. Without
``--full-history``, git's default history simplification treesame-prunes that second
parent out of the walk entirely — the commit is a real ancestor, reachable only through
the merge's parent list (its own branch ref is gone, the routine post-merge gitflow
shape this workspace's own ``dd-gitflow-default`` mandates), yet invisible.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

pytestmark = [pytest.mark.slow]


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=path, capture_output=True
    )
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, capture_output=True)


def _commit_all(path: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=path, capture_output=True, check=True)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def test_log_added_lines_reports_exact_and_ledger_only_from_a_real_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)

    bugs_dir = repo / "specs" / "bugs"
    bugs_dir.mkdir(parents=True)
    ledger = bugs_dir / "bugs.jsonl"
    ledger.write_text('{"event": "reported", "bug_id": "bug-alpha"}\n')
    (repo / "code.py").write_text("print('hi')\n")
    exact_sha = _commit_all(repo, "register bug-alpha, touch code")

    ledger.write_text(ledger.read_text() + '{"event": "reported", "bug_id": "bug-beta"}\n')
    ledger_only_sha = _commit_all(repo, "register bug-beta, ledger only")

    commits = list(GitSubprocessClient().log_added_lines(repo, "specs/bugs/"))

    assert [c.sha for c in commits] == [exact_sha, ledger_only_sha]

    exact_commit = commits[0]
    assert exact_commit.parents == ()
    assert '{"event": "reported", "bug_id": "bug-alpha"}' in exact_commit.added_lines
    assert "code.py" in exact_commit.touched_paths
    assert any(not p.startswith("specs/") for p in exact_commit.touched_paths)

    ledger_only_commit = commits[1]
    assert ledger_only_commit.parents == (exact_sha,)
    assert '{"event": "reported", "bug_id": "bug-beta"}' in ledger_only_commit.added_lines
    assert all(p.startswith("specs/") for p in ledger_only_commit.touched_paths)
    assert ledger_only_commit.date  # non-empty ISO-8601 author date


def _run(args: list[str], *, cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def test_log_added_lines_sees_a_commit_history_simplification_would_otherwise_hide(
    tmp_path: Path,
) -> None:
    """bug ``git-history-walk-omits-full-history-hides-ledger-commits``.

    Built with plumbing (``commit-tree``/``update-ref``), never an auto-merge's guess,
    so the scenario is deterministic: a merge commit ``m`` with parents ``[a1, t1]``
    whose TREE for the pathspec is byte-identical to ``a1``'s (``t1``'s change never
    survives the merge) — and ``t1``'s own branch ref is deleted afterward, the routine
    post-merge shape this workspace's own gitflow mandates. Without ``--full-history``,
    git's default treesame-based simplification never even queues ``t1`` for traversal
    when walking through ``m`` — it is a real ancestor, invisible to the walk. This is
    the ONE test in the module that needs the full plumbing, not the higher-level
    ``_commit_all`` helper, because the merge's exact tree must be pinned by hand."""
    repo = tmp_path / "repo"
    _init_repo(repo)

    bugs_dir = repo / "specs" / "bugs"
    bugs_dir.mkdir(parents=True)
    ledger = bugs_dir / "BUGS.jsonl"
    ledger.write_text('{"id": "bug-a0"}\n')
    a0_sha = _commit_all(repo, "a0: init ledger")
    trunk = _run(["git", "symbolic-ref", "--short", "HEAD"], cwd=repo)  # whatever init picked

    subprocess.run(
        ["git", "checkout", "-q", "-b", "topic"], cwd=repo, capture_output=True, check=True
    )
    ledger.write_text(ledger.read_text() + '{"id": "bug-t1-must-not-be-hidden"}\n')
    t1_sha = _commit_all(repo, "t1: topic adds a bug record")

    subprocess.run(["git", "checkout", "-q", trunk], cwd=repo, capture_output=True, check=True)
    (repo / "README.md").write_text("mainline-only change\n")
    a1_sha = _commit_all(repo, "a1: mainline unrelated change")

    # The merge's tree is EXPLICITLY pinned to a1's own tree — t1's ledger addition is
    # discarded by construction, never left to an auto-merge's guess.
    a1_tree = _run(["git", "rev-parse", f"{a1_sha}^{{tree}}"], cwd=repo)
    merge_sha = _run(
        ["git", "commit-tree", a1_tree, "-p", a1_sha, "-p", t1_sha, "-m", "m: merge, discard t1"],
        cwd=repo,
    )
    subprocess.run(
        ["git", "update-ref", f"refs/heads/{trunk}", merge_sha],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(["git", "branch", "-D", "topic"], cwd=repo, capture_output=True, check=True)

    commits = list(GitSubprocessClient().log_added_lines(repo, "specs/bugs/"))

    assert [c.sha for c in commits] == [a0_sha, t1_sha], (
        "t1 (the commit history simplification hides without --full-history) is "
        f"missing from the walk: {[c.sha for c in commits]}"
    )
    assert '{"id": "bug-t1-must-not-be-hidden"}' in commits[1].added_lines


def test_log_added_lines_refuses_a_shallow_repository(tmp_path: Path) -> None:
    """bug ``release-workflow-shallow-checkout-collapses-resolved-commit-derivation-to-head``:
    a shallow clone can only walk the commits it has, so every ledger line derives to
    HEAD — the silent under-report the port forbids. The adapter refuses the walk
    instead of returning a partial history (fixes the class, not one more yaml checkout)."""
    from dadaia_workspace.core.protocols.git_history_reader import GitHistoryReadError

    origin = tmp_path / "origin"
    _init_repo(origin)
    bugs_dir = origin / "specs" / "bugs"
    bugs_dir.mkdir(parents=True)
    ledger = bugs_dir / "bugs.jsonl"
    ledger.write_text('{"event": "reported", "bug_id": "bug-alpha"}\n')
    _commit_all(origin, "register bug-alpha")
    ledger.write_text(ledger.read_text() + '{"event": "resolved", "bug_id": "bug-alpha"}\n')
    _commit_all(origin, "resolve bug-alpha")

    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "--quiet", "--depth", "1", origin.as_uri(), str(shallow)],
        capture_output=True,
        check=True,
    )

    with pytest.raises(GitHistoryReadError, match="shallow"):
        list(GitSubprocessClient().log_added_lines(shallow, "specs/bugs/"))
