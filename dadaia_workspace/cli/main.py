"""dadaia CLI entry point."""

import sys

import typer

from dadaia_workspace.cli.commands import (
    academy,
    ci,
    clean,
    context,
    doctor,
    init,
    lifecycle,
    lock,
    migrate,
    orchestrate,
    panel,
    public,
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
    bug_app,
    release_app,
)
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
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
app.add_typer(clean.app, name="clean")

# Sub-command groups
app.add_typer(context.app, name="context")
app.add_typer(lock.app, name="lock")
app.add_typer(lifecycle.app, name="lifecycle")
app.add_typer(ci.app, name="ci")
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
app.add_typer(bugs_app, name="bugs")


def _safe_app() -> None:
    """Entry point that captures unexpected exceptions and persists them before re-raising.

    Bug reports are written to the real workspace .dadaia/bugs/ — resolved dynamically
    via resolve_workspace_root() so they never land inside a sub-repo (T-017-02).
    Falls back to the platform temp dir on WorkspaceNotInitializedError (T-018-09:
    PLATFORM.tmp_dir, never a hardcoded /tmp — portable to Windows/macOS).
    """
    try:
        app()
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as exc:
        command = " ".join(sys.argv)
        try:
            workspace_root = resolve_workspace_root()
        except WorkspaceNotInitializedError:
            workspace_root = PLATFORM.tmp_dir / "dadaia-bugs"
        _report_exc(workspace_root, command, exc)
        raise  # re-raise so Typer still exits with error


if __name__ == "__main__":
    _safe_app()
