"""GitSubprocessClient — git operations via stdlib subprocess."""

import subprocess
from collections.abc import Sequence
from pathlib import Path

from dadaia_workspace.core.cli_line import fix_line, git_line
from dadaia_workspace.core.exceptions import GitCloneError, GitSyncError
from dadaia_workspace.core.gitflow import DEFAULT, Gitflow, read_gitflow
from dadaia_workspace.core.models.git_scan import GitObjectReadError
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.infrastructure.git_objects import unpublished

#: A lost branch's archive-tag push, also recording it under ``refs/remotes/origin/archive/``.
_ARCHIVE_PUSH = (
    "-c",
    "remote.origin.fetch=+refs/tags/archive/*:refs/remotes/origin/archive/*",
    "push",
    "origin",
)


def _run(
    args: list[str],
    cwd: Path | None = None,
    stdin: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        input=stdin,
        env={**load_owner("dd-bug-resolution", "_git").scrubbed_env(), **(env or {})},
    )


def _commit(path: Path, msg: str, pathspec: Sequence[str] | None = None) -> None:
    """Run ``git commit`` against whatever is currently staged in *path*.

    Git's own identity rule applies; no fallback identity is supplied
    (:meth:`GitSubprocessClient.identity_fix` is the one probe). When *pathspec* is
    given, the commit is scoped with a trailing ``-- <pathspec>``: only the changes
    matching *pathspec* are committed, and anything else staged stays staged.

    CWE-367: ``git commit -- <pathspec>`` commits the working-tree contents of the named
    paths at commit time, not necessarily the bytes ``git add`` staged earlier in
    ``commit_paths``. A concurrent writer could change one of those files in between;
    every caller passes paths it has just written, with no yield point in between.
    """
    commit_cmd = ["git", "commit", "-m", msg]
    if pathspec:
        commit_cmd += ["--", *pathspec]
    result = _run(commit_cmd, cwd=path)

    # An empty stdout and stderr with a non-zero exit is a silent no-op (submodule
    # edge case); both streams go in the error message.
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
        result = _run(["git", "clone", "-c", "core.longpaths=true", url, str(dest)])
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

    def dirty_paths(self, path: Path) -> list[str]:
        """Repo-relative paths ``git status`` reports — changed, staged or untracked (not
        ignored), each file once; a rename names its new path."""
        out = _run(["git", "status", "--porcelain", "-z", "--untracked-files=all"], cwd=path)
        entries, paths = iter(out.stdout.split("\0")), []
        for entry in entries:
            if entry:
                paths.append(entry[3:])
                if entry[0] in "RC":
                    next(entries, None)  # the rename's source
        return paths

    def has_commits(self, path: Path) -> bool:
        """Return whether the repository has a valid HEAD commit."""
        result = _run(["git", "rev-parse", "--verify", "HEAD"], cwd=path)
        return result.returncode == 0

    def commit_paths(self, path: Path, msg: str, paths: Sequence[str]) -> None:
        """Stage and commit exactly *paths* — never a blanket ``-A``/``-u`` sweep.

        Stage and commit exactly *paths*, never a blanket stage, so unrelated worktree
        modifications stay untouched and uncommitted. A no-op when *paths* is empty.

        Raises :class:`GitSyncError` when ``git add`` exits non-zero. The commit is
        path-scoped, so already-staged content outside *paths* stays out of it. Each path
        is wrapped in the ``:(literal)`` pathspec magic: a pathspec-magic character in a
        name is staged as the literal file it names, never read as a glob.
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

    def unpushed(self, path: Path, rev: str = "HEAD") -> bool:
        """Whether *rev* carries a commit origin lacks — the ONE rule, ``unpublished``."""
        try:
            return bool(unpublished(path, rev))
        except GitObjectReadError:
            return True

    def unrecoverable(self, path: Path) -> list[str]:
        """One fix line per thing removing *path* loses: a linked worktree, or a local
        branch carrying a commit neither origin nor HEAD holds — archived on origin as
        ``archive/<branch>/<sha7>`` (a tag push is never gated on branch policy),
        the push recording it under ``refs/remotes/origin/`` so ``unpushed`` sees origin hold
        it until a ``fetch --prune`` drops it (re-running the line restores it); commits with
        no remote; a stash entry, which lives only in this checkout."""
        if self.has_commits(path) and not self.has_remote(path):
            return [f"Operator action: add the clone URL of {path} as its origin remote"]
        listed = _run(["git", "worktree", "list", "--porcelain"], cwd=path).stdout
        trees = [
            t["worktree"] for t in load_owner("dd-bug-resolution", "_git").parse_worktrees(listed)
        ]
        refs = ["git", "for-each-ref", "--format=%(objectname) %(refname:short)", "refs/heads"]
        heads = [line.split(" ", 1) for line in _run(refs, cwd=path).stdout.split("\n") if line]
        in_head = ["git", "merge-base", "--is-ancestor"]  # HEAD itself is pushed by dead()
        lost = [
            (s, b)
            for s, b in heads
            if _run([*in_head, f"refs/heads/{b}", "HEAD"], cwd=path).returncode != 0
            and self.unpushed(path, f"refs/heads/{b}")
        ]
        stashes = _run(["git", "stash", "list"], cwd=path).stdout.count("\n")
        stash = f"Operator action: pop or drop the {stashes} stash entry(ies) of {path}"
        return (
            [git_line(path, "worktree", "remove", t) for t in trees]
            + [
                git_line(path, *_ARCHIVE_PUSH, f"{b}:refs/tags/archive/{b}/{s[:7]}")
                for s, b in lost
            ]
            + ([stash] if stashes else [])
        )

    def identity_fix(self, path: Path) -> str:
        """The ONE identity probe — git's own rule (env, config, auto-detection): ``""``
        when git resolves an author and a committer, else the operator action setting one."""
        for ident in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
            if _run(["git", "var", ident], cwd=path).returncode != 0:
                named = _run(["git", "config", "user.name"], cwd=path).stdout.strip()
                key = "user.email" if named else "user.name"
                return f"Operator action: set git {key} in the config of {path}"
        return ""

    def push(self, path: Path) -> None:
        """Publish HEAD's unpushed commits: on its upstream by the explicit refspec
        ``HEAD:<upstream-branch>`` (``push.default=simple`` refuses a differently named
        upstream), else ``-u origin <branch>``; nothing unpushed, nothing run."""
        if not self.unpushed(path):
            return
        tracking = _run(["git", "rev-parse", "--abbrev-ref", "@{u}"], cwd=path)
        if tracking.returncode != 0:
            self.git(path, "push", "-u", "origin", self.current_branch(path))
        else:
            remote, _, remote_branch = tracking.stdout.strip().partition("/")
            self.git(path, "push", remote, f"HEAD:{remote_branch}")

    def git(
        self, path: Path, *args: str, stdin: str | None = None, env: dict[str, str] | None = None
    ) -> str:
        """One git command in *path* (*env* over the process environment): its stripped
        stdout, else ``GitSyncError`` carrying git's full output (CONFLICT is on stdout); the
        first ``fix:`` line of that output becomes the error's ``fix``."""
        result = _run(["git", *args], cwd=path, stdin=stdin, env=env)
        if result.returncode != 0:
            lines = f"{result.stdout}\n{result.stderr}".strip().splitlines()
            fix = next((ln[5:] for ln in lines if ln.startswith("fix: ")), "")
            output = "\n".join(ln for ln in lines if not (fix and ln == f"fix: {fix}"))
            raise GitSyncError(f"git {args[0]} failed in {path}:\n{output}", fix=fix)
        return result.stdout.strip()

    def gitflow(self, repo: Path, main_repo: Path | None = None) -> tuple[Gitflow, str | None]:
        """Read the gitflow of *repo*: the constitution committed at HEAD, else the newest
        on a local branch or on origin, else (an associated repo) that of *main_repo*;
        never a working tree. Falls back to DEFAULT with a warning."""
        text = self.committed_text(repo, "specs/constitution.md")
        if text is None and main_repo is not None and main_repo.resolve() != repo.resolve():
            return self.gitflow(main_repo)
        if text is None:
            return DEFAULT, (
                f"{repo}: no specs/constitution.md — using the default gitflow\n"
                f"hint: {fix_line(None, 'specs', 'init', '--specs-dir', str(repo / 'specs'))}"
            )
        return read_gitflow(repo / "specs", text)

    def published(self, path: Path) -> bool:
        """Whether the project is published: ``origin/<integration>`` of the committed
        gitflow exists and ``specs/constitution.md`` is on origin. Offline; reads refs only."""
        ref = f"refs/remotes/origin/{self.gitflow(path)[0].integration}"
        born = _run(["git", "rev-parse", "-q", "--verify", ref], cwd=path)
        rel = "specs/constitution.md"
        result = _run(["git", "log", "--remotes=origin", "-n1", "--format=%H", "--", rel], cwd=path)
        return born.returncode == 0 and bool(result.stdout.strip())

    def committed_text(self, path: Path, rel: str) -> str | None:
        """*rel* at HEAD, else at the newest commit touching it on a local branch or an
        ``origin`` remote-tracking ref, never another remote's. Offline. ``None`` when
        none carries it (*path* may not exist)."""
        git = ["git", "-C", str(path)]
        newest = _run(
            [*git, "log", "--branches", "--remotes=origin", "-n1", "--format=%H", "--", rel]
        )
        for rev in ("HEAD", newest.stdout.strip()):
            shown = _run([*git, "show", f"{rev}:{rel}"])
            if rev and shown.returncode == 0:
                return shown.stdout
        return None

    def principal(self, path: Path) -> str:
        """``origin/HEAD``; unset or the integration branch: ``master`` when origin has it,
        else ``DEFAULT.principal`` (``-C``: *path* may not exist yet)."""
        ref = _run(["git", "-C", str(path), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
        if (head := ref.stdout.strip().removeprefix("origin/")) not in ("", DEFAULT.integration):
            return head
        master = _run(["git", "-C", str(path), "rev-parse", "-q", "--verify", "origin/master"])
        return "master" if master.returncode == 0 else DEFAULT.principal

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
        result = _run(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=path)
        return [rel for rel in result.stdout.split("\0") if rel]

    def tracked(self, path: Path) -> frozenset[str]:
        """Tracked plus untracked-unignored paths under *path*, *path*-relative; empty outside a repo."""
        result = _run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=path
        )
        return frozenset(rel for rel in result.stdout.split("\0") if rel)

    def remote_url(self, path: Path) -> str:
        """Return the URL of the ``origin`` remote, or ``""`` if none is configured.

        Returns the empty string on any failure (no remote, not a repo) and never raises.
        """
        result = _run(["git", "remote", "get-url", "origin"], cwd=path)
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
