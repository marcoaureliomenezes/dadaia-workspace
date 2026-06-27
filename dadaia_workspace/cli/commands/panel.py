"""dadaia panel — local workspace UI served at http://127.0.0.1:<port>/."""

from __future__ import annotations

import logging
import sqlite3
import sys
import webbrowser
from pathlib import Path
from typing import Any

import typer

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import PlatformSecurityError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.server import build_panel_http_server

_LOOPBACK_ONLY: frozenset[str] = frozenset({"127.0.0.1"})

logger = logging.getLogger(__name__)

app = typer.Typer(help="Start the Dadaia Workspace Panel (local UI).")


def _try_build_telemetry(workspace_root: Path) -> object | None:
    """Best-effort TelemetryService construction for the panel boot.

    Returns a TelemetryService instance if all dependencies can be wired,
    or None if telemetry is unavailable (e.g. running as root, missing
    state directory, etc.).  The panel starts regardless — telemetry
    endpoints degrade to 503 when this returns None.
    """
    try:
        import pathlib

        from dadaia_workspace.features.telemetry import pricing as _pricing
        from dadaia_workspace.features.telemetry.aggregator.queries import TelemetryAggregator
        from dadaia_workspace.features.telemetry.reader import claude as _claude_reader
        from dadaia_workspace.features.telemetry.reader import codex as _codex_reader
        from dadaia_workspace.features.telemetry.reader import pi as _pi_reader
        from dadaia_workspace.features.telemetry.service import TelemetryService
        from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
        from dadaia_workspace.features.telemetry.store.schema import apply_migrations

        state_dir = pathlib.Path("~/.dadaia/state/telemetry").expanduser()
        state_dir.mkdir(parents=True, exist_ok=True)

        def _dao_factory() -> TelemetryDao:
            db_path = state_dir / "telemetry.sqlite"
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
            apply_migrations(conn)
            return TelemetryDao(conn)

        # We need a SpecContextService for context resolution.
        spec_context = container.build_spec_context_service(workspace_root)

        aggregator = TelemetryAggregator(
            dao=_dao_factory(),
            spec_context_service=spec_context,
            pricing_module=_pricing,
            workspace_root=workspace_root,
        )

        def _reader_factory() -> tuple[Any, ...]:
            return (_claude_reader, _codex_reader, _pi_reader)

        return TelemetryService(
            dao_factory=_dao_factory,
            aggregator=aggregator,
            reader_factory=_reader_factory,
            pricing_module=_pricing,
            workspace_root=workspace_root,
            state_dir=state_dir,
            spec_context_service=spec_context,
        )
    except ImportError as exc:
        logger.warning("Telemetry unavailable (missing dependency): %s", exc)
        return None
    except PermissionError as exc:
        logger.warning("Telemetry unavailable (permission denied on telemetry state dir): %s", exc)
        return None
    except PlatformSecurityError as exc:
        # Tier-2: telemetry dir permission restriction failed on this platform.
        # The panel continues without telemetry (503 on telemetry endpoints).
        logger.warning(
            "Telemetry unavailable (platform security error restricting state dir): %s", exc
        )
        return None
    except OSError as exc:
        logger.warning("Telemetry unavailable (OS error initialising telemetry state): %s", exc)
        return None
    except sqlite3.OperationalError as exc:
        logger.warning("Telemetry unavailable (SQLite database error): %s", exc)
        return None


@app.callback(invoke_without_command=True)
def panel(
    port: int = typer.Option(4999, "--port", help="HTTP port to bind"),
    no_open: bool = typer.Option(False, "--no-open", help="Skip automatic browser launch"),
    bind: str = typer.Option("127.0.0.1", "--bind", help="Bind address (loopback only)"),
) -> None:
    """Start the Dadaia Workspace Panel at http://<bind>:<port>/."""
    if bind not in _LOOPBACK_ONLY:
        typer.echo(
            f"Release-1 supports loopback bind only. Got: {bind}",
            err=True,
        )
        raise typer.Exit(2)

    workspace_root = resolve_workspace_root()

    # No authentication (operator decision 2026-06-11): the panel is a
    # loopback-only local dev tool.  No token is minted, no cookie, no launch
    # URL.  The handler's Host-header allowlist is the only residual guard
    # (DNS-rebinding protection — never a credential).

    # Build telemetry first so it can be injected into the panel service,
    # enabling the canonical agent overlay (PR3-08).
    telemetry = _try_build_telemetry(workspace_root)

    try:
        views = container.build_panel_views(workspace_root, telemetry=telemetry)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Failed to initialise panel: {exc}", err=True)
        raise typer.Exit(1) from None

    handler_cls = make_handler_class(
        views,
        telemetry=telemetry,
    )

    try:
        server = build_panel_http_server(host=bind, port=port, handler_factory=handler_cls)
    except OSError:
        typer.echo(
            f"Port {port} already in use. Find the holder with: lsof -i :{port}",
            err=True,
        )
        raise typer.Exit(1) from None

    # Install SIGINT/SIGTERM handlers (platform-appropriate) BEFORE announcing
    # readiness, otherwise a SIGINT arriving between the "Panel running at"
    # print and the serve_forever call would hit Python's default handler and
    # exit with code 130 (observed flake in CI; AC-9 requires clean exit 0).
    shutdown_handler = container.build_shutdown_handler()
    shutdown_handler.install(server)

    # Print the readiness banner.  No credential, no launch URL — the panel is
    # open without auth on loopback (operator decision 2026-06-11); the browser
    # opens the bare URL directly.
    typer.echo(f"Panel running at http://{bind}:{port}/")
    # Flush the readiness banner before entering the blocking serve loop. stdout
    # is block-buffered when piped (e.g. a supervising launcher or the e2e
    # harness); without this flush the line can sit in the buffer until the
    # process exits — which never happens under serve_forever — so any
    # readiness handoff over stdout would hang. Flush makes the handoff
    # deterministic.
    sys.stdout.flush()

    if not no_open:
        webbrowser.open(f"http://{bind}:{port}/")

    server.serve_forever()
    sys.exit(0)
