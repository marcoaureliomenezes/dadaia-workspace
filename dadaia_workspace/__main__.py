"""Allow running dadaia_workspace as a module: python -m dadaia_workspace."""

from dadaia_workspace.cli.main import app

if __name__ == "__main__":
    app()
