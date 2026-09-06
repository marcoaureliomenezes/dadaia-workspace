"""dadaia reports subcommands — validate handoff sidecars and diagnose their artifact links."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import HandoffSchemaError, WorkspaceNotInitializedError
from dadaia_workspace.core.handoff_index import Handoff, ValidationResult, scan_handoffs
from dadaia_workspace.core.workspace_resolver import (
    resolve_cli_workspace_root,
    resolve_workspace_root,
)

app = typer.Typer(help="Validate and diagnose agent handoff reports.")
console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# validate subcommand
# ---------------------------------------------------------------------------


@app.command(name="validate")
def validate(
    paths: list[Path] | None = typer.Argument(
        default=None, help="Paths to .handoff.json files to validate."
    ),
    all_: bool = typer.Option(
        False, "--all", help="Validate all *.handoff.json files under the workspace handoff root."
    ),
    release: str | None = typer.Option(
        None,
        "--release",
        help="Filter to a specific release ID (matches against handoff release_id field).",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON output instead of human-readable text."
    ),
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help=(
            "Explicit workspace root to validate against, bypassing cwd-based "
            "ancestor-walk resolution. Use when the target handoff/artifact lives in a "
            "workspace other than the one containing cwd (e.g. a throwaway/nested "
            "workspace) — otherwise artifact.path resolves against the wrong root."
        ),
    ),
    reviewed_root: Path | None = typer.Option(
        None,
        "--reviewed-root",
        help=(
            "Resolve self_pull.refs against THIS filesystem root first (e.g. a linked "
            "worktree checked out at the commit a verdict was authored/reviewed against), "
            "before the ordinary repos/<context>/<ref> and <workspace>/<ref> candidates. "
            "Fixes a false 'ref does not exist' when validating a handoff whose "
            "self_pull.refs were resolved against a tree other than whatever "
            "repos/<context> currently has checked out on disk."
        ),
    ),
) -> None:
    """Validate one or more agent handoff JSON files.

    \b
    Exit codes:
      0  All files valid
      1  One or more INVALID files
      2  One or more file paths not found
      3  Bad invocation (no paths and not --all) or workspace not initialized

    \b
    Examples:
      dadaia reports validate path/to/report.handoff.json
      dadaia reports validate --all
      dadaia reports validate --all
      dadaia reports validate --all --json
      dadaia reports validate path/to/report.handoff.json --workspace /path/to/other/ws
      dadaia reports validate path/to/verdict.handoff.json --reviewed-root /path/to/worktree
    """
    # Invocation guard: must have paths or --all
    if not paths and not all_:
        err_console.print("[red]Error:[/red] provide one or more PATHS or use [bold]--all[/bold].")
        raise typer.Exit(3)

    try:
        workspace_root = resolve_cli_workspace_root(workspace)
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(3) from None

    # Bug ancestor-walk-workspace-root-silent-mistarget (T-043-47/A30.5): always name
    # the resolved workspace root (stderr — never pollutes --json's stdout list shape)
    # so a false INVALID/missing_artifact caused by resolving against the wrong
    # ancestor is never silently misread. --workspace above is the primary fix; this
    # diagnostic covers every invocation, including the cwd-default path.
    err_console.print(f"[dim]Resolved workspace root: {workspace_root}[/dim]")

    index = container.build_handoff_index(workspace_root)

    # Collect paths to validate
    target_paths: list[Path] = []
    if all_:
        results_root = workspace_root / ".dadaia" / "handoff"
        target_paths = sorted(results_root.rglob("*.handoff.json")) if results_root.exists() else []
    elif paths:
        missing = [p for p in paths if not p.exists()]
        if missing:
            for m in missing:
                err_console.print(f"[red]Error:[/red] File not found: {m}")
            raise typer.Exit(2)
        target_paths = list(paths)

    # Version routing (v1/v1.1/v1.2, and refusal of any future/unknown token) lives in
    # the schema's own ``schema_version`` enum now — Handoff.validate applies ONE
    # validation path for every schema_version, never a second ad-hoc detector here.
    try:
        results: list[ValidationResult] = [
            index.validate_file(p, reviewed_root=reviewed_root) for p in target_paths
        ]
    except HandoffSchemaError as exc:
        err_console.print(
            f"[red]Error:[/red] Could not load handoff schema: {exc}\n"
            "Run [bold]dadaia public stage && dadaia public install --target all[/bold] first."
        )
        raise typer.Exit(3) from None

    # Apply release filter if requested
    if release:
        filtered: list[ValidationResult] = []
        for r in results:
            if r.valid:
                if Handoff.load(r.path).release_id == release:
                    filtered.append(r)
            else:
                filtered.append(r)
        results = filtered

    # Output
    n_valid = sum(1 for r in results if r.valid)
    n_invalid = len(results) - n_valid

    if json_output:
        payload = [
            {
                "path": str(r.path),
                "valid": r.valid,
                "errors": [{"field_path": e.field_path, "message": e.message} for e in r.errors],
                "hash_status": r.hash_status,
            }
            for r in results
        ]
        console.print_json(data=payload)
    else:
        for r in results:
            if r.valid:
                console.print(f"[green]VALID[/green]   {r.path}")
            else:
                console.print(f"[red]INVALID[/red] {r.path}")
                for err in r.errors:
                    console.print(f"         [yellow]{err.field_path}[/yellow]: {err.message}")

        console.print(
            f"\nSummary: [green]{n_valid} valid[/green], [red]{n_invalid} invalid[/red] "
            f"(of {len(results)} files)"
        )

    # Exit-code truthfulness (validation-029 F-12): an INVALID file is a hard failure
    # — printing INVALID while exiting 0 masked tampered/malformed handoffs from every
    # consuming script.
    if n_invalid > 0:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# doctor subcommand (T-PANEL-02)
# ---------------------------------------------------------------------------


@app.command(name="doctor")
def doctor(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of human-readable text."
    ),
) -> None:
    """Diagnose structural invariants in .dadaia/handoff/.

    \b
    Invariants checked:
      RPT-1: a declared handoff artifact.path must resolve to an existing .html file.

    \b
    Flags emitted:
      [dangling-artifact-path] <sidecar> → <artifact.path>  (RPT-1 violation)

    \b
    Exit codes:
      0  No issues found.
      1  One or more invariant violations detected.

    \b
    Examples:
      dadaia reports doctor
      dadaia reports doctor --json
    """
    workspace_root = resolve_workspace_root()
    handoff_root = workspace_root / ".dadaia" / "handoff"
    issues: list[dict[str, str | None]] = []
    for handoff in scan_handoffs(handoff_root):
        artifact_path_str = handoff.artifact_path_raw
        if not artifact_path_str:
            # No artifact.path declared — sidecar is valid (handoff-first emission).
            continue
        reason: str | None = None
        resolved = handoff.artifact_path(workspace_root)
        if resolved is None:
            reason = "path traversal or boundary escape detected"
        elif not resolved.exists():
            reason = "file does not exist"
        elif resolved.suffix.lower() != ".html":
            reason = f"not an .html file — got {resolved.suffix!r}"
        if reason is not None:
            issues.append(
                {
                    "code": "RPT-1",
                    "message": (
                        f"[dangling-artifact-path] {handoff.path} → {artifact_path_str!r} "
                        f"({reason})"
                    ),
                    "sidecar_path": str(handoff.path),
                    "artifact_path": artifact_path_str,
                }
            )

    if json_output:
        typer.echo(
            _json.dumps(
                {
                    "ok": not issues,
                    "issue_count": len(issues),
                    "issues": issues,
                }
            )
        )
        raise typer.Exit(0 if not issues else 1)

    if not issues:
        console.print("[green]OK[/green] No RPT-1 issues found.")
        raise typer.Exit(0)

    for issue in issues:
        console.print(f"[red]{issue['code']}[/red] {issue['message']}", markup=False)
    console.print(f"\n{len(issues)} issue(s) found.")
    raise typer.Exit(1)
