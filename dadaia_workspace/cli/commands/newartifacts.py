"""CLI command groups: ``dadaia release``, ``dadaia backlog``, ``dadaia bug``.

Implements:
- dadaia release new <id>    → specs/releases/<id>/SPEC.md stub
- dadaia backlog new <slug>  → specs/backlog/<slug>.md stub
- dadaia bug new <slug>      → specs/bugs/<slug>.md stub (session_id: null)
- dadaia backlog subjects    → read-only resolve/preview of canonical subjects (v0.1.25 R1)
- dadaia backlog doctor      → BL-SCHEMA/DUP/CONFLICT/STALE backlog-consistency check (R1)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.core.specs_resolver import resolve_specs_dir as _shared_resolve_specs_dir
from dadaia_workspace.features.spec_artifacts.new_artifacts import (
    backlog_new,
    bug_new,
    release_new,
)


def _resolve_backlog_roots(
    specs_dir: Path, source_root: str | None, alias_map: str | None
) -> tuple[Path, Path, Path, Path]:
    """Resolve the injected roots the registry/doctor need (SPEC §3.8 #6 — never cwd).

    Returns ``(source_root, catalog_path, alias_map_path, archive_root)``. ``source_root``
    defaults to the repo root that owns ``specs_dir`` (``specs_dir.parent``) so code anchors
    are derived REPO-ROOT-relative (e.g. ``dadaia_workspace/core/...#Sym``) — matching the way
    committed ``code`` refs are authored. The alias map defaults to the workspace-level
    ``.dadaia/states/backlog_subject_aliases.txt`` resolved up from ``specs_dir``.
    """
    src = Path(source_root).resolve() if source_root else specs_dir.parent.resolve()
    catalog_path = specs_dir / "memory" / "product" / "catalog.json"
    archive_root = specs_dir / "_archive"
    alias_map_path = Path(alias_map).resolve() if alias_map else _default_alias_map_path(specs_dir)
    return src, catalog_path, alias_map_path, archive_root


def _default_alias_map_path(specs_dir: Path) -> Path:
    """Walk up from ``specs_dir`` to the workspace root and target the alias-map file."""
    here = specs_dir.resolve()
    for parent in (here, *here.parents):
        if (parent / ".dadaia").is_dir():
            return parent / ".dadaia" / "states" / "backlog_subject_aliases.txt"
    # No workspace found above specs_dir: fall back to a sibling of specs_dir (still injected).
    return specs_dir.parent / ".dadaia" / "states" / "backlog_subject_aliases.txt"


# ── shared typer apps ─────────────────────────────────────────────────────────

release_app = typer.Typer(help="Release management commands.")
backlog_app = typer.Typer(help="Backlog entry management commands.")
bug_app = typer.Typer(help="Bug report management commands.")


# ── helper: resolve specs_dir ─────────────────────────────────────────────────


def _current_ancestry_pids() -> frozenset[int] | None:
    """Build this ``dadaia`` process's nearest-first ancestry pid chain for bind attribution.

    W1-8 (v0.1.47): the persisted-bind fallback attributes a bind-epoch marker by
    ancestry-chain MEMBERSHIP. A marker written from an ephemeral harness Bash shell records
    the bind process's chain (incl. the long-lived harness pid); this CLI runs under a
    DIFFERENT short-lived shell but shares that harness pid deeper in ITS chain, so passing
    this process's chain lets the resolver match on the shared anchor. Built via the
    composition-root ancestry seam (same read-only port the chokepoints use). Any failure ⇒
    ``None`` ⇒ the resolver degrades to single-getppid equality.
    """
    try:
        from dadaia_workspace import container

        return frozenset(container.build_ancestry_pid_chain(os.getppid()))
    except Exception:  # noqa: BLE001 — attribution is best-effort; never break resolution.
        return None


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory.

    Priority:
    1. Explicit ``--specs-dir`` argument.
    2. Bound context session (``DADAIA_CONTEXT`` / ``DADAIA_SESSION_ID`` / persisted-bind
       marker attributed by ancestry-chain membership — W1-8).
    3. ``<cwd>/specs`` fallback.
    """
    return _shared_resolve_specs_dir(specs_dir, ancestry_pids=_current_ancestry_pids())


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


# ── dadaia backlog subjects (read-only resolve/preview surface — v0.1.25 R1) ────


@backlog_app.command("subjects")
def backlog_subjects_cmd(
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
    source_root: str | None = typer.Option(
        None, "--source-root", help="Source root for code-anchor derivation. Default: library."
    ),
    alias_map: str | None = typer.Option(
        None, "--alias-map", help="Alias-map path. Default: workspace .dadaia/states/."
    ),
    kind: SubjectKind | None = typer.Option(
        None, "--kind", help="Filter listed anchors to one subject kind."
    ),
    resolve: str | None = typer.Option(
        None, "--resolve", help="Resolve a proposed subject ref (requires --kind) and exit."
    ),
) -> None:
    """List the live canonical-subject anchors, or resolve one proposed subject (read-only).

    Never writes a backlog file or the alias map. ``--resolve`` shows how a proposed subject
    binds to a canonical anchor (or UNRESOLVED/AMBIGUOUS + an alias-map suggestion) and exits
    non-zero on a HALT, so the backfill author sees real anchors before authoring intents.
    """
    from dadaia_workspace.features.backlog.preview import list_anchors, resolve_one
    from dadaia_workspace.features.backlog.subject_registry import BindStatus, build_registry

    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)
    src, catalog_path, alias_map_path, _archive = _resolve_backlog_roots(
        target, source_root, alias_map
    )
    registry = build_registry(
        source_root=src,
        catalog_path=catalog_path,
        alias_map_path=alias_map_path,
        specs_dir=target,
    )

    if resolve is not None:
        if kind is None:
            typer.echo("[error] --resolve requires --kind", err=True)
            sys.exit(2)
        preview = resolve_one(registry, resolve, kind)
        if preview.status is BindStatus.RESOLVED:
            typer.echo(f"RESOLVED  {resolve}  ->  {preview.anchor_id}")
            return
        typer.echo(f"{preview.status.value.upper()}  {resolve}", err=True)
        if preview.message:
            typer.echo(f"  {preview.message}", err=True)
        if preview.alias_suggestion:
            typer.echo(f"  alias suggestion: {preview.alias_suggestion}", err=True)
        sys.exit(1)

    anchors = list_anchors(registry, kind)
    for anchor in anchors:
        typer.echo(f"{anchor.kind.value:10s}  {anchor.id}")
    typer.echo(f"\n[ok] {len(anchors)} anchor(s).")


# ── dadaia backlog doctor (the ENFORCED backstop — v0.1.25 R1) ──────────────────


@backlog_app.command("doctor")
def backlog_doctor_cmd(
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
    source_root: str | None = typer.Option(
        None, "--source-root", help="Source root for code-anchor derivation. Default: library."
    ),
    alias_map: str | None = typer.Option(
        None, "--alias-map", help="Alias-map path. Default: workspace .dadaia/states/."
    ),
    explain: bool = typer.Option(
        False, "--explain", help="Print the per-item bound-anchor resolution alongside findings."
    ),
) -> None:
    """Run BL-SCHEMA/DUP/CONFLICT/STALE over the live backlog; exit non-zero on any ERROR.

    This is the ENFORCED backstop (ADR-D): wired into the pre-commit chokepoint + CI, it
    rejects a hand-written divergent twin even though ``specs/backlog/`` is gitignored +
    ADDITIVE. ``--explain`` additionally prints how each item's subjects resolved.
    """
    from dadaia_workspace.features.backlog.doctor import Severity, run_backlog_doctor

    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)
    src, catalog_path, alias_map_path, archive_root = _resolve_backlog_roots(
        target, source_root, alias_map
    )

    if explain:
        _explain_backlog(target, src, catalog_path, alias_map_path)

    findings = run_backlog_doctor(
        specs_dir=target,
        source_root=src,
        catalog_path=catalog_path,
        alias_map_path=alias_map_path,
        archive_root=archive_root,
    )

    errors = [f for f in findings if f.severity is Severity.ERROR]
    for finding in findings:
        marker = finding.severity.value.upper()
        slug = f" [{finding.slug}]" if finding.slug else ""
        typer.echo(f"[{marker}] {finding.code.value}{slug} {finding.message}", err=True)

    if errors:
        typer.secho(
            f"\nbacklog doctor FAILED: {len(errors)} error(s).", fg=typer.colors.RED, err=True
        )
        sys.exit(1)
    typer.secho("backlog doctor: clean.", fg=typer.colors.GREEN)


def _explain_backlog(specs_dir: Path, src: Path, catalog_path: Path, alias_map_path: Path) -> None:
    """Print how each backlog item's subjects bind to canonical anchors (read-only)."""
    from dadaia_workspace.features.backlog.preview import (
        bound_anchor_changes,
        load_backlog_items,
    )
    from dadaia_workspace.features.backlog.subject_registry import build_registry

    registry = build_registry(
        source_root=src,
        catalog_path=catalog_path,
        alias_map_path=alias_map_path,
        specs_dir=specs_dir,
    )
    for item in load_backlog_items(specs_dir / "backlog"):
        anchor_changes, unresolved = bound_anchor_changes(item, registry)
        typer.echo(f"# {item.slug}")
        for anchor_id, change in sorted(anchor_changes.items()):
            typer.echo(f"  RESOLVED  {anchor_id}  ->  {change}")
        for message in unresolved:
            typer.echo(f"  UNRESOLVED  {message}")
