"""dadaia harness subcommands — the roster of record for agent runtimes.

`harness add <name>` is the ONE way a harness enters a workspace after `init`:
it stages, projects that record's set, and registers the name in
`.dadaia/states/harness_profile.json` through `JsonHarnessProfileStore.write`,
the single writer. `public install` then reads that roster instead of a flag —
there is no `--target` and no second roster.
"""

from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core.harness_registry import HARNESS_RECORDS, L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore

app = typer.Typer(help="Register and inspect the workspace's agent runtimes (harnesses).")
console = Console()


def _states_dir(workspace_root: Path) -> Path:
    return workspace_root / ".dadaia" / "states"


@app.command("add")
def add(name: str = typer.Argument(..., help=f"One of: {', '.join(L1_ENTRY_HARNESSES)}")) -> None:
    """Register a harness and project its runtime set into this workspace.

    Stages the packaged assets, installs the named record's projection, then appends
    the name to the harness profile. Idempotent: re-adding a registered harness
    re-projects the same bytes and leaves the profile untouched.
    """
    if name not in HARNESS_RECORDS:
        raise typer.BadParameter(
            f"unknown harness {name!r}; registered harnesses: {', '.join(L1_ENTRY_HARNESSES)}",
            param_hint="HARNESS",
        )

    workspace_root = resolve_workspace_root()
    svc = container.build_public_service()
    svc.stage(workspace_root)
    installed = svc.install(workspace_root, target=name)

    states_dir = _states_dir(workspace_root)
    store = JsonHarnessProfileStore()
    registered = store.resolve(states_dir, workspace_root).harnesses
    store.write(states_dir, HarnessProfile.of(_with(registered, name)))

    console.print(f"[green]✓[/green] {name} registered — {len(installed)} asset(s) projected:")
    for item in installed:
        console.print(f"  {item}", markup=False)


@app.command("list")
def list_harnesses(
    as_json: bool = typer.Option(False, "--json", help="Emit the roster as JSON."),
) -> None:
    """Show the harnesses registered in this workspace's profile.

    The profile is the roster of record: `public install` and `public doctor` both
    scope to exactly these names.
    """
    workspace_root = resolve_workspace_root()
    harnesses = JsonHarnessProfileStore().resolve(_states_dir(workspace_root), workspace_root)
    if as_json:
        import json

        console.print_json(json.dumps({"harnesses": list(harnesses.harnesses)}))
        return
    for harness in harnesses.harnesses:
        console.print(harness, markup=False)


def _with(registered: tuple[str, ...], name: str) -> tuple[str, ...]:
    """*registered* plus *name*, in canonical registry order."""
    merged = set(registered) | {name}
    return tuple(h for h in L1_ENTRY_HARNESSES if h in merged) + tuple(
        sorted(merged - set(L1_ENTRY_HARNESSES))
    )
