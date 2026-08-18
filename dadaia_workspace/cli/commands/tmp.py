"""``dadaia tmp`` — FR29/T-043-44: the orphan backstop (``dadaia tmp gc``).

The **only** calendar-based deletion in v0.4.3 (alpha-5, WS-G): a dated-scratch sweep,
a ``*cache*``-named directory sweep, and an orphaned-session-marker sweep, each gated by
a 3-day age floor. Every OTHER GC capability this release ships (FR23-FR28 — a consumed
push verdict, a closed release's artifacts, the reconciler's own stale-record reap, log
rotation, the cache-must-not-be-born venv guard) is EVENT-DRIVEN: it fires because a
specific, observable thing happened. This verb exists precisely because event-driven GC
can still miss something (a session that crashed before any hook fired, a long gap
between tool calls), and it is safe to run unattended at a harness's ``SessionStart``
because nothing recent is ever eligible — see
``dadaia_workspace.features.tmp_gc.service`` for the full doctrine and the AG.1 lane
guard.
"""

from __future__ import annotations

import typer

from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.tmp_gc.service import TmpGcOutcome, run_tmp_gc

app = typer.Typer(help="Ephemeral .dadaia/ scratch backstop (the calendar-based GC lane).")

_LANE_LABELS: tuple[tuple[str, str], ...] = (
    ("scratch_dirs", "dated scratch (>3 days old)"),
    ("cache_dirs", "cache directories"),
    ("orphan_markers", "orphaned session markers"),
)


def _print_lane(label: str, entries: tuple[str, ...]) -> None:
    if not entries:
        return
    typer.echo(f"  {label}:")
    for entry in entries:
        typer.echo(f"    - {entry}")


@app.command(name="gc")
def gc(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Report what would be removed without touching the filesystem.",
    ),
) -> None:
    """The orphan backstop: dated scratch >3 days old, ``*cache*`` directories, and
    orphaned session markers. This is the ONLY calendar-based deletion in this release
    — every other GC capability here is event-driven (a push landing, a release
    closing, the reconciler's own stale-record reap). Idempotent (a second run reports
    and changes nothing) and safe to run unattended at SessionStart: nothing recent is
    ever eligible, and a live session's own records/markers are never touched.
    """
    workspace_root = resolve_workspace_root()
    outcome: TmpGcOutcome = run_tmp_gc(workspace_root, dry_run=dry_run)

    if outcome.total == 0 and not outcome.lane_guard_refused:
        typer.echo("dadaia tmp gc: nothing to reclaim.")
        return

    verb = "would reclaim" if dry_run else "reclaimed"
    typer.echo(f"dadaia tmp gc: {verb} {outcome.total} item(s).")
    for field, label in _LANE_LABELS:
        _print_lane(label, getattr(outcome, field))
    if outcome.lane_guard_refused:
        typer.echo("  refused by the lane guard (resolved outside .dadaia/):")
        for entry in outcome.lane_guard_refused:
            typer.echo(f"    - {entry}")

    if dry_run:
        typer.echo("\nRun 'dadaia tmp gc' (no --dry-run) to actually delete.")
