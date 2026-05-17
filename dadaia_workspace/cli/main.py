"""dadaia CLI entry point."""

import typer

from dadaia_workspace.cli.commands import (
    academy,
    context,
    doctor,
    init,
    orchestrate,
    panel,
    public,
    repos,
    server,
    specs,
)
from dadaia_workspace.cli.commands.export import export
from dadaia_workspace.cli.commands.import_ import import_workspace

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
app.add_typer(specs.app, name="specs")
app.add_typer(server.app, name="server")
app.add_typer(panel.app, name="panel")


if __name__ == "__main__":
    app()
