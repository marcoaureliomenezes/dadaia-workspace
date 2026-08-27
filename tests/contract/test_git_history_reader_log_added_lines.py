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
