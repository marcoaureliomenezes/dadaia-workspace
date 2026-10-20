"""The object scan of an export bundle, matched by an injected matcher; each refusal has its fix."""

import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import NoReturn

from dadaia_workspace.core.cli_line import git_line
from dadaia_workspace.core.exceptions import DadaiaError, GitSyncError
from dadaia_workspace.core.models.git_scan import GitObjectReadError, GitRunError, ScannedObject
from dadaia_workspace.core.platform import act, write_text
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient


def scratch_fix(tmp: Path) -> str:
    """The act that clears a scratch directory or file that cannot be written under *tmp*."""
    return act("agent", f"free space and write permission under {tmp}, then rerun the export")


def new_scratch(tmp: Path, prefix: str) -> "tempfile.TemporaryDirectory[str]":
    """A scratch directory under *tmp*; a failure to make it refuses with the act that clears it."""
    try:
        tmp.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=tmp, prefix=prefix)
    except OSError as exc:
        raise DadaiaError(
            f"cannot create a scratch directory ({type(exc).__name__})",
            fix=scratch_fix(tmp),
        ) from exc


def scan_bundle(
    workspace_root: Path,
    bundle: Path,
    repo: Path,
    match: Callable[[Iterable[ScannedObject]], dict[str, str]],
    read_fix: Callable[[GitObjectReadError, Path], str],
) -> dict[str, str]:
    """*match* over the objects *bundle* adds to *repo*, as the push gate reads them: git's own exit statuses tell the cases apart (`list-heads` fails: a damaged header;
    `verify` fails: a missing prerequisite), a scratch bare repo borrows *repo*'s objects and
    `origin` refs, and the bundle is unbundled there. Nothing is written into *repo*.
    A failure raises `DadaiaError` relaying git's reason, with the act that clears its cause."""
    # An open lane's bundle was written a moment ago: its damage is git's, never the operator's.
    paused = bundle.is_relative_to(workspace_root / ".dadaia" / "dist")
    damaged = (
        act("operator", f"rule whether {bundle} is restored from a copy or discarded")
        if paused
        else git_line(repo, "fsck")
    )

    def refuse(why: str, fix: str) -> NoReturn:
        raise DadaiaError(f"{bundle.name} cannot be scanned ({why})", fix=fix)

    def git(cwd: Path, *args: str, why: str, fix: str) -> str:
        try:
            return GitSubprocessClient().git(cwd, *args)
        except GitSyncError as exc:
            refuse(f"{why}: {exc.message.partition(':\n')[2].strip()}", fix)
        except (OSError, TimeoutError):
            refuse("git could not run", read_fix(GitRunError("git"), repo))

    try:
        bundle.open("rb").close()
    except OSError as exc:
        refuse(
            type(exc).__name__, act("agent", f"make {bundle} readable, then run the export again")
        )
    heads = git(
        repo, "bundle", "list-heads", str(bundle), why="its header is unreadable", fix=damaged
    )
    if not heads:
        refuse("it holds no ref", damaged)
    git(
        repo,
        "bundle",
        "verify",
        str(bundle),
        why="its repo lacks a prerequisite",
        fix=git_line(repo, "fetch", "origin"),
    )
    tmp = workspace_root / ".dadaia" / "tmp"
    with new_scratch(tmp, "scan-") as name:
        scratch, fsck = Path(name), git_line(repo, "fsck")
        git(scratch, "init", "-q", "--bare", why="no scratch repo", fix=scratch_fix(tmp))
        store = git(
            repo,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "objects",
            why="no repo",
            fix=fsck,
        )
        try:
            write_text(scratch / "objects" / "info" / "alternates", store + "\n")
        except OSError as exc:
            refuse(type(exc).__name__, scratch_fix(tmp))
        git(
            scratch,
            "fetch",
            "-q",
            str(repo),
            "+refs/remotes/origin/*:refs/remotes/origin/*",
            why="no origin refs",
            fix=fsck,
        )
        # verify never reads the pack body: a failed unbundle is the file's if it is a pause bundle.
        unbundled = damaged if paused else scratch_fix(tmp)
        git(scratch, "bundle", "unbundle", str(bundle), why="git refused it", fix=unbundled)
        try:
            found = GitSubprocessObjectReader().new_objects(scratch, heads.split()[0], "")
            return match(found)
        except GitObjectReadError as exc:
            refuse(str(exc), read_fix(exc, repo))
