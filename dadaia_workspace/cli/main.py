"""dadaia CLI entry point."""

import os
import sys

import typer

from dadaia_workspace.cli._fail import print_error
from dadaia_workspace.cli.commands import (
    capabilities,
    certify,
    ci,
    context,
    doctor,
    harness,
    init,
    migrate,
    public,
    reconcile,
    reports,
    specs,
)
from dadaia_workspace.cli.commands import (
    help as help_cmd,
)
from dadaia_workspace.cli.commands.export import export
from dadaia_workspace.cli.commands.import_ import import_workspace
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.infrastructure.provider_version import provider_version

app = typer.Typer(
    name="dadaia",
    help="AI-native workspace management with Spec Context Projects.",
    no_args_is_help=True,
    # A DadaiaError (e.g. WorkspaceNotInitializedError from a verb run outside an
    # initialized workspace) is an EXPECTED operator-facing condition, not a crash. Let it
    # propagate out of app() so _safe_app renders a concise message instead of a Rich
    # traceback. Genuinely unexpected
    # exceptions still surface their traceback for debugging.
    pretty_exceptions_enable=False,
)


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
        typer.echo(f"dadaia-workspace {provider_version() or '0+source'}")
        raise typer.Exit(0)
    # Preserve no_args_is_help behavior: bare `dadaia` prints help and exits.
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


# Top-level commands
app.command(name="init", rich_help_panel="Management")(init.init)
app.command(name="export", rich_help_panel="Management")(export)
app.command(name="import", rich_help_panel="Management")(import_workspace)
app.command(name="capabilities", rich_help_panel="Management")(capabilities.capabilities)
app.command(name="certify", rich_help_panel="Management")(certify.certify)
app.command(name="reconcile", rich_help_panel="Management")(reconcile.reconcile)

# Sub-command groups
app.add_typer(context.app, name="context", rich_help_panel="Common")
app.add_typer(ci.app, name="ci", rich_help_panel="Management")
app.add_typer(public.app, name="public", rich_help_panel="Common")
app.add_typer(harness.app, name="harness", rich_help_panel="Common")
app.add_typer(doctor.app, name="doctor", rich_help_panel="Common")
app.add_typer(reports.app, name="reports", rich_help_panel="Management")
app.add_typer(specs.app, name="specs", rich_help_panel="Common")
app.add_typer(migrate.app, name="migrate", rich_help_panel="Management")
app.add_typer(help_cmd.app, name="help", rich_help_panel="Common")


#: Values of ``DADAIA_TRACEBACK`` that do NOT enable the traceback opt-in, so an
#: exported-but-off variable cannot silently enable the traceback.
_TRACEBACK_OFF = frozenset({"", "0", "false", "no", "off"})


def _traceback_requested() -> bool:
    return os.environ.get("DADAIA_TRACEBACK", "").strip().lower() not in _TRACEBACK_OFF


def _safe_app() -> None:
    """Console entry point: every failure is one concise line, never a raw traceback.

    A ``DadaiaError`` prints as an operator-facing line and exits 1. Any other exception
    is a defect: one line naming its type, exit 1. ``DADAIA_TRACEBACK=1`` re-raises every
    failure untouched. ``SystemExit`` and ``KeyboardInterrupt`` derive from
    ``BaseException`` and pass through unchanged.
    """
    try:
        app()
    except DadaiaError as exc:
        if _traceback_requested():
            raise
        print_error(exc)
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
