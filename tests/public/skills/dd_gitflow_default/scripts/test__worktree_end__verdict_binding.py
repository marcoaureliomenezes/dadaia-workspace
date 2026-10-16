"""A job merge lands only a verdict that names a sha of the job's range in `reviewed_sha` and
carries the `diff_sha256` of the diff the merge lands; a hand form, a missing or other hash, a sha outside the job's range and a
same-patch rebase over other blobs each refuse. `worktree.py hash` prints the binding.
Size: MEDIUM (real git, tmp workspace, a stub CLI).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import shell_line
from dadaia_workspace.core.platform import cli_argv
from tests.helpers.oslib import command, venv_dir, write_text
from tests.helpers.worktree_ws import (
    NEW_JOB,
    SCRIPT,
    approve,
    commit,
    diff_hash,
    fixes,
    git,
    land,
    make_workspace,
    open_tree,
    run,
)

RC = "0.5.0/rc-1/wt-rc"
TREE = f"worktrees/r/{NEW_JOB}"
VALIDATE_ALL = "validate-all"
DISPATCH = "dispatch"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path := tmp_path / "my ws").mkdir()
    make_workspace(tmp_path)
    git(tmp_path / "repos/r", "checkout", "-q", "feature/0.5.0")
    open_tree(tmp_path, RC)
    assert open_tree(tmp_path, NEW_JOB).is_dir()
    return tmp_path


def _hand(root: Path, scope_sha: str, **fields: str) -> None:
    """A valid APPROVED a hand wrote: `scope` names *scope_sha*, *fields* ride beside it."""
    handoff = root / ".dadaia/handoff/c/2026-10-02T100000Z-dd-code-reviewer-hand.handoff.json"
    handoff.parent.mkdir(parents=True, exist_ok=True)
    write_text(
        handoff,
        json.dumps(
            {
                "schema_version": "1.2",
                "agent": "dd-code-reviewer",
                "verdict": "APPROVED",
                "scope": f"wt/{NEW_JOB}@{scope_sha}",
                "produced_at": "2026-10-02T10:00:00Z",
                **fields,
            }
        ),
    )


def _refusal(root: Path, result: subprocess.CompletedProcess[str], kind: str, head: str) -> None:
    """The merge refused with exactly the one `fix:` line of *kind*, and nothing landed."""
    dispatch = (f"fix: Agent action: dispatch dd-code-reviewer on {root / TREE} at HEAD {head};"
                " its verdict.py run writes the verdict")  # fmt: skip
    validate = f"fix: {command(*cli_argv(venv_dir(root)), 'reports', 'validate', '--all')}"
    got = fixes(result)
    want = [validate] if kind == VALIDATE_ALL else [dispatch]
    assert result.returncode == 1 and got == want, result.stderr
    assert git(root / "repos/r", "rev-parse", f"wt/{RC}").strip() != head


@pytest.mark.parametrize(
    ("kind", "fields"),
    [
        pytest.param(VALIDATE_ALL, "hand", id="hand-form"),
        pytest.param(DISPATCH, "no-hash", id="no-diff-sha256"),
        pytest.param(DISPATCH, "other-range", id="other-range-hash"),
        pytest.param(VALIDATE_ALL, "outside", id="reviewed-sha-outside"),
    ],
)  # fmt: skip
def test_a_verdict_that_does_not_bind_the_diff_it_lands_refuses(
    root: Path, kind: str, fields: str
) -> None:
    first = land(root, "src/a.py")
    head = land(root, "src/b.py")
    body = {
        "hand": {},
        "no-hash": {"reviewed_sha": head},
        "other-range": {"reviewed_sha": head, "diff_sha256": diff_hash(root, first, NEW_JOB)},
        "outside": {  # scope names HEAD; the bound sha is the work branch tip, outside the job's range
            "reviewed_sha": git(root / "repos/r", "rev-parse", "feature/0.5.0").strip(),
            "diff_sha256": diff_hash(root, head, NEW_JOB),
        },
    }[fields]
    _hand(root, head, **body)
    _refusal(root, run(root, "merge", TREE), kind, head)


def test_hash_prints_the_binding_a_verdict_carries(root: Path) -> None:
    head = land(root, "src/a.py")
    printed = run(root, "hash", TREE, "--sha", head)
    assert printed.returncode == 0, printed.stderr
    out = json.loads(printed.stdout)
    assert {k: out.get(k) for k in ("scope", "reviewed_sha", "diff_sha256")} == {
        "scope": f"wt/{NEW_JOB}@{head}",
        "reviewed_sha": head,
        "diff_sha256": diff_hash(root, head, NEW_JOB),
    }


def test_hash_refuses_an_unknown_sha_and_a_path_that_is_not_our_worktree(root: Path) -> None:
    head = land(root, "src/a.py")
    unknown = run(root, "hash", TREE, "--sha", "0" * 40)
    assert unknown.returncode == 1 and "0" * 40 in unknown.stderr
    stray = run(root, "hash", "repos/r", "--sha", head)
    assert stray.returncode == 1 and stray.stderr == run(root, "merge", "repos/r").stderr != ""


def test_a_stale_sha_named_by_a_verdict_refuses_for_review(root: Path) -> None:
    old = land(root, "src/a.py")
    head = land(root, "src/b.py")
    approve(root, old, name=NEW_JOB)  # bound, but to the sha a later commit left behind
    _refusal(root, run(root, "merge", TREE), VALIDATE_ALL, head)


def test_a_same_patch_rebase_over_other_blobs_refuses_with_the_dispatch_line(root: Path) -> None:
    rc, tree = root / "worktrees/r" / RC, root / TREE
    text = "".join(f"l{i}\n" for i in range(30))
    commit(rc, "src/a.py", text)
    git(tree, "rebase", "-q", f"wt/{RC}")
    approve(root, commit(tree, "src/a.py", text.replace("l0\n", "top\n", 1)), name=NEW_JOB)
    commit(rc, "src/a.py", text.replace("l29\n", "bottom\n", 1))  # the rc branch moved, same file
    git(tree, "rebase", "-q", f"wt/{RC}")  # the same patch, other blobs
    head = git(tree, "rev-parse", "HEAD").strip()  # read before the merge removes the tree
    _refusal(root, run(root, "merge", TREE), DISPATCH, head)


def test_a_commit_that_changes_the_diff_after_the_review_refuses(root: Path) -> None:
    approve(root, land(root, "src/a.py"), name=NEW_JOB)
    head = commit(root / TREE, "src/b.py")
    _refusal(root, run(root, "merge", TREE), VALIDATE_ALL, head)


def test_a_matching_verdict_tied_with_a_forged_one_refuses(root: Path) -> None:
    first = land(root, "src/a.py")
    head = land(root, "src/b.py")
    approve(root, head, name=NEW_JOB)
    _hand(root, head, reviewed_sha=head, diff_sha256=diff_hash(root, first, NEW_JOB))  # same moment
    _refusal(root, run(root, "merge", TREE), DISPATCH, head)


def test_a_bound_approval_of_head_lands(root: Path) -> None:
    head = land(root, "src/a.py")
    approve(root, head, name=NEW_JOB)
    landed = run(root, "merge", TREE)
    assert landed.returncode == 0, landed.stderr
    assert git(root / "repos/r", "rev-parse", f"wt/{RC}").strip() == head


@pytest.mark.parametrize("verdict", ["missing", "rejected", "other-sha", "other-diff"])
def test_a_plain_name_is_refused_as_not_a_worktree_name_whatever_the_verdict(
    root: Path, verdict: str
) -> None:
    repo = root / "repos/r"
    base = git(repo, "rev-parse", "HEAD").strip()
    head = land(root, "src/a.py")
    if verdict == "rejected":
        approve(root, head, verdict="REJECTED")
    elif verdict == "other-sha":
        _hand(root, head, reviewed_sha=base, diff_sha256=diff_hash(root, head, NEW_JOB))
    elif verdict == "other-diff":
        _hand(root, head, reviewed_sha=head, diff_sha256=diff_hash(root, base, NEW_JOB))

    refused = run(root, "new", "r", "maintenance")

    assert refused.returncode == 1
    assert "[error] not a worktree name" in refused.stderr
    assert fixes(refused) == [f"fix: {shell_line(sys.executable, str(SCRIPT))} list"]
    assert not (root / "worktrees/r/maintenance").exists()
    assert git(repo, "rev-parse", "feature/0.5.0").strip() == base
