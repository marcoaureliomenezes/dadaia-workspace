"""GitSubprocessClient — git operations via stdlib subprocess."""

import logging
import subprocess
from collections.abc import Sequence
from pathlib import Path

from dadaia_workspace.core.exceptions import GitCloneError, GitSyncError

logger = logging.getLogger(__name__)


def _run(
    args: list[str], cwd: Path | None = None, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, input=stdin)


def _has_embedded_git(directory: Path) -> bool:
    """Return True if *directory* is itself a git repository (contains .git)."""
    return (directory / ".git").exists()


def _stage_files_safe(path: Path) -> None:
    """Stage all changes while excluding embedded git repos.

    Problem: ``git add -A`` recurses into directories that contain their own
    ``.git`` directory (embedded repos, e.g. ``.claude/worktrees/agent-*``).
    This produces git warnings ("adding embedded git repository") and pollutes
    the outer repo's index.

    Fix strategy:
    1. Use ``git add -u`` to stage modifications/deletions to already-tracked files.
    2. Find untracked directories via ``git ls-files --others --directory``.
    3. For each untracked directory, skip it if it contains its own ``.git``.
    4. Add the remaining untracked entries individually.

    This is equivalent to ``git add -A`` but respects embedded repos.

    v0.4.3 T-043-23 security-review rework (FR10 sibling hardening — this seam
    carried NEITHER of A10.1/A10.3, the two `commit_paths`/`_commit` already
    applies): a non-zero exit from EITHER ``git add`` call now raises
    :class:`GitSyncError` (a stage that did not happen must never silently become
    part of a commit, matching A10.1), and every untracked path is wrapped in the
    ``:(literal)`` pathspec-magic escape before it reaches ``git add`` (matching
    A10.3) — an untracked file literally named e.g. ``:(exclude)specs`` is staged
    as the literal file it names, never reinterpreted as pathspec magic. The
    commit itself (``_commit(path, msg)``, no *pathspec*) is UNAFFECTED by the
    commit-vs-staged-worktree-content note documented on :func:`_commit` below —
    that note only applies when a *pathspec* is passed (``commit_paths``); a bare
    ``git commit -m <msg>`` (what `commit_all` issues) commits whatever the index
    holds at commit time, exactly what the two ``git add`` calls above just staged.
    """
    # Stage tracked-file changes (modifications + deletions)
    add_tracked = _run(["git", "add", "-u"], cwd=path)
    if add_tracked.returncode != 0:
        raise GitSyncError(f"git add -u failed in {path}: {add_tracked.stderr.strip()}")

    # Discover untracked items (files and dirs)
    result = _run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=path,
    )
    untracked: list[str] = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    safe: list[str] = []
    skipped: list[str] = []
    for item in untracked:
        # Paths ending with "/" are untracked directories
        full = path / item.rstrip("/")
        if full.is_dir() and _has_embedded_git(full):
            skipped.append(item)
        else:
            safe.append(item)

    if skipped:
        logger.debug(
            "commit_all: skipping %d embedded git repo(s) in %s: %s",
            len(skipped),
            path,
            skipped,
        )

    if safe:
        # git add accepts multiple paths; chunk to avoid ARG_MAX issues on
        # very large trees (practical repos are fine with a single call)
        literal_safe = [f":(literal){p}" for p in safe]
        add_untracked = _run(["git", "add", "--", *literal_safe], cwd=path)
        if add_untracked.returncode != 0:
            raise GitSyncError(
                f"git add failed in {path} for paths {safe!r}: {add_untracked.stderr.strip()}"
            )


def _commit(path: Path, msg: str, pathspec: Sequence[str] | None = None) -> None:
    """Run ``git commit`` against whatever is currently staged in *path*.

    Shared by ``commit_all`` (blanket staging) and ``commit_paths`` (explicit-path
    staging) — the staging strategy differs, the commit/identity-fallback/no-op
    handling does not. When *pathspec* is given (``commit_paths``, v0.4.3
    T-043-14/FR10/A10.2), the commit itself is scoped with a trailing ``-- <pathspec>``
    — this is what makes it honest even when the index carries OTHER staged content
    (operator pre-staged, or a concurrent caller): ``git commit -- <pathspec>`` commits
    only the changes matching *pathspec*, leaving everything else staged and untouched.

    CWE-367 (v0.4.3 T-043-23 security-review rework, LOW residual, documented rather
    than redesigned — see the handoff's own alternative resolution): ``git commit --
    <pathspec>`` is documented git behaviour (``git commit --help``, ``-o``/``--only``,
    "the DEFAULT mode of operation ... if any paths are given on the command line") to
    commit the UPDATED WORKING-TREE CONTENTS of the named paths at commit time, NOT
    necessarily the exact bytes ``git add`` staged a moment earlier in ``commit_paths``.
    Under the NO-LOCKS DOCTRINE a concurrent agent could, in principle, mutate one of
    *pathspec*'s files in the window between ``commit_paths``'s ``git add`` and this
    call, and the newer worktree content — not the reviewed/staged content — would be
    committed. Every current caller passes paths it JUST wrote itself, with no
    intervening yield point, so this is a theoretical race, not an observed defect; a
    fix that eliminated it entirely (a temporary index via ``GIT_INDEX_FILE`` or
    ``write-tree``/``commit-tree``) is a bigger design change than this hardening pass
    covers, and is deliberately left as a follow-up rather than half-landed here (the
    same commit-vs-staged distinction does NOT apply to a bare, no-*pathspec* call —
    ``commit_all``'s — which commits exactly what its own ``git add`` calls in
    :func:`_stage_files_safe` just staged).
    """
    # Tool-authored commits must not depend on an operator git identity being
    # configured (validation-029 F-06: containers/CI runners without user.email made
    # dead()'s auto-commit die with 'Please tell me who you are'). When no identity
    # resolves, fall back to a deterministic tool identity via -c overrides; a
    # configured identity always wins.
    commit_cmd = ["git"]
    identity = _run(["git", "config", "user.email"], cwd=path)
    if identity.returncode != 0 or not identity.stdout.strip():
        commit_cmd += [
            "-c",
            "user.name=dadaia-workspace",
            "-c",
            "user.email=dadaia@workspace.local",
        ]
    commit_cmd += ["commit", "-m", msg]
    if pathspec:
        commit_cmd += ["--", *pathspec]
    result = _run(commit_cmd, cwd=path)

    # Bug 2 fix: treat empty stdout+stderr with non-zero exit as silent
    # no-op (submodule edge case); include both streams in error message.
    if result.returncode != 0:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if "nothing to commit" in stdout:
            return  # normal no-op
        if not stdout and not stderr:
            return  # silent no-op (submodule edge case)
        raise GitSyncError(f"git commit failed in {path}. stdout: {stdout!r} stderr: {stderr!r}")


class GitSubprocessClient:
    def clone(self, url: str, dest: Path) -> None:
        # Block the two transports that turn a URL into code/option execution:
        # ``ext::`` runs an arbitrary helper (RCE) and a leading "-" can be parsed
        # by git as an option (argument injection). Legitimate https/ssh/git@ and
        # local-path / file:// clones are still allowed.
        if url.startswith("ext::") or url.startswith("-"):
            raise GitCloneError(f"refusing to clone from unsafe URL: {url!r}", url)
        result = _run(["git", "clone", url, str(dest)])
        if result.returncode != 0:
            raise GitCloneError(f"git clone failed for {url!r}: {result.stderr.strip()}", url)

    def move(self, repo: Path, src: str, dst: str) -> None:
        """Rename ``repo/src`` to ``repo/dst``, staging the rename of its tracked files —
        never committing. A tree git does not track is renamed on disk alone."""
        if not _run(["git", "ls-files", "--", src], cwd=repo).stdout.strip():
            (repo / src).rename(repo / dst)
            return
        result = _run(["git", "mv", "--", src, dst], cwd=repo)
        if result.returncode != 0:
            raise GitSyncError(f"git mv {src} {dst} failed in {repo}: {result.stderr.strip()}")

    def is_dirty(self, path: Path) -> bool:
        result = _run(["git", "status", "--porcelain"], cwd=path)
        return bool(result.stdout.strip())

    def has_commits(self, path: Path) -> bool:
        """Return whether the repository has a valid HEAD commit."""
        result = _run(["git", "rev-parse", "--verify", "HEAD"], cwd=path)
        return result.returncode == 0

    def commit_all(self, path: Path, msg: str) -> None:
        # Bug 1 fix: use safe staging that excludes embedded git repos
        _stage_files_safe(path)
        _commit(path, msg)

    def commit_paths(self, path: Path, msg: str, paths: Sequence[str]) -> None:
        """Stage and commit exactly *paths* — never a blanket ``-A``/``-u`` sweep.

        Bug context-alive-sweeps-unrelated-worktree-changes (MEDIUM): callers that
        must commit only the files THEY themselves just wrote (e.g. the ``context
        alive`` scaffold commit) use this instead of ``commit_all``, so pre-existing
        unrelated worktree modifications stay untouched and uncommitted. A no-op
        (nothing staged, nothing committed) when *paths* is empty.

        v0.4.3 T-043-14/FR10 hardening — honest by construction:

        - **A10.1** — a non-zero ``git add`` exit raises :class:`GitSyncError`; a stage
          that did not happen must never silently become (part of) a commit.
        - **A10.2** — the commit itself is path-scoped (``git commit -m <msg> --
          <paths>``, via ``_commit``'s *pathspec*), not a bare ``git commit``, so
          content the OPERATOR pre-staged (or any other already-staged content) is
          never swept into this commit even though it stays in the index.
        - **A10.3** — every path is wrapped in the literal pathspec-magic escape
          (``:(literal)<path>``, git's own defence per gitglossary(7) ``pathspec``):
          every *paths* entry this seam ever receives is a concrete repo-relative
          filename the caller itself just wrote (template names, scaffold files) —
          never an operator- or attacker-influenced glob — so a path that happens to
          contain a pathspec-magic character (``:``/``*``/``!``/``?``/…) is still
          staged and committed as the literal file it names, never reinterpreted as a
          glob or an exclude pattern.
        """
        if not paths:
            return
        literal_paths = [f":(literal){p}" for p in paths]
        add_result = _run(["git", "add", "--", *literal_paths], cwd=path)
        if add_result.returncode != 0:
            raise GitSyncError(
                f"git add failed in {path} for paths {list(paths)!r}: {add_result.stderr.strip()}"
            )
        _commit(path, msg, pathspec=literal_paths)

    def has_remote(self, path: Path) -> bool:
        result = _run(["git", "remote"], cwd=path)
        return bool(result.stdout.strip())

    def unpushed(self, path: Path) -> bool:
        """Whether :meth:`push` has anything to push: no upstream, or commits ahead of it."""
        ahead = _run(["git", "rev-list", "--count", "@{u}..HEAD"], cwd=path)
        return ahead.returncode != 0 or ahead.stdout.strip() != "0"

    def push(self, path: Path) -> None:
        # Bug 4 fix: detect whether an upstream tracking branch is configured.
        # If not, use ``git push -u origin <branch>`` to set it on first push.
        tracking = _run(["git", "rev-parse", "--abbrev-ref", "@{u}"], cwd=path)
        if tracking.returncode != 0:
            # No upstream tracking branch — set it during push
            branch = self.current_branch(path)
            result = _run(["git", "push", "-u", "origin", branch], cwd=path)
        else:
            # v0.1.50 FR3 (bug context-dead-plain-git-push-fails-mismatched-upstream):
            # skip entirely when there is nothing to push, and push with an EXPLICIT
            # refspec ``HEAD:<upstream-branch>`` — plain ``git push`` fails under
            # ``push.default=simple`` whenever the upstream branch name differs from
            # the local one.
            if not self.unpushed(path):
                return
            upstream = tracking.stdout.strip()  # e.g. "origin/main"
            remote, _, remote_branch = upstream.partition("/")
            result = _run(["git", "push", remote, f"HEAD:{remote_branch}"], cwd=path)

        if result.returncode != 0:
            raise GitSyncError(f"git push failed in {path}:\n{result.stderr.strip()}")

    def git(self, path: Path, *args: str, stdin: str | None = None) -> str:
        """One git command in *path*: its stripped stdout, else ``GitSyncError``."""
        result = _run(["git", *args], cwd=path, stdin=stdin)
        if result.returncode != 0:
            raise GitSyncError(f"git {args[0]} failed in {path}: {result.stderr.strip()}")
        return result.stdout.strip()

    def published(self, path: Path, integration: str) -> bool:
        """Whether the project is published (local, offline): ``origin/<integration>``
        exists and ``specs/constitution.md`` is reachable from a remote-tracking ref."""
        born = _run(
            ["git", "rev-parse", "-q", "--verify", f"refs/remotes/origin/{integration}"], cwd=path
        )
        rel = "specs/constitution.md"
        result = _run(["git", "log", "--remotes", "-n1", "--format=%H", "--", rel], cwd=path)
        return born.returncode == 0 and result.returncode == 0 and bool(result.stdout.strip())

    def committed_text(self, path: Path, rel: str) -> str | None:
        """*rel* at HEAD, else at the newest commit touching it on a local branch or an
        ``origin`` remote-tracking ref — never another remote's (ADR 0048: local,
        offline); ``None`` when none carries it."""
        newest = _run(
            ["git", "log", "--branches", "--remotes=origin", "-n1", "--format=%H", "--", rel],
            cwd=path,
        )
        for rev in ("HEAD", newest.stdout.strip()):
            shown = _run(["git", "show", f"{rev}:{rel}"], cwd=path)
            if rev and shown.returncode == 0:
                return shown.stdout
        return None

    def default_branch(self, path: Path) -> str:
        """The remote's default branch from the local ``origin/HEAD``; ``main`` when unset
        (``-C``: *path* may not exist yet)."""
        ref = _run(["git", "-C", str(path), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
        return ref.stdout.strip().removeprefix("origin/") if ref.returncode == 0 else "main"

    def current_branch(self, path: Path) -> str:
        result = _run(["git", "branch", "--show-current"], cwd=path)
        return result.stdout.strip()

    def checkout(self, path: Path, branch: str) -> None:
        result = _run(["git", "checkout", branch], cwd=path)
        if result.returncode != 0:
            raise GitSyncError(f"git checkout {branch!r} failed in {path}: {result.stderr.strip()}")

    def is_git_root(self, path: Path) -> bool:
        result = _run(["git", "rev-parse", "--show-toplevel"], cwd=path)
        if result.returncode != 0:
            return False
        return Path(result.stdout.strip()).resolve() == path.resolve()

    def list_untracked(self, path: Path) -> list[str]:
        """Return repo-relative paths of untracked, non-gitignored files.

        Uses ``git ls-files --others --exclude-standard`` so that ``.gitignore``
        is honoured (gitignored files are NOT returned). The result drives the
        ``dead()`` review gate: an untracked file here is content that would be
        newly committed and pushed, so it must be reviewed/scanned first. ``-z``: the
        real names, never core.quotePath's quoting.
        """
        result = _run(["git", "ls-files", "-z", "--others", "--exclude-standard"], cwd=path)
        return [rel for rel in result.stdout.split("\0") if rel]

    def remote_url(self, path: Path) -> str:
        """Return the URL of the ``origin`` remote, or ``""`` if none is configured.

        Drives the repo_url back-fill (FR-W2-03 / T-011-08): when a context record
        has an empty ``repo_url`` but the repo is on disk with an ``origin`` remote,
        ``alive``/``dead`` read the canonical URL straight from the repo. Returns
        the empty string on any failure (no remote, not a repo) so callers treat it
        as "nothing to back-fill" rather than raising.
        """
        result = _run(["git", "remote", "get-url", "origin"], cwd=path)
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
