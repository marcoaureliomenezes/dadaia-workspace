"""CLI command: dadaia doctor [--fix] [--redact]."""

from pathlib import Path

import typer

from dadaia_workspace import container
from dadaia_workspace.cli._specs_resolution import resolve_context_for_cli
from dadaia_workspace.cli.redact import ContextRedactor
from dadaia_workspace.core.exceptions import SchemaVersionError, WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

app = typer.Typer(help="Diagnose and repair workspace state.")


err_console = typer.echo


def _resolve_caller_context_and_slug(workspace_root: Path) -> tuple[str | None, str | None]:
    """Best-effort resolution of the caller's own context name + repo slug (SPEC v0.9.0
    FR8a: "other than the caller's resolved context"). Never raises — an unresolved
    caller (no bind, no DADAIA_CONTEXT, cwd outside any repo) simply means nothing is
    excluded, so `--redact` masks every context/slug it encounters."""
    try:
        name = resolve_context_for_cli(None)
    except ValueError:
        return None, None
    slug: str | None = None
    try:
        for ctx in container.build_spec_context_service(workspace_root).list_all():
            if ctx.name == name:
                slug = ctx.repo_slug
                break
    except (WorkspaceNotInitializedError, SchemaVersionError):
        pass
    return name, slug


def _build_redactor(workspace_root: Path) -> ContextRedactor:
    """Candidates = every known registered context name/repo slug, PLUS every context
    name that appears in an advisory presence record (`[stale-presence] context
    '<name>'`, PRESENCE-GC) — a presence record can outlive its context's registry
    entry, so the registry alone is not enough to cover A8.1's PRESENCE-GC line."""
    from dadaia_workspace.features.spec_context import presence

    caller_name, caller_slug = _resolve_caller_context_and_slug(workspace_root)
    try:
        contexts = container.build_spec_context_service(workspace_root).list_all()
    except (WorkspaceNotInitializedError, SchemaVersionError):
        contexts = []
    candidates: list[str] = []
    for ctx in contexts:
        candidates.append(ctx.name)
        candidates.append(ctx.repo_slug)
    candidates.extend(ref.context for ref in presence.stale_records(workspace_root))
    return ContextRedactor(candidates, exclude=(caller_name, caller_slug))


@app.callback(invoke_without_command=True)
def doctor(
    fix: bool = typer.Option(False, "--fix", help="Apply automatic repairs."),
    redact: bool = typer.Option(
        False,
        "--redact",
        help=(
            "Mask every Spec Context name and repo slug other than this caller's "
            "resolved context (SPEC v0.9.0 FR8a). Default output is unchanged."
        ),
    ),
) -> None:
    """Diagnose workspace state invariants and optionally repair them."""
    workspace_root = resolve_workspace_root()
    try:
        dr = container.build_doctor_service(workspace_root)
    except WorkspaceNotInitializedError:
        typer.echo("Error: Workspace not initialized. Run 'dadaia init' first.", err=True)
        raise typer.Exit(1) from None

    issues = dr.check()

    # Render boundary ONLY: `dr` (DoctorService) never sees `redactor` and its issue
    # descriptions/fix actions keep carrying true names — nothing here mutates them.
    redactor = _build_redactor(workspace_root) if redact else None

    def _render(text: str) -> str:
        return redactor.text(text) if redactor is not None else text

    if not issues:
        typer.echo("All invariants OK — workspace is healthy.")
        return

    typer.echo(f"Found {len(issues)} issue(s):")
    for issue in issues:
        fixable = "[fixable]" if issue.fixable else "[manual]"
        typer.echo(f"  {issue.code} {fixable} — {_render(issue.description)}")

    if fix:
        actions = dr.fix()
        typer.echo(f"\nApplied {len(actions)} repair(s):")
        for action in actions:
            typer.echo(f"  - {_render(action)}")
        remaining = dr.check()
        if remaining:
            typer.echo(f"\n{len(remaining)} issue(s) remain after repairs.")
            raise typer.Exit(1)
    else:
        typer.echo("\nRun 'dadaia doctor --fix' to apply automatic repairs.")
        # Exit-code truthfulness (validation-029 F-04): issues found => non-zero, so
        # scripts and agents consuming doctor never mistake a sick tree for healthy.
        raise typer.Exit(1)
