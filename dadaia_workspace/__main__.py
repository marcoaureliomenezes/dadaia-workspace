"""Allow running dadaia_workspace as a module: python -m dadaia_workspace."""

from dadaia_workspace.cli.main import _safe_app

if __name__ == "__main__":
    _safe_app()
