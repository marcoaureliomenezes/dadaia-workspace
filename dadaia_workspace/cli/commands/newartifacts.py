"""CLI command groups: ``dadaia release``, ``dadaia backlog``.

Implements:
- dadaia release new <id>    → specs/releases/<id>/SPEC.md stub + _RELEASE.json
- dadaia release rc-archive  → the completed candidate trio into rc-N/
- dadaia release archive <id> → the promote lane: ship, move to _archive/, birth <next>
- dadaia backlog new <slug>  → appends one active[] entry to specs/backlog/BACKLOG.json
- dadaia backlog subjects    → read-only resolve/preview of canonical subjects (v0.1.25 R1)
- dadaia backlog doctor      → BL-SCHEMA/CONFLICT/STALE backlog-consistency check (BL-DUP
  deleted, not disabled, v0.5.0 A5.2)

The legacy ``dadaia bug new`` Markdown scaffolder was retired in v0.1.53 — bugs are
event-sourced JSONL via ``dadaia bugs append`` (the v0.1.46 canon). ``BACKLOG.md`` support
is retired outright (operator ruling 2026-08-28) — the single source is
``specs/backlog/BACKLOG.json``, schema ``public/schemas/backlog/backlog-v1.schema.json``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import typer

from dadaia_workspace.cli._backlog_roots import resolve_backlog_roots
from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.core.atomic_write import ConcurrentModificationError
from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.core.models.histo import HistoRecord
from dadaia_workspace.core.release_state import RELEASE_STATE_FILENAME
from dadaia_workspace.features.backlog.document import backlog_new
from dadaia_workspace.features.specs.candidate import (
    ArchiveError,
    archive_candidate,
    archive_release,
)
from dadaia_workspace.features.specs.canon import release_new
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

# ── shared typer apps ─────────────────────────────────────────────────────────

release_app = typer.Typer(help="Release management commands.")
backlog_app = typer.Typer(help="Backlog entry management commands.")


# ── helper: resolve specs_dir ─────────────────────────────────────────────────


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory.

    Priority: explicit ``--specs-dir``, else the single resolution authority
    (``DADAIA.md`` §3: ``DADAIA_CONTEXT`` → own live session record → repo-of-cwd).
    """
    return resolve_specs_dir_for_cli(specs_dir)


# ── dadaia release new ────────────────────────────────────────────────────────


@release_app.command("new")
def release_new_cmd(
    release_id: str = typer.Argument(
        ...,
        help="New release ID: bare SemVer X.Y.Z (e.g. 0.1.23 — the canon; a v prefix is refused) or the legacy slug in lowercase kebab-case.",
    ),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
) -> None:
    """Create specs/releases/<id>/ with its SPEC.md stub and _RELEASE.json state.

    The ONE birth act (0.4.7 FR2): both files are written in one transaction, so the
    gate's MEMORY class, `dadaia context show` and `dd-spec-navigator` resolve the new
    release immediately. Exits non-zero — writing nothing — if a live release already
    exists, if any release artifact already exists (no-clobber), or if the release ID
    does not match the required pattern.
    """
    target = _resolve_specs_dir(specs_dir)

    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)

    try:
        spec_path = release_new(target, release_id)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)
    except FileExistsError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    typer.echo(f"[ok] created: {spec_path}")
    typer.echo(f"[ok] created: {spec_path.parent / RELEASE_STATE_FILENAME}")


# ── dadaia release rc-archive ─────────────────────────────────────────────────


@release_app.command("rc-archive")
def release_rc_archive_cmd(
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
) -> None:
    """Archive the live release's completed candidate trio into the next rc-N/.

    The "continue" mechanics of the promote-or-continue gate (release-candidates
    model, ADR 0008): validates candidate closure (trio at root, every task [x],
    phase CLOSURE), moves SPEC/PLAN/TASKS into rc-N/, bumps the candidate counter
    and resets phase to DEFINITION so the next candidate's trio can be born at root.
    The version never increments here — that happens only at operator-approved
    deploy.
    """
    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)
    try:
        result = archive_candidate(target)
    except ArchiveError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)
    archived_bugs = _archive_bugs(target)
    typer.echo(
        f"[ok] candidate {result.rc} of release {result.release} archived -> "
        f"{result.rc_dir} — root is ready for the next candidate's SPEC/PLAN/TASKS."
    )
    typer.echo(f"[ok] bugs archived: {archived_bugs}")


# ── helper: the bugs-archive sweep both archive verbs run ─────────────────────


def _archive_bugs(target: Path) -> int:
    """Run ``bugs archive`` inside an archive verb and return how many records moved.

    Composed HERE, at the CLI — ``features/specs`` must not import ``features/bugs``
    (P-07: features compose through the container or the CLI). Archiving a candidate
    or a release is exactly the moment the ledger's terminal records stop being live
    history, so the sweep rides the same verb instead of being a step an agent
    remembers (RC-FLOW's hand-driven lane is what 0.4.7 FR3 deletes).
    """
    from dadaia_workspace.cli.commands.bugs import build_bug_service

    return build_bug_service(target, with_archive=True).archive().archived


def _histo_appender(target: Path) -> Callable[[HistoRecord], None]:
    """The ``releases_histo.jsonl`` sink, built the way every other ledger store is
    built at the composition root — one record shape, one store, no second writer."""
    store: JsonlRecordStore[HistoRecord] = JsonlRecordStore(
        target / "releases" / "_archive" / "releases_histo.jsonl",
        to_dict=HistoRecord.to_dict,
        from_dict=HistoRecord.from_dict,
    )
    return store.append


# ── dadaia release archive ────────────────────────────────────────────────────


@release_app.command("archive")
def release_archive_cmd(
    release_id: str = typer.Argument(..., help="The live release being shipped, e.g. 0.4.7."),
    shipped: str = typer.Option(
        ..., "--shipped", help="The develop -> main merge commit sha (7-40 hex)."
    ),
    pr: int = typer.Option(..., "--pr", help="The ship PR's number."),
    next_release: str = typer.Option(
        ..., "--next", help="The next release version, bare SemVer M.m.p."
    ),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
) -> None:
    """Ship the live release: one transactional promote verb (0.4.7 FR3).

    Validates (release tree, every task [x], phase CLOSURE, `implemented` set), then
    writes `shipped` + ARCHIVED, moves specs/releases/<id>/ to _archive/<id>/, births
    <next>, appends the one releases_histo record and sweeps `bugs archive` — all or
    nothing. Prints the git commands the operator runs next and NEVER runs git itself.
    """
    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)
    try:
        result = archive_release(
            target,
            release_id,
            shipped_sha=shipped,
            pr=pr,
            next_release=next_release,
            histo_append=_histo_appender(target),
        )
    except ArchiveError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    archived_bugs = _archive_bugs(target)
    typer.echo(f"[ok] archived: {result.archived_dir}")
    typer.echo(f"[ok] created: {result.next_spec}")
    typer.echo(f"[ok] created: {result.next_spec.parent / RELEASE_STATE_FILENAME}")
    typer.echo(f"[ok] histo record: {result.histo_id} (delivered)")
    typer.echo(f"[ok] bugs archived: {archived_bugs}")
    typer.echo(
        "next: git add -A specs/releases specs/bugs && git commit -m "
        f'"chore(specs): archive release {result.release} — shipped {shipped} '
        f'(PR #{pr}); {result.next_release} born"'
    )
    typer.echo(f"next: git push origin --delete feature/{result.release}")
    typer.echo(
        f"next: git checkout -b feature/{result.next_release} main "
        "&& git merge -s ours origin/develop"
    )


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
    """Append one ``active[]`` entry for <slug> to specs/backlog/BACKLOG.json.

    Creates the document (``{"schema": "backlog-v1", "active": []}``) first when it does
    not yet exist (SPEC v0.12.0 FR3, ADR #14; operator ruling 2026-08-28 — the
    single-source JSON document, not a per-entry file and not Markdown).
    """
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
    except RuntimeError as exc:
        # A1.2 (v0.4.2) — write-then-verify: the writer raises rather than reporting
        # success when a re-parse of its own fresh write does not show the slug.
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)
    except ConcurrentModificationError as exc:
        # Code review M-8 (0.5.0 T-050-35 re-verdict) — after 7280856c (F-14 CAS),
        # backlog_new's expected_previous write can lose a lost-update race under the
        # NO-LOCKS DOCTRINE. Report it the same way as its three siblings above,
        # rather than an uncaught traceback.
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    verb = "created" if result.created else "appended"
    typer.echo(
        f"[ok] {verb} {slug!r} -> {result.path}"
        if not result.created
        else f"[ok] created: {result.path}"
    )


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
    src, catalog_path, alias_map_path = resolve_backlog_roots(target, source_root, alias_map)
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
