"""dadaia CLI entry point."""

import sys
from pathlib import Path

import typer

from dadaia_workspace.cli.commands import (
    academy,
    context,
    doctor,
    init,
    migrate,
    orchestrate,
    panel,
    public,
    reports,
    repos,
    server,
    specs,
)
from dadaia_workspace.cli.commands.export import export
from dadaia_workspace.cli.commands.import_ import import_workspace
from dadaia_workspace.cli.commands.memory import app as memory_app
from dadaia_workspace.cli.commands.newartifacts import (
    backlog_app,
    bug_app,
    release_app,
)
from dadaia_workspace.infrastructure.bug_reporter import report_exception as _report_exc

app = typer.Typer(
    name="dadaia",
    help="AI-native workspace management with Spec Context Projects.",
    no_args_is_help=True,
)

# Top-level commands
app.command(name="init")(init.init)
app.command(name="export")(export)
app.command(name="import")(import_workspace)

# Sub-command groups
app.add_typer(context.app, name="context")
app.add_typer(repos.app, name="repos")
app.add_typer(public.app, name="public")
app.add_typer(doctor.app, name="doctor")
app.add_typer(academy.app, name="academy")
app.add_typer(orchestrate.app, name="orchestrate")
app.add_typer(reports.app, name="reports")
app.add_typer(specs.app, name="specs")
app.add_typer(server.app, name="server")
app.add_typer(migrate.app, name="migrate")
app.add_typer(panel.app, name="panel")
app.add_typer(memory_app, name="memory")
app.add_typer(release_app, name="release")
app.add_typer(backlog_app, name="backlog")
app.add_typer(bug_app, name="bug")

# Workspace root resolved from the editable install location:
# cli/main.py → cli/ → dadaia_workspace/ → repos/dadaia-workspace/ → workspace root
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _safe_app() -> None:
    """Entry point that captures unexpected exceptions and persists them before re-raising."""
    try:
        app()
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as exc:
        command = " ".join(sys.argv)
        _report_exc(_WORKSPACE_ROOT, command, exc)
        raise  # re-raise so Typer still exits with error


if __name__ == "__main__":
    _safe_app()
