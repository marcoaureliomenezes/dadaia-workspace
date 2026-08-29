"""dadaia panel — local workspace UI served at http://127.0.0.1:<port>/."""

from __future__ import annotations

import contextlib
import logging
import sys
import webbrowser

import typer

from dadaia_workspace import container
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.server import build_panel_http_server

_LOOPBACK_ONLY: frozenset[str] = frozenset({"127.0.0.1"})

logger = logging.getLogger(__name__)

app = typer.Typer(help="Start the Dadaia Workspace Panel (local UI).")


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

    # Telemetry composition is plain wiring in the container (K8 — the
    # composition root, not a nested-class factory) so it can be injected
    # into the panel service, enabling the canonical agent overlay (PR3-08).
    telemetry = container.build_telemetry_service(workspace_root)

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
    # dev-server-registry law (validation-027 F-13): the panel is a dev server, so it
    # registers its own port and releases it on clean shutdown. Registry I/O never
    # blocks the panel — failures are logged, not fatal.
    registry = None
    try:
        registry = container.build_server_registry_service(workspace_root)
        registry.register(
            port,
            "dadaia-panel",
            url=f"http://{bind}:{port}",
            description="Dadaia Workspace Panel",
        )
    except Exception as exc:  # noqa: BLE001 - advisory registration only
        logger.warning("panel port registration failed: %s", exc)
        registry = None

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

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if registry is not None:
            with contextlib.suppress(Exception):
                registry.release(port, "dadaia-panel")
    sys.exit(0)
