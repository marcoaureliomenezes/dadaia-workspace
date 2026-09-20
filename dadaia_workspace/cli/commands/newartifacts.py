"""CLI command group: ``dadaia release``.

Implements:
- dadaia release new <id>    → specs/releases/<id>/SPEC.md stub + _RELEASE.json
- dadaia release phase <P>   → the ONE writer of phase/defined/implemented
- dadaia release rc-archive  → the completed candidate trio into rc-N/
- dadaia release archive <id> → the promote lane: ship, move to _archive/, birth <next>

The backlog verbs retired in 0.4.7 c7 (T-047-65): ``BACKLOG.json`` and its exit ledger
have ONE writer, the stdlib skill script
``public/skills/dd-backlog-definition/scripts/backlog.py``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import typer

from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.core.models.histo import HistoRecord
from dadaia_workspace.core.release_state import RELEASE_STATE_FILENAME
from dadaia_workspace.features.specs.candidate import (
    ArchiveError,
    archive_candidate,
    archive_release,
    fold_release,
    set_phase,
)
from dadaia_workspace.features.specs.canon import release_new
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

# ── shared typer apps ─────────────────────────────────────────────────────────

release_app = typer.Typer(help="Release management commands.")


# ── helper: resolve specs_dir ─────────────────────────────────────────────────


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory.

    Priority: explicit ``--specs-dir``, else the single resolution authority
    (the root `AGENTS.md` map §3: ``DADAIA_CONTEXT`` → own live session record → repo-of-cwd).
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


# ── dadaia release phase ──────────────────────────────────────────────────────


@release_app.command("phase")
def release_phase_cmd(
    phase: str = typer.Argument(..., help="IMPLEMENTATION or CLOSURE."),
    sha: str = typer.Option(..., "--sha", help="The commit the milestone names (7-40 hex)."),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
) -> None:
    """Move the live release to IMPLEMENTATION or CLOSURE, stamping its milestone.

    The ONE writer of `phase`, `defined` and `implemented` (0.4.7 FR5): those fields
    were Read-then-Edit, which is how `release archive` came to refuse on a hand-set
    `implemented` it validated itself. The phase and the milestone now move in one act,
    so they cannot disagree.
    """
    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)
    try:
        change = set_phase(target, phase.upper(), sha=sha)
    except ArchiveError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    typer.echo(f"[ok] release {change.release} -> phase {change.phase} ({change.ts})")


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
    typer.echo(
        f"[ok] candidate {result.rc} of release {result.release} archived -> "
        f"{result.rc_dir} — root is ready for the next candidate's SPEC/PLAN/TASKS."
    )


def _histo_appender(target: Path) -> Callable[[HistoRecord], None]:
    """The ``releases_histo.jsonl`` sink, built the way every other ledger store is
    built at the composition root — one record shape, one store, no second writer.

    The append carries its own governance event, under its own namespace: a histo
    record and the ``_RELEASE.json`` of the same release share an id and are two
    different records, so one namespace for both would compare each against the
    other's hash forever.
    """
    store: JsonlRecordStore[HistoRecord] = JsonlRecordStore(
        target / "releases" / "_archive" / "releases_histo.jsonl",
        to_dict=HistoRecord.to_dict,
        from_dict=HistoRecord.from_dict,
    )

    def append(record: HistoRecord) -> None:
        store.append(record)

    return append


# ── dadaia release fold ───────────────────────────────────────────────────────


def _histo_updater(
    target: Path,
) -> Callable[[str, Callable[[HistoRecord], HistoRecord]], HistoRecord | None]:
    """The in-place rewrite of one ``releases_histo.jsonl`` record — the same store the
    appender builds, one governance event per rewritten record; ``None`` when no record
    carries that id (a pre-canon release may have none)."""
    from dadaia_workspace.infrastructure.jsonl_record_store import RecordNotFoundError

    store: JsonlRecordStore[HistoRecord] = JsonlRecordStore(
        target / "releases" / "_archive" / "releases_histo.jsonl",
        to_dict=HistoRecord.to_dict,
        from_dict=HistoRecord.from_dict,
    )

    def update(record_id: str, mutate: Callable[[HistoRecord], HistoRecord]) -> HistoRecord | None:
        try:
            record = store.update(record_id, mutate)
        except RecordNotFoundError:
            return None
        return record

    return update


@release_app.command("fold")
def release_fold_cmd(
    folded_id: str = typer.Argument(
        ..., help="The wrongly archived release under _archive/, e.g. 0.5.2."
    ),
    into: str = typer.Option(
        ..., "--into", help="The published version that shipped it, e.g. 0.4.5."
    ),
    shipped: str | None = typer.Option(
        None, "--shipped", help="Publication sha — required when _archive/<into>/ is born here."
    ),
    pr: int | None = typer.Option(
        None, "--pr", help="Ship PR number — required when _archive/<into>/ is born here."
    ),
    shipped_ts: str | None = typer.Option(
        None, "--shipped-ts", help="The publication's UTC timestamp (default: now)."
    ),
    final: bool = typer.Option(
        False, "--final", help="Place the trio at the target's root (the final candidate)."
    ),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
) -> None:
    """Fold a wrongly archived release into rc-N/ of the version that published it.

    The archive holds PUBLISHED versions only (operator ruling 2026-09-14, ADR 0014): a
    candidate closed between two PyPI publications is rc-N of the version that
    published it, never its own archived release — the shape RELEASE-TREE-ARCHIVE-ID /
    RELEASE-TREE-ARCHIVE-UNSHIPPED refuse. One transactional act: moves the trio(s),
    merges the state logs, deletes the folded directory, rewrites the histo record(s)
    in place, and records one governance event.
    """
    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)
    try:
        result = fold_release(
            target,
            folded_id,
            into=into,
            shipped_sha=shipped,
            pr=pr,
            shipped_ts=shipped_ts,
            final=final,
            histo_update=_histo_updater(target),
        )
    except ArchiveError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)
    typer.echo(
        f"[ok] {result.folded} folded into {result.into} at "
        f"{result.placed_at.relative_to(target).as_posix()} (rc={result.rc}); "
        f"histo rewritten: {', '.join(result.histo_ids) or 'none'}."
    )


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
    <next>, appends the one releases_histo record — all or
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

    typer.echo(f"[ok] archived: {result.archived_dir}")
    typer.echo(f"[ok] created: {result.next_spec}")
    typer.echo(f"[ok] created: {result.next_spec.parent / RELEASE_STATE_FILENAME}")
    typer.echo(f"[ok] histo record: {result.histo_id} (delivered)")
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
