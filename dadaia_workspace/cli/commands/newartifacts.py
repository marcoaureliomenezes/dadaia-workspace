"""CLI command groups: ``dadaia release``, ``dadaia backlog``, ``dadaia bug``.

Implements:
- dadaia release new <id>    → specs/releases/<id>/SPEC.md stub
- dadaia backlog new <slug>  → specs/backlog/<slug>.md stub
- dadaia bug new <slug>      → specs/bugs/<slug>.md stub (session_id: null)
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from dadaia_workspace.core.specs_resolver import resolve_specs_dir as _shared_resolve_specs_dir
from dadaia_workspace.features.spec_artifacts.new_artifacts import (
    backlog_new,
    bug_new,
    release_new,
)

# ── shared typer apps ─────────────────────────────────────────────────────────

release_app = typer.Typer(help="Release management commands.")
backlog_app = typer.Typer(help="Backlog entry management commands.")
bug_app = typer.Typer(help="Bug report management commands.")


# ── helper: resolve specs_dir ─────────────────────────────────────────────────


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory.

    Priority:
    1. Explicit ``--specs-dir`` argument.
    2. Bound context session (``DADAIA_CONTEXT`` or ``DADAIA_SESSION_ID``).
    3. ``<cwd>/specs`` fallback.
    """
    return _shared_resolve_specs_dir(specs_dir)


# ── dadaia release new ────────────────────────────────────────────────────────


@release_app.command("new")
def release_new_cmd(
    release_id: str = typer.Argument(
        ...,
        help="New release ID. SemVer vX.Y.Z (e.g. v0.1.23 — preferred, matches the specs-doctor canon) or the legacy slug ^[a-z][a-z0-9-]+$.",
    ),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
) -> None:
    """Create specs/releases/<id>/SPEC.md with canonical Draft frontmatter.

    Exits non-zero if the release directory already exists (no-clobber) or if
    the release ID does not match the required slug pattern.
    """
    target = _resolve_specs_dir(specs_dir)

    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)

    try:
        result = release_new(target, release_id)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)
    except FileExistsError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    typer.echo(f"[ok] created: {result.path}")


# ── dadaia backlog new ────────────────────────────────────────────────────────


@backlog_app.command("new")
def backlog_new_cmd(
    slug: str = typer.Argument(
        ...,
        help="Backlog entry slug (e.g. cool-idea). Must match ^[a-z][a-z0-9-]+$.",
    ),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
) -> None:
    """Create specs/backlog/<slug>.md with canonical frontmatter stub."""
    target = _resolve_specs_dir(specs_dir)

    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)

    try:
        result = backlog_new(target, slug)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)
    except FileExistsError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    typer.echo(f"[ok] created: {result.path}")


# ── dadaia bug new ────────────────────────────────────────────────────────────


@bug_app.command("new")
def bug_new_cmd(
    slug: str = typer.Argument(
        ...,
        help="Bug slug (e.g. login-crash). Must match ^[a-z][a-z0-9-]+$.",
    ),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
) -> None:
    """Create specs/bugs/<slug>.md with session_id: null in frontmatter.

    Per R1 spec: does NOT block when no session is bound (that is an R2 feature).
    The file is always created with session_id: null.
    """
    target = _resolve_specs_dir(specs_dir)

    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)

    try:
        result = bug_new(target, slug)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)
    except FileExistsError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    typer.echo(f"[ok] created: {result.path}")
