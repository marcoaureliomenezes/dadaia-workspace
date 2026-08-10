"""dadaia CLI entry point."""

import os
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


#: Values of ``DADAIA_TRACEBACK`` that do NOT enable the traceback opt-in, so an
#: exported-but-off variable cannot silently restore the old failure mode.
_TRACEBACK_OFF = frozenset({"", "0", "false", "no", "off"})


def _traceback_requested() -> bool:
    return os.environ.get("DADAIA_TRACEBACK", "").strip().lower() not in _TRACEBACK_OFF


def _safe_app() -> None:
    """Console entry point; failures surface without creating a second bug database.

    F-22 — "no CLI verb ever emits a raw traceback" — is enforced here as a **boundary**,
    not a whitelist. A DadaiaError is a known, operator-facing condition (uninitialized
    workspace, unknown context, …) and renders as one concise line
    (bug doctor-uninitialized-workspace-traceback). Anything else is a *defect*, and it
    renders as one concise line too, naming the exception type so it can be reported.

    Catching only DadaiaError was the earlier design, and it made the contract depend on
    every raise in the package being inside that hierarchy — ~138 are not. The contract
    then leaked one verb at a time (WorkspaceVenvBootstrapError, then a dangling
    DADAIA_BOOTSTRAP_PACKAGE; bug f22-cli-boundary-is-a-whitelist-not-a-boundary), because
    a whitelist is maintained by discipline. A boundary cannot leak.

    Debuggability is not traded away: ``DADAIA_TRACEBACK=1`` re-raises untouched, and it
    applies to EVERY failure — including a ``DadaiaError``. Honouring the opt-in only for
    unexpected exceptions made the escape hatch disappear the moment a specific failure was
    (correctly) moved into the DadaiaError hierarchy, which is exactly how a developer
    debugging a misfiring DadaiaError loses the traceback they need
    (bug r6a-traceback-escape-hatch-suppressed, reported by the consumer-side validator).
    ``SystemExit`` and ``KeyboardInterrupt`` derive from ``BaseException``, so Click's
    normal exits and Ctrl-C pass through this handler unchanged.
    """
    try:
        app()
    except DadaiaError as exc:
        if _traceback_requested():
            raise
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    except Exception as exc:
        if _traceback_requested():
            raise
        print(f"Error: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        print(
            "This is a dadaia-workspace defect — please report it. "
            "Re-run with DADAIA_TRACEBACK=1 for the full traceback.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    _safe_app()
