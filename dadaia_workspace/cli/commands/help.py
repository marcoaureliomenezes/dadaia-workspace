"""CLI command group: `dadaia help <verb>` — derived help surfaces."""

from __future__ import annotations

import typer

from dadaia_workspace.cli._fail import fail
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.platform import act
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

app = typer.Typer(help="Derived help surfaces (docker-style; generated, never transcribed).")


@app.command(
    name="tree",
    epilog=f"Examples:\n\n{fix_line(None)} help tree\n\n{fix_line(None)} help tree --digest",
)
def tree(
    digest: bool = typer.Option(
        False,
        "--digest",
        help="Write the version-stamped digest under .dadaia/agentic/ and print its path.",
    ),
) -> None:
    """Print the compact CLI digest derived from the live command tree.

    The digest is the ONE derived map of the command surface (~4k-token budget);
    `--help` on any group remains the authoritative detail. With `--digest`, the
    rendered text is also written to `.dadaia/agentic/help-digest.md`, where
    ctx-inject attaches it to every session bootstrap.
    """
    from dadaia_workspace.cli.help_digest import render_digest, write_digest

    if digest:
        path = write_digest(resolve_workspace_root())
        if path is None:
            fail(
                "digest could not be written",
                act(
                    "agent", "make .dadaia/agentic writable by the current user, then run it again"
                ),
            )
        typer.echo(f"[ok] digest written: {path}")
    typer.echo(render_digest(), nl=False)
