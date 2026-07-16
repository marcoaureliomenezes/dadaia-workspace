"""dadaia CLI entry point."""

import sys

import typer

from dadaia_workspace.cli.commands import (
    academy,
    capabilities,
    certify,
    ci,
    clean,
    context,
    doctor,
    init,
    lifecycle,
    migrate,
    panel,
    plugin,
    public,
    reconcile,
    reports,
    repos,
    server,
    specs,
)
from dadaia_workspace.cli.commands.bugs import bugs_app
from dadaia_workspace.cli.commands.export import export
from dadaia_workspace.cli.commands.import_ import import_workspace
from dadaia_workspace.cli.commands.memory import app as memory_app
from dadaia_workspace.cli.commands.newartifacts import (
    backlog_app,
    release_app,
)
from dadaia_workspace.core.exceptions import DadaiaError

app = typer.Typer(
    name="dadaia",
    help="AI-native workspace management with Spec Context Projects.",
    no_args_is_help=True,
    # A DadaiaError (e.g. WorkspaceNotInitializedError from a verb run outside an
    # initialized workspace) is an EXPECTED operator-facing condition, not a crash. Let it
    # propagate out of app() so _safe_app renders a concise message instead of a Rich
    # traceback (bug doctor-uninitialized-workspace-traceback). Genuinely unexpected
    # exceptions still surface their traceback for debugging.
    pretty_exceptions_enable=False,
)


def _resolve_version() -> str:
    from importlib import metadata

    try:
        return metadata.version("dadaia-workspace")
    except metadata.PackageNotFoundError:
        return "0+source"


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show the installed dadaia-workspace version and exit.",
        is_eager=True,
    ),
) -> None:
    """Root callback: handles the top-level ``--version`` flag."""
    if version:
        typer.echo(f"dadaia-workspace {_resolve_version()}")
        raise typer.Exit(0)
    # Preserve no_args_is_help behavior: bare `dadaia` prints help and exits.
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


# Top-level commands
app.command(name="init")(init.init)
app.command(name="export")(export)
app.command(name="import")(import_workspace)
app.command(name="capabilities")(capabilities.capabilities)
app.command(name="certify")(certify.certify)
app.command(name="reconcile")(reconcile.reconcile)
app.add_typer(clean.app, name="clean")

# Sub-command groups
app.add_typer(context.app, name="context")
app.add_typer(lifecycle.app, name="lifecycle")
app.add_typer(ci.app, name="ci")
app.add_typer(repos.app, name="repos")
app.add_typer(public.app, name="public")
app.add_typer(doctor.app, name="doctor")
app.add_typer(academy.app, name="academy")
app.add_typer(plugin.app, name="plugin")
app.add_typer(reports.app, name="reports")
app.add_typer(specs.app, name="specs")
app.add_typer(server.app, name="server")
app.add_typer(migrate.app, name="migrate")
app.add_typer(panel.app, name="panel")
app.add_typer(memory_app, name="memory")
app.add_typer(release_app, name="release")
app.add_typer(backlog_app, name="backlog")
app.add_typer(bugs_app, name="bugs")


def _safe_app() -> None:
    """Console entry point; failures surface without creating a second bug database.

    A DadaiaError is a known, operator-facing condition (uninitialized workspace, unknown
    context, etc.) — surface it as one concise stderr line + a non-zero exit, never a
    traceback (bug doctor-uninitialized-workspace-traceback). Every other exception keeps
    its traceback for debugging.
    """
    try:
        app()
    except DadaiaError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    _safe_app()
