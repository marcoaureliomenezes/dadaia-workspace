"""dadaia plugin subcommands — install and inspect distributed plugin packs (v0.1.60 FR2).

The Layer-1 entry surface for the in-package plugin packs (``frontend-design``, ``devops``).
``install`` validates a pack against the packaged descriptors, records it in the
``.dadaia/states/installed_plugins.json`` ledger via the ``JsonPluginStore`` adapter, and
calls the :func:`_project_pack` seam. In **W1** projection is a documented no-op — the real
profile-scoped projection + precedence lands in W2 (T-60-20, ``infrastructure/public_assets.py``).

Ports-and-adapters (v0.1.58 precedent): the pure ``PluginPack``/``InstalledPlugins`` core
models + the ``PluginStore`` port + the ``JsonPluginStore`` JSON adapter keep all I/O out of
``core``. This CLI is the only place the packaged descriptors are read from disk.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

import dadaia_workspace
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.models.plugin_pack import InstalledPlugins, PluginPack
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore

app = typer.Typer(help="Install and inspect distributed plugin packs.")
console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Packaged-descriptor discovery (in-package, offline-safe)
# ---------------------------------------------------------------------------


def _packs_root() -> Path:
    """The packaged plugin-pack root: ``dadaia_workspace/public/plugins/``."""
    return Path(dadaia_workspace.__file__).parent / "public" / "plugins"


def _available_packs() -> dict[str, PluginPack]:
    """Discover the in-package plugin packs by parsing each ``<pack>/pack.json`` descriptor.

    A malformed descriptor raises ``ValueError`` (via :meth:`PluginPack.from_dict`) rather than
    being silently skipped — a broken pack must surface, not vanish from the available set.
    """
    root = _packs_root()
    packs: dict[str, PluginPack] = {}
    if not root.is_dir():
        return packs
    for pack_dir in sorted(entry for entry in root.iterdir() if entry.is_dir()):
        descriptor = pack_dir / "pack.json"
        if not descriptor.is_file():
            continue
        data = json.loads(descriptor.read_text(encoding="utf-8"))
        pack = PluginPack.from_dict(data)
        packs[pack.name] = pack
    return packs


def _states_dir() -> Path:
    """Resolve the active workspace's ``.dadaia/states/`` directory.

    Raises ``typer.Exit(3)`` with a clean message when no initialized workspace is found —
    matching the ``dadaia reports`` uninitialized-workspace convention.
    """
    try:
        return resolve_workspace_root() / ".dadaia" / "states"
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(3) from None


def _read_ledger(states_dir: Path) -> InstalledPlugins:
    """Read the installed-plugins ledger, defaulting to the empty ledger when absent."""
    return JsonPluginStore().read(states_dir) or InstalledPlugins.empty()


def _project_pack(workspace_root: Path, pack: PluginPack, force: bool) -> list[str]:
    """Project a pack's agents/skills/rules into the runtime projections.

    **W1 SEAM (no-op).** In v0.1.60 W1 the ``dadaia plugin`` machinery only validates a pack
    and records the ledger; the actual profile-scoped projection + stub replacement +
    projection precedence lands in **W2 (T-60-20)**, wired through
    ``infrastructure/public_assets.py``. This function is the single, greppable call site W2
    fleshes out — it deliberately returns no projected lines today so the W1 CLI stays
    unit-cheap and byte-neutral (golden (a) is unaffected).
    """
    return []


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def install(
    pack: str = typer.Argument(..., help="Plugin pack to install (e.g. frontend-design, devops)."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing projected files."),
) -> None:
    """Enable a distributed plugin pack in this workspace.

    Validates *pack* against the in-package descriptors (an unknown pack is a Click
    ``BadParameter`` — exit 2, message on stderr, empty stdout), records it in
    ``installed_plugins.json`` (idempotent — a re-install is a no-op), and projects it
    (W2). Pack-name validation runs BEFORE workspace resolution so a bad value is always a
    clean exit-2 regardless of workspace state.
    """
    available = _available_packs()
    if pack not in available:
        names = ", ".join(sorted(available)) or "(none)"
        raise typer.BadParameter(
            f"unknown plugin pack '{pack}'. Available packs: {names}",
            param_hint="PACK",
        )

    states_dir = _states_dir()
    workspace_root = states_dir.parent.parent
    resolved = available[pack]

    ledger = _read_ledger(states_dir)
    already_installed = pack in ledger.plugins
    JsonPluginStore().write(states_dir, ledger.with_added(pack))

    _project_pack(workspace_root, resolved, force)

    if already_installed:
        console.print(f"[dim]Plugin pack '{pack}' is already installed — no change.[/dim]")
    else:
        agents = ", ".join(resolved.agents)
        console.print(f"[green]✓[/green] Plugin pack '{pack}' installed (agents: {agents}).")


@app.command(name="list")
def list_packs() -> None:
    """List available in-package plugin packs and which are installed in this workspace."""
    available = _available_packs()
    installed = set(_read_ledger(_states_dir()).plugins)

    if not available:
        console.print("[dim]No plugin packs are distributed in this build.[/dim]")
        return

    for name in sorted(available):
        pack = available[name]
        status = "[installed]" if name in installed else "[available]"
        agents = ", ".join(pack.agents)
        console.print(f"{status} {name} — agents: {agents}", markup=False)


@app.command()
def doctor() -> None:
    """Report the descriptor status of each installed plugin pack.

    W1 surfaces whether each installed pack still resolves to a packaged descriptor; the
    per-projected-file drift/missing reporting lands in W2 (T-60-20).
    """
    available = _available_packs()
    installed = _read_ledger(_states_dir()).plugins

    if not installed:
        console.print("[not-applicable] no plugin packs installed", markup=False)
        return

    for name in installed:
        if name in available:
            console.print(f"[ok] plugin:{name} (descriptor present)", style="green", markup=False)
        else:
            console.print(
                f"[missing] plugin:{name} (descriptor absent from this build)",
                style="yellow",
                markup=False,
            )
