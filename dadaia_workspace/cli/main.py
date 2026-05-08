"""dadaia CLI entry point."""

import typer

from dadaia_workspace.cli.commands import context, init, public, repos

app = typer.Typer(
    name="dadaia",
    help="AI-native workspace management with Spec Context Projects.",
    no_args_is_help=True,
)

# Top-level init command
app.command(name="init")(init.init)

# Sub-command groups
app.add_typer(context.app, name="context")
app.add_typer(repos.app, name="repos")
app.add_typer(public.app, name="public")


if __name__ == "__main__":
    app()
