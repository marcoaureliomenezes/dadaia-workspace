"""The ``reference-transaction`` hook on real git, work-branch side.

The shipped script is copied into a tmp repo with a bare origin, under a workspace-shaped
``.dadaia/.venv/bin/dadaia`` the hook resolves as in production. That runner executes this
tree's real ``ci ref-gate-check``; a second one exits non-zero, as a venv older than the hook.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import os
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import dadaia_workspace
from dadaia_workspace.core.cli_line import fix_line

pytestmark = pytest.mark.medium

_SCRIPT = Path(dadaia_workspace.__file__).parent / "public" / "scripts" / "reference-transaction.sh"
_SOURCE = Path(dadaia_workspace.__file__).parent.parent
_WORK = "feature/0.5.0"
_REAL = f"""#!/bin/sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={shlex.quote(str(_SOURCE))} exec {shlex.quote(sys.executable)} -m dadaia_workspace "$@"
"""


class _Repo:
    def __init__(self, root: Path) -> None:
        self.root = root / "ws" / "repo"
        self.origin = root / "origin.git"
        self.runner = root / "ws" / ".dadaia" / ".venv" / "bin" / "dadaia"

    def install_runner(self, text: str) -> None:
        self.runner.parent.mkdir(parents=True, exist_ok=True)
        self.runner.write_text(text, encoding="utf-8")
        self.runner.chmod(self.runner.stat().st_mode | stat.S_IXUSR)

    def git(
        self, *args: str, cwd: Path | None = None, wt: bool = False
    ) -> subprocess.CompletedProcess[str]:
        env = {k: v for k, v in os.environ.items() if k != "DADAIA_WT"}
        if wt:
            env["DADAIA_WT"] = "1"
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.root,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def ok(self, *args: str, cwd: Path | None = None) -> str:
        done = self.git(*args, cwd=cwd)
        assert done.returncode == 0, done.stderr
        return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> _Repo:
    r = _Repo(tmp_path)
    r.install_runner(_REAL)
    r.root.mkdir()
    r.ok("init", "-q", "--bare", str(r.origin), cwd=tmp_path)
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "test@example.invalid"],
        ["config", "user.name", "Test"],
        ["commit", "-q", "--allow-empty", "-m", "init"],
        ["remote", "add", "origin", str(r.origin)],
        ["checkout", "-q", "-b", _WORK],
        ["push", "-q", "-u", "origin", _WORK],
    ):
        r.ok(*args)
    # Installed last, as an installer would on an existing repo.
    assert _SCRIPT.is_file(), f"hook script missing: {_SCRIPT}"
    hook = r.root / ".git" / "hooks" / "reference-transaction"
    shutil.copy(_SCRIPT, hook)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    return r


def _other_ahead(r: _Repo) -> str:
    r.ok("checkout", "-q", "-b", "other")
    r.ok("commit", "-q", "--allow-empty", "-m", "elsewhere")
    sha = r.ok("rev-parse", "HEAD")
    r.ok("checkout", "-q", _WORK)
    return sha


def _assert_refused(r: _Repo, done: subprocess.CompletedProcess[str], before: str) -> None:
    assert done.returncode != 0
    assert "[ref-gate] BLOCKED" in done.stderr
    fixes = [ln for ln in done.stderr.splitlines() if "fix:" in ln]
    assert len(fixes) == 1, done.stderr
    assert fixes[0].startswith("fix: Agent action: "), fixes[0]
    assert fix_line(None, "worktree", "new", "repo") in fixes[0]
    assert r.ok("rev-parse", f"refs/heads/{_WORK}") == before


def test_raw_commit_on_the_work_branch_is_refused(repo: _Repo) -> None:
    before = repo.ok("rev-parse", "HEAD")
    done = repo.git("commit", "-q", "--allow-empty", "-m", "raw")
    _assert_refused(repo, done, before)


def test_raw_ff_merge_on_the_work_branch_is_refused(repo: _Repo) -> None:
    before = repo.ok("rev-parse", "HEAD")
    other = _other_ahead(repo)
    done = repo.git("merge", "--ff-only", other)
    _assert_refused(repo, done, before)


def test_raw_hard_reset_on_the_work_branch_is_refused(repo: _Repo) -> None:
    before = repo.ok("rev-parse", "HEAD")
    other = _other_ahead(repo)
    done = repo.git("reset", "--hard", other)
    _assert_refused(repo, done, before)


def test_raw_update_ref_without_an_old_sha_on_the_work_branch_is_refused(repo: _Repo) -> None:
    before = repo.ok("rev-parse", "HEAD")
    other = _other_ahead(repo)
    done = repo.git("update-ref", f"refs/heads/{_WORK}", other)
    _assert_refused(repo, done, before)


def test_raw_branch_force_move_of_the_work_branch_is_refused(repo: _Repo) -> None:
    before = repo.ok("rev-parse", "HEAD")
    other = _other_ahead(repo)
    repo.ok("checkout", "-q", "other")
    done = repo.git("branch", "-f", _WORK, other)
    _assert_refused(repo, done, before)


def test_pull_ff_only_from_origin_passes(repo: _Repo, tmp_path: Path) -> None:
    peer = tmp_path / "peer"
    repo.ok("clone", "-q", "-b", _WORK, str(repo.origin), str(peer), cwd=tmp_path)
    for args in (
        ["config", "user.email", "test@example.invalid"],
        ["config", "user.name", "Test"],
        ["commit", "-q", "--allow-empty", "-m", "from peer"],
        ["push", "-q", "origin", _WORK],
    ):
        repo.ok(*args, cwd=peer)
    pushed = repo.ok("rev-parse", "HEAD", cwd=peer)
    done = repo.git("pull", "-q", "--ff-only")
    assert done.returncode == 0, done.stderr
    assert repo.ok("rev-parse", f"refs/heads/{_WORK}") == pushed
    assert repo.ok("rev-parse", f"refs/remotes/origin/{_WORK}") == pushed


def test_branch_rename_passes(repo: _Repo) -> None:
    done = repo.git("branch", "-m", _WORK, "feature/0.5.1")
    assert done.returncode == 0, done.stderr


def test_a_marked_ff_merge_of_a_wt_branch_into_the_work_branch_passes(repo: _Repo) -> None:
    other = _other_ahead(repo)
    done = repo.git("merge", "-q", "--ff-only", other, wt=True)
    assert done.returncode == 0, done.stderr
    assert repo.ok("rev-parse", f"refs/heads/{_WORK}") == other


def test_an_audit_only_commit_on_the_work_branch_passes(repo: _Repo) -> None:
    audit = repo.root / "specs" / "audits"
    audit.mkdir(parents=True)
    (audit / "2026-10-14.md").write_text("finding\n", encoding="utf-8")
    repo.ok("add", "-A")
    done = repo.git("commit", "-q", "-m", "audit")
    assert done.returncode == 0, done.stderr


@pytest.mark.parametrize("code", [1, 2])
def test_a_runner_fault_warns_and_lets_the_commit_through(repo: _Repo, code: int) -> None:
    repo.install_runner(f"#!/bin/sh\necho boom >&2\nexit {code}\n")
    done = repo.git("commit", "-q", "--allow-empty", "-m", "on the work branch")
    assert done.returncode == 0, done.stderr
    assert "boom" in done.stderr
    assert "ref gate failed" in done.stderr


def _ahead_by_a_marked_merge(repo: _Repo) -> None:
    """The normal state between a worktree merge and the push: local is ahead of origin."""
    other = _other_ahead(repo)
    assert repo.git("merge", "-q", "--ff-only", other, wt=True).returncode == 0


def test_stash_and_hard_reset_pass_on_a_work_branch_ahead_of_origin(repo: _Repo) -> None:
    _ahead_by_a_marked_merge(repo)
    before = repo.ok("rev-parse", "HEAD")
    (repo.root / "f.txt").write_text("x\n", encoding="utf-8")
    repo.ok("add", "f.txt")
    stashed = repo.git("stash")
    assert stashed.returncode == 0, stashed.stderr
    reset = repo.git("reset", "--hard")
    assert reset.returncode == 0, reset.stderr
    assert repo.ok("rev-parse", "HEAD") == before


def test_a_raw_commit_is_still_refused_on_a_work_branch_ahead_of_origin(repo: _Repo) -> None:
    _ahead_by_a_marked_merge(repo)
    before = repo.ok("rev-parse", "HEAD")
    _assert_refused(repo, repo.git("commit", "-q", "--allow-empty", "-m", "raw"), before)


def _two_unpublished(repo: _Repo) -> None:
    for name in ("one", "two"):
        assert repo.git("commit", "-q", "--allow-empty", "-m", name, wt=True).returncode == 0


def _raw_branch_under_origin(repo: _Repo) -> str:
    """A branch off origin's tip holding one raw (unmarked, never merged) commit."""
    repo.ok("checkout", "-q", "-b", "raw", f"origin/{_WORK}")
    (repo.root / "raw.txt").write_text("raw\n", encoding="utf-8")
    repo.ok("add", "raw.txt")
    repo.ok("commit", "-q", "-m", "raw")
    sha = repo.ok("rev-parse", "HEAD")
    repo.ok("checkout", "-q", _WORK)
    return sha


def test_amending_the_unpublished_tip_is_refused(repo: _Repo) -> None:
    _ahead_by_a_marked_merge(repo)
    before = repo.ok("rev-parse", "HEAD")
    done = repo.git("commit", "-q", "--allow-empty", "--amend", "-m", "amended")
    _assert_refused(repo, done, before)


def test_an_amend_that_adds_content_is_refused(repo: _Repo) -> None:
    _ahead_by_a_marked_merge(repo)
    before = repo.ok("rev-parse", "HEAD")
    (repo.root / "added.txt").write_text("raw\n", encoding="utf-8")
    repo.ok("add", "added.txt")
    done = repo.git("commit", "-q", "--amend", "--no-edit")
    _assert_refused(repo, done, before)


def test_a_soft_reset_inside_the_unpublished_range_is_refused(repo: _Repo) -> None:
    _two_unpublished(repo)
    before = repo.ok("rev-parse", "HEAD")
    done = repo.git("reset", "--soft", "HEAD~1")
    _assert_refused(repo, done, before)


def test_a_hard_reset_onto_a_raw_branch_is_refused(repo: _Repo) -> None:
    _ahead_by_a_marked_merge(repo)
    before = repo.ok("rev-parse", "HEAD")
    raw = _raw_branch_under_origin(repo)
    done = repo.git("reset", "--hard", raw)
    _assert_refused(repo, done, before)


def test_a_rebase_under_a_raw_commit_is_refused(repo: _Repo) -> None:
    _ahead_by_a_marked_merge(repo)
    before = repo.ok("rev-parse", "HEAD")
    raw = _raw_branch_under_origin(repo)
    done = repo.git("rebase", raw)
    _assert_refused(repo, done, before)


_TERM = "zzprivateterm"


def _verb(
    repo: _Repo, oldest: str, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(repo.runner),
            "ci",
            "push-gate-check",
            "--repo",
            str(repo.root),
            "--rewrite-from",
            oldest,
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, **(env or {})},
    )


def _leak(repo: _Repo, tmp_path: Path, *, in_message: bool = False) -> tuple[str, dict[str, str]]:
    """One unpublished commit carrying the denylisted term (in a file, or only in its message);
    returns that commit and the env naming the denylist."""
    denylist = tmp_path / "denylist.json"
    denylist.write_text(f'{{"{_TERM}": "t"}}', encoding="utf-8")
    (repo.root / "leak.txt").write_text(f"a {'' if in_message else _TERM}\n", encoding="utf-8")
    repo.ok("add", "leak.txt")
    message = f"mentions {_TERM}" if in_message else "leak"
    assert repo.git("commit", "-q", "-m", message, wt=True).returncode == 0
    return repo.ok("rev-parse", "HEAD"), {"DADAIA_PRIVACY_DENYLIST": str(denylist)}


def _assert_verb_refused(repo: _Repo, done: subprocess.CompletedProcess[str], before: str) -> None:
    assert done.returncode != 0, done.stderr
    fixes = [ln for ln in done.stderr.splitlines() if ln.startswith("fix: ")]
    assert len(fixes) == 1 and fixes[0].startswith("fix: Agent action: "), done.stderr
    assert repo.ok("rev-parse", f"refs/heads/{_WORK}") == before


def test_the_rewrite_verb_refuses_unrelated_staged_content_when_the_gate_lists_nothing(
    repo: _Repo,
) -> None:
    _ahead_by_a_marked_merge(repo)
    before = repo.ok("rev-parse", "HEAD")
    (repo.root / "unreviewed.py").write_text("x = 1\n", encoding="utf-8")
    repo.ok("add", "unreviewed.py")
    done = _verb(repo, before, "--message", "looks reviewed")
    _assert_verb_refused(repo, done, before)
    assert "unreviewed.py" not in repo.ok("ls-tree", "-r", "--name-only", _WORK)


def test_the_rewrite_verb_refuses_a_remedy_that_also_adds_a_path(
    repo: _Repo, tmp_path: Path
) -> None:
    oldest, env = _leak(repo, tmp_path)
    (repo.root / "leak.txt").write_text("a\n", encoding="utf-8")
    (repo.root / "extra.txt").write_text("x\n", encoding="utf-8")
    repo.ok("add", "extra.txt")
    done = _verb(repo, oldest, env=env)
    _assert_verb_refused(repo, done, oldest)


def test_the_rewrite_verb_refuses_a_new_message_when_the_gate_lists_no_message(
    repo: _Repo, tmp_path: Path
) -> None:
    oldest, env = _leak(repo, tmp_path)
    (repo.root / "leak.txt").write_text("a\n", encoding="utf-8")
    done = _verb(repo, oldest, "--message", "looks reviewed", env=env)
    _assert_verb_refused(repo, done, oldest)


def test_the_rewrite_verb_removes_a_listed_term_and_clears_the_gate(
    repo: _Repo, tmp_path: Path
) -> None:
    oldest, env = _leak(repo, tmp_path)
    (repo.root / "leak.txt").write_text("a\n", encoding="utf-8")
    done = _verb(repo, oldest, env=env)
    assert done.returncode == 0, done.stderr
    assert repo.ok("rev-list", "--count", f"origin/{_WORK}..{_WORK}") == "1"
    assert _TERM not in repo.ok("show", f"{_WORK}:leak.txt")
    tip = repo.ok("rev-parse", _WORK)
    held = repo.ok("rev-parse", f"origin/{_WORK}")
    gate = subprocess.run(
        [str(repo.runner), "ci", "push-gate-check"],
        input=f"refs/heads/{_WORK} {tip} refs/heads/{_WORK} {held}\n",
        cwd=repo.root,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert gate.returncode == 0, gate.stderr


def test_the_rewrite_verb_takes_a_new_message_when_the_term_sits_in_the_message(
    repo: _Repo, tmp_path: Path
) -> None:
    oldest, env = _leak(repo, tmp_path, in_message=True)
    done = _verb(repo, oldest, "--message", "clean message", env=env)
    assert done.returncode == 0, done.stderr
    assert repo.ok("log", "-1", "--format=%s", _WORK) == "clean message"


def test_the_rewrite_verb_refuses_a_commit_origin_already_holds(
    repo: _Repo, tmp_path: Path
) -> None:
    _, env = _leak(repo, tmp_path)
    before = repo.ok("rev-parse", "HEAD")
    published = repo.ok("rev-parse", f"origin/{_WORK}")
    done = _verb(repo, published, env=env)
    _assert_verb_refused(repo, done, before)
