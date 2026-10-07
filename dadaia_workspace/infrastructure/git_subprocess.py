"""GitSubprocessClient — git operations via stdlib subprocess."""

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

from dadaia_workspace.core.cli_line import fix_line, git_line
from dadaia_workspace.core.exceptions import GitCloneError, GitSyncError
from dadaia_workspace.core.gitflow import DEFAULT, Gitflow, read_gitflow
from dadaia_workspace.core.models.git_scan import GitObjectReadError
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
    environ = {**os.environ, **env} if env else None
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, input=stdin, env=environ)


def _commit(path: Path, msg: str, pathspec: Sequence[str] | None = None) -> None:
    """Run ``git commit`` against whatever is currently staged in *path*.

    ``commit_paths``'s commit; git's own identity rule applies, never a fallback identity
    (:meth:`GitSubprocessClient.identity_fix` is the one probe). When *pathspec* is given (``commit_paths``, v0.4.3
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
    covers, and is deliberately left as a follow-up rather than half-landed here.
    """
    commit_cmd = ["git", "commit", "-m", msg]
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

        Bug context-alive-sweeps-unrelated-worktree-changes (MEDIUM): callers that
        must commit only the files THEY themselves just wrote (e.g. the ``context
        alive`` scaffold commit) use this, never a blanket stage, so pre-existing
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

    def unpushed(self, path: Path, rev: str = "HEAD") -> bool:
        """Whether *rev* carries a commit origin lacks — the ONE rule, ``unpublished``."""
        try:
            return bool(unpublished(path, rev))
        except GitObjectReadError:
            return True

    def unrecoverable(self, path: Path) -> list[str]:
        """One fix line per thing removing *path* loses: a linked worktree, or a local
        branch carrying a commit neither origin nor HEAD holds — archived on origin as
        ``archive/<branch>/<sha7>`` (ADR 0120: a tag push is never gated on branch policy),
        the push recording it under ``refs/remotes/origin/`` so ``unpushed`` sees origin hold
        it until a ``fetch --prune`` drops it (re-running the line restores it); commits with
        no remote; a stash entry, which lives only in this checkout."""
        if self.has_commits(path) and not self.has_remote(path):
            return [f"Operator action: add the clone URL of {path} as its origin remote"]
        run = _run(["git", "worktree", "list", "--porcelain"], cwd=path).stdout.split("\n")
        trees = [line[9:] for line in run if line.startswith("worktree ")][1:]
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
        stdout, else ``GitSyncError`` carrying git's full output (CONFLICT is on stdout)."""
        result = _run(["git", *args], cwd=path, stdin=stdin, env=env)
        if result.returncode != 0:
            output = f"{result.stdout}\n{result.stderr}".strip()
            raise GitSyncError(f"git {args[0]} failed in {path}:\n{output}")
        return result.stdout.strip()

    def gitflow(self, repo: Path, main_repo: Path | None = None) -> tuple[Gitflow, str | None]:
        """ADR 0048 — the ONE gitflow reader (the gate, ``baseline``, ``dead``, onboarding):
        the constitution committed at HEAD, else the newest on a local branch or on origin,
        else — an associated repo — its *main_repo*'s; never a working tree; else DEFAULT
        plus the warning."""
        text = self.committed_text(repo, "specs/constitution.md")
        if text is None and main_repo is not None and main_repo.resolve() != repo.resolve():
            return self.gitflow(main_repo)
        if text is None:
            return DEFAULT, (
                f"{repo}: no specs/constitution.md — using the default gitflow\n"
                f"fix: {fix_line(None, 'specs', 'init', '--specs-dir', str(repo / 'specs'))}"
            )
        return read_gitflow(repo / "specs", text)

    def published(self, path: Path) -> bool:
        """Whether the project is published (local, offline, AC4.1): ``origin/<integration>``
        of the committed gitflow exists and ``specs/constitution.md`` is on origin."""
        ref = f"refs/remotes/origin/{self.gitflow(path)[0].integration}"
        born = _run(["git", "rev-parse", "-q", "--verify", ref], cwd=path)
        rel = "specs/constitution.md"
        result = _run(["git", "log", "--remotes=origin", "-n1", "--format=%H", "--", rel], cwd=path)
        return born.returncode == 0 and bool(result.stdout.strip())

    def committed_text(self, path: Path, rel: str) -> str | None:
        """*rel* at HEAD, else at the newest commit touching it on a local branch or an
        ``origin`` remote-tracking ref — never another remote's (ADR 0048: local,
        offline); ``None`` when none carries it (``-C``: *path* may not exist)."""
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
