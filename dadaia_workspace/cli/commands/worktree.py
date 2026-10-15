"""CLI command: `dadaia worktree <verb> …` — a runner of the installed `worktree.py`.

Verbs: new, merge, clean, list, preflight, sync, hash. The installed script owns every verb
and every refusal; this command forwards argv, stdout, stderr and the exit code.
"""

from __future__ import annotations

import sys

import typer

from dadaia_workspace.cli._fail import fail
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.infrastructure import ledger_scripts
from dadaia_workspace.infrastructure.subprocess_runner import SubprocessProcessRunner


def worktree(
    args: list[str] = typer.Argument(
        None, metavar="VERB [ARGS]...", help="Verb and its arguments."
    ),
) -> None:
    """Run a worktree verb of the installed dd-gitflow-default `worktree.py`.

    Verbs: new, merge, clean, list, preflight, sync, hash.
    """
    root = ledger_scripts.own_workspace_root()
    script = ledger_scripts.resolve_script(ledger_scripts.WORKTREE_SCRIPT, root) if root else None
    if script is None:
        fail("worktree.py is not installed", fix=fix_line(None, "public", "install"))
    result = SubprocessProcessRunner().run([sys.executable, str(script), *(args or [])])
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    raise typer.Exit(result.returncode)
