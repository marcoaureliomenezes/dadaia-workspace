"""CLI command groups: ``dadaia release``, ``dadaia backlog``.

Implements:
- dadaia release new <id>    → specs/releases/<id>/SPEC.md stub
- dadaia backlog new <slug>  → specs/backlog/<slug>.md stub
- dadaia backlog subjects    → read-only resolve/preview of canonical subjects (v0.1.25 R1)
- dadaia backlog doctor      → BL-SCHEMA/DUP/CONFLICT/STALE backlog-consistency check (R1)

The legacy ``dadaia bug new`` Markdown scaffolder was retired in v0.1.53 — bugs are
event-sourced JSONL via ``dadaia bugs append`` (the v0.1.46 canon).
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.features.spec_artifacts.new_artifacts import (
    backlog_new,
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


# ── helper: resolve specs_dir ─────────────────────────────────────────────────


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory.

    Priority:
    1. Explicit ``--specs-dir`` argument.
    2. Bound context session (``DADAIA_CONTEXT`` / ``DADAIA_SESSION_ID`` / persisted-bind
       marker attributed by ancestry-chain membership — W1-8).
    3. ``<cwd>/specs`` fallback.
    """
    return resolve_specs_dir_for_cli(specs_dir)


# ── dadaia release new ────────────────────────────────────────────────────────


@release_app.command("new")
def release_new_cmd(
    release_id: str = typer.Argument(
        ...,
        help="New release ID. SemVer vX.Y.Z (e.g. v0.1.23 — preferred, matches the specs-doctor canon) or the legacy slug in lowercase kebab-case (start with a letter, then a-z0-9 or hyphens).",
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
        help="Backlog entry slug in lowercase kebab-case: start with a letter, then a-z0-9 or hyphens (e.g. cool-idea).",
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
    from dadaia_workspace.cli.anchors import derive_cli_anchors
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
        cli_anchors=derive_cli_anchors(),
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
    from dadaia_workspace.cli.anchors import derive_cli_anchors
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
        cli_anchors=derive_cli_anchors(),
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
    from dadaia_workspace.cli.anchors import derive_cli_anchors
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
        cli_anchors=derive_cli_anchors(),
    )
    for item in load_backlog_items(specs_dir / "backlog"):
        anchor_changes, unresolved = bound_anchor_changes(item, registry)
        typer.echo(f"# {item.slug}")
        for anchor_id, change in sorted(anchor_changes.items()):
            typer.echo(f"  RESOLVED  {anchor_id}  ->  {change}")
        for message in unresolved:
            typer.echo(f"  UNRESOLVED  {message}")


@backlog_app.command("consume")
def backlog_consume_cmd(
    release_id: str = typer.Option(
        ..., "--release-id", help="Release whose SPEC declares the picks."
    ),
    context: str | None = typer.Option(
        None, "--context", help="Spec context. Default: resolve from the bound session."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit the ledger summary as JSON."),
) -> None:
    """Write the consumed-backlog ledger from a release SPEC's ``**Consumes:**`` line.

    Producer half of removal-on-release. Parses
    ``<specs_dir>/releases/<release-id>/SPEC.md``, binds each declared slug's ``intents[]``
    through the canonical-subject registry into the verified shipped-anchor set, and writes
    ``specs/_archive/<release-id>/consumed_backlog.json``.

    An absent or empty ``**Consumes:**`` line is a clean no-op. A declared slug that does not
    resolve fails loudly — never a silent skip.
    """
    import json as _json

    from dadaia_workspace import container
    from dadaia_workspace.cli._specs_resolution import resolve_context_for_cli
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
    from dadaia_workspace.features.backlog.consumes import parse_consumes_line, shipped_anchors_for

    from dadaia_workspace.core.exceptions import DadaiaError

    workspace_root = resolve_workspace_root()
    ctx = resolve_context_for_cli(context)
    try:
        spec_path = container.build_release_spec_path(
            workspace_root, context=ctx, release_id=release_id
        )
    except DadaiaError as exc:
        # A missing SPEC is NOT "consumes nothing" — reading an absent file as an empty
        # string made a real release look like a clean no-op (exit 0), which is exactly
        # the silence this verb exists to prevent.
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(2) from None
    slugs = parse_consumes_line(spec_path.read_text(encoding="utf-8"))
    if not slugs:
        typer.echo("no `**Consumes:**` line — nothing to consume.")
        return
    lifecycle = container.build_backlog_removal_lifecycle(workspace_root, context=ctx)
    shipped = shipped_anchors_for(
        slugs, backlog_dir=lifecycle.backlog_dir, registry=lifecycle.registry
    )
    ledger = lifecycle.consume(release_id=release_id, shipped_anchors=shipped)
    payload = {
        "consumed_slugs": list(slugs),
        "shipped_anchors": sorted(shipped),
        "ledger": str(ledger),
    }
    typer.echo(
        _json.dumps(payload, indent=2, sort_keys=True)
        if json_output
        else f"consumed {len(slugs)} item(s) -> {ledger}"
    )


@backlog_app.command("remove-consumed")
def backlog_remove_consumed_cmd(
    release_id: str = typer.Option(
        ..., "--release-id", help="Release whose ledger drives removal."
    ),
    context: str | None = typer.Option(
        None, "--context", help="Spec context. Default: resolve from the bound session."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit the removal summary as JSON."),
) -> None:
    """Drop every fully-consumed backlog item named by a release's ledger.

    Consumer half of removal-on-release, run at closure. Archives a copy of each item first,
    then removes it from the live ``specs/backlog/`` set, so ``dadaia backlog doctor`` reports
    no BL-STALE. Reports any slug the ledger claims was consumed that is still present.
    """
    import json as _json

    from dadaia_workspace import container
    from dadaia_workspace.cli._specs_resolution import resolve_context_for_cli
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    workspace_root = resolve_workspace_root()
    ctx = resolve_context_for_cli(context)
    removal = container.build_backlog_removal_lifecycle(workspace_root, context=ctx).remove(
        release_id=release_id
    )
    payload = {
        "removed": [a.slug for a in removal.actions if a.action.value == "archived_and_removed"],
        "rewritten": [a.slug for a in removal.actions if a.action.value == "rewritten"],
        "unchanged": [a.slug for a in removal.actions if a.action.value == "unchanged"],
    }
    typer.echo(
        _json.dumps(payload, indent=2, sort_keys=True)
        if json_output
        else f"removed {len(payload['removed'])}, rewritten {len(payload['rewritten'])}"
    )
