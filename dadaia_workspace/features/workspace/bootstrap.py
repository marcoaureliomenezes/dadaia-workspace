"""The first repo of a workspace — `dadaia init <dir> --harness <n> --repo <url>`.

`init --repo` is a CALLER of the context lifecycle, never a second copy of it: the clone
is `SpecContextService.alive`'s own clone (the ONE clone implementation, the one that
already refuses `ext::`/option-injection URLs), the registration is `create`, and the
binding is `core.session_store`'s record author. Nothing here re-implements any of them —
the two lifecycle entry points arrive as parameters, the same "everything it needs is a
parameter" discipline that let `push_gate_decision`/`pre_commit_decision` drop their
cross-feature imports.

Idempotence contract: re-running the identical command is a no-op that exits 0. Every
step below is already idempotent on its own — `alive` re-confirms rather than re-clones,
the hooks are copied over themselves, the binding is one record per session id — except
registration, which refuses a name it already holds. So an existing context whose main
repo url is the one asked for is REUSED; one whose url differs still raises
`ContextAlreadyExistsError`, because that is a genuine name collision. This is what makes
the `fix:` line a failed run prints truthful: the same command, run again once the url is
reachable, succeeds.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import session_store, workspace_layout
from dadaia_workspace.core.exceptions import ContextAlreadyExistsError, InvalidContextNameError

#: A repo slug is a directory name under ``repos/`` — never a traversal, never an option.
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def slug_from_url(url: str) -> str:
    """The directory name ``repos/<slug>`` a clone URL lands in.

    The URL's last path segment minus a trailing ``.git``. Validated as a plain
    directory name (CWE-22): a segment that is not one is refused here, before any
    path is built from it.
    """
    tail = url.rstrip("/").replace("\\", "/").rsplit("/", 1)[-1]
    slug = tail[: -len(".git")] if tail.endswith(".git") else tail
    if not _SLUG_RE.match(slug):
        raise InvalidContextNameError(
            f"cannot derive a repo directory name from '{url}': "
            f"'{slug}' is not a plain directory name."
        )
    return slug


def install_git_hooks(repo_root: Path, *, force: bool = False) -> list[Path]:
    """Copy every ``workspace_layout.INSTALLED_GIT_HOOKS`` row into ``<repo>/.git/hooks``.

    The ONE git-chokepoint installer — `dadaia ci install-hook` and the `init --repo`
    bootstrap are both callers. Raises :class:`FileNotFoundError` when *repo_root* is
    not a git repository and :class:`FileExistsError` for an installed hook the caller
    did not ask to overwrite; nothing is written in either case.
    """
    hooks_dir = repo_root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        raise FileNotFoundError(f"{hooks_dir} not found (is this a git repository?)")
    scripts = workspace_layout.public_scripts_dir()
    planned = [
        (hooks_dir / target, scripts / source)
        for target, source in workspace_layout.INSTALLED_GIT_HOOKS
    ]
    for dest, _ in planned:
        if dest.exists() and not force:
            raise FileExistsError(str(dest))
    for dest, source in planned:
        shutil.copyfile(source, dest)
        dest.chmod(0o755)
    return [dest for dest, _ in planned]


def bootstrap_repo(
    workspace_root: Path,
    repo_url: str,
    *,
    session_id: str,
    create_context: Callable[[str, str, str], object],
    main_repo_url: Callable[[str], str],
    alive_context: Callable[[str], object],
) -> tuple[str, tuple[str, str]]:
    """Make *repo_url* this workspace's first project; return its slug and env lines.

    Order is load-bearing: register (`create_context`, which validates the name and the
    slug before writing anything) -> `alive_context` (clone + specs scaffold) -> the
    pre-push chokepoint on the tree that now exists -> the session binding. A failure at
    any step raises and the later steps never run.

    Re-entrant per the module's idempotence contract: the one branch below reuses a
    context already registered for THIS url and lets any other collision propagate.
    """
    slug = slug_from_url(repo_url)
    try:
        create_context(slug, slug, repo_url)
    except ContextAlreadyExistsError:
        if main_repo_url(slug) != repo_url:
            raise
    alive_context(slug)
    install_git_hooks(workspace_root / "repos" / slug, force=True)
    session_store.write_session(
        workspace_root,
        session_id,
        session_store.new_binding_record(
            session_id=session_id,
            context=slug,
            runtime=os.environ.get("DADAIA_RUNTIME", "unknown"),
            pid=os.getpid(),
            now=datetime.now(tz=UTC).isoformat(),
        ),
    )
    return slug, session_store.binding_env_lines(slug, session_id)
