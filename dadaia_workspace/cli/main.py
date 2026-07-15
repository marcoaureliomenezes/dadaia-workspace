"""dadaia CLI entry point."""

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

app = typer.Typer(
    name="dadaia",
    help="AI-native workspace management with Spec Context Projects.",
    no_args_is_help=True,
)

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
    """Console entry point; failures surface without creating a second bug database."""
    app()


if __name__ == "__main__":
    _safe_app()
