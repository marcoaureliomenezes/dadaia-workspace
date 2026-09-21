"""The first repo of a workspace — `dadaia init <dir> --harness <n> --repo <url>`.

`init --repo` is a CALLER of the context lifecycle, never a second copy of it: the clone
is `SpecContextService.alive`'s own clone (the ONE clone implementation, the one that
already refuses `ext::`/option-injection URLs), the registration is `create`, and the
binding is `core.session_store`'s record author. Nothing here re-implements any of them —
the two lifecycle entry points arrive as parameters, the same "everything it needs is a
parameter" discipline that let `push_gate_decision`/`pre_commit_decision` drop their
cross-feature imports.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import session_store, workspace_layout
from dadaia_workspace.core.exceptions import InvalidContextNameError

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
    alive_context: Callable[[str], object],
) -> tuple[str, tuple[str, str]]:
    """Make *repo_url* this workspace's first project; return its slug and env lines.

    Order is load-bearing: register (`create_context`, which validates the name and the
    slug before writing anything) -> `alive_context` (clone + specs scaffold) -> the
    pre-push chokepoint on the tree that now exists -> the session binding. A failure at
    any step raises and the later steps never run.
    """
    slug = slug_from_url(repo_url)
    create_context(slug, slug, repo_url)
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
