"""CLI command group: ``dadaia bugs append|status|stats|update|resolve|supersede|defer|
reject|archive``.

One record per bug (``core.models.bugs.BugRecord``), appended once — no event stream,
no fold. ``append`` registers a brand-new record (``status: "open"``).

**Status transitions are the interface.** ``resolve``/``supersede``/``defer``/
``reject`` are the ONLY way a record reaches their respective terminal status — each
calls :meth:`~dadaia_workspace.features.bugs.service.BugService.transition` with the
matching unbound :class:`~dadaia_workspace.core.models.bugs.BugRecord` transition
method: status is unreachable without its own required fields, refused with every
missing/invalid field named at once, the record left completely untouched on refusal.
``update --set status=...`` is REFUSED (the model itself refuses the key ``"status"``).
``update`` remains the seam for every OTHER governance/write-once field (the auditor's
``audited``/``resolved_commit`` rewrite). ``archive`` moves terminal records older
than 90 days to ``specs/bugs/_archive/bugs_histo.jsonl``. Writes land under an
ADDITIVE path (never concurrency-blocked).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

import typer

from dadaia_workspace import container
from dadaia_workspace.cli._specs_resolution import (
    repo_slug_for_context,
    resolve_context_for_cli,
    resolve_specs_dir_for_cli,
)
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.models.bugs import BUG_ARCHIVE_THRESHOLD_DAYS, BugRecord
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.bugs.service import BugService
from dadaia_workspace.infrastructure.jsonl_record_store import (
    JsonlRecordStore,
    RecordNotFoundError,
    StaleRecordWriteError,
)

__all__ = ["bugs_app"]

bugs_app = typer.Typer(
    help="One-record-per-bug telemetry "
    "(append/status/stats/update/resolve/supersede/defer/reject/archive)."
)


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory (explicit flag, else the resolution authority)."""
    return resolve_specs_dir_for_cli(specs_dir)


def _target(specs_dir: str | None) -> Path:
    """Resolve *specs_dir* and echo-and-exit when it is not a directory — the one
    guard every command below shares (D7/D8), instead of a copy per command."""
    resolved = _resolve_specs_dir(specs_dir)
    if not resolved.is_dir():
        typer.echo(f"[error] specs_dir not found: {resolved}", err=True)
        raise typer.Exit(code=1)
    return resolved


def _resolve_append_specs_dir(specs_dir: str | None, event_context: str | None) -> Path:
    """Resolve the ledger destination for ``bugs append``.

    Bug ``bugs-append-ledger-ignores-context-flag``: the record's ``--context`` field is
    a ROUTING key, not an inert label — a record whose context names B must never land
    silently in the bound context A's ledger. Order: explicit ``--specs-dir`` (always
    wins, unchanged) -> ``--context``'s own ``repos/<name>/specs`` (refused loudly when
    that directory does not exist) -> the pre-existing bound-context/cwd resolution.
    """
    if specs_dir is not None:
        return resolve_specs_dir_for_cli(specs_dir)
    if event_context:
        resolved_name = resolve_context_for_cli(event_context)  # validates the name shape
        try:
            workspace_root = resolve_workspace_root()
        except WorkspaceNotInitializedError:
            workspace_root = None
        if workspace_root is not None:
            # The repo DIRECTORY comes from the registry, never from the context name: a
            # context created with `--repo <slug>` legitimately has a name that differs,
            # and assuming they match refused a perfectly valid context
            # (bug a2-bugs-append-context-resolution-ignores-repo-slug).
            slug = repo_slug_for_context(workspace_root, resolved_name)
            candidate = workspace_root / "repos" / slug / "specs"
            if candidate.is_dir():
                return candidate.resolve()
            raise typer.BadParameter(
                f"--context {resolved_name!r} resolves to repo slug {slug!r}, but no "
                f"'repos/{slug}/specs' directory exists in this workspace. Check the "
                "context is registered and ALIVE, or pass --specs-dir explicitly — "
                "refusing to land the record in a different context's ledger."
            )
    return resolve_specs_dir_for_cli(specs_dir)


def _now_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _service(target: Path, *, with_archive: bool = False) -> BugService:
    # ADR-0001: build_bug_archive_store had exactly one consumer (this module's
    # `dadaia bugs archive`) — the single consumer builds it directly instead of a
    # container seam. build_bug_record_store stays a container seam because
    # `cli.commands.specs` shares it (bug_store_factory -> GovernanceValidator).
    archive_store: JsonlRecordStore[BugRecord] | None = None
    if with_archive:
        archive_store = JsonlRecordStore(
            target / "bugs" / "_archive" / "bugs_histo.jsonl",
            to_dict=BugRecord.to_dict,
            from_dict=BugRecord.from_dict,
        )
    return BugService(
        container.build_bug_record_store(target),
        archive_store=archive_store,
        denylist_terms=container.load_denylist_terms(),
        baseline_patterns=container.load_denylist_baseline_patterns(),
        validate=container.build_bug_record_validator(),
        # F017: the component normalizer probes the containing repo for the on-disk
        # spelling; specs/ always sits at the repo root.
        repo_root=target.parent,
    )


@bugs_app.command("append")
def bugs_append_cmd(
    bug_id: str = typer.Option(..., "--bug-id", help="Stable kebab-case bug identifier."),
    reported_by: str = typer.Option(
        "software-engineer", "--reported-by", help="Agent/runtime recording the record."
    ),
    ts: str | None = typer.Option(None, "--ts", help="ISO-8601 UTC timestamp. Default: now."),
    title: str | None = typer.Option(None, "--title", help="Short human-readable bug title."),
    severity: str | None = typer.Option(None, "--severity", help="LOW/MEDIUM/HIGH/CRITICAL."),
    surface: str | None = typer.Option(
        None,
        "--surface",
        help="Closed enum — a feature package name, a non-feature layer "
        "(core/infrastructure/cli/hooks/tests/public-assets), or 'unknown'.",
    ),
    component: str = typer.Option(
        "",
        "--component",
        help="Repo-relative path#symbol (normalized at the seam; free text tolerated).",
    ),
    context: str = typer.Option("", "--context", help="The spec-context the bug was found in."),
    symptom: str | None = typer.Option(None, "--symptom", help="What happened."),
    repro: str | None = typer.Option(None, "--repro", help="How to reproduce."),
    expected: str | None = typer.Option(None, "--expected", help="What the contract promises."),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """Register a brand-new bug record (``status: "open"``) — validated against
    ``bug-record-v1`` (:meth:`~dadaia_workspace.features.bugs.service.BugService
    .register`, D9) before it touches the ledger.

    ADDITIVE and never concurrency-blocked. On schema-validation failure (a missing
    immutable-core field, a bad ``--severity``/``--surface`` enum value), or a
    ``--bug-id`` that already exists, nothing is written and the command exits
    non-zero.
    """
    target = _resolve_append_specs_dir(specs_dir, context or None)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        raise typer.Exit(code=1)

    resolved_ts = ts or _now_iso()
    service = _service(target)
    try:
        service.register(
            bug_id=bug_id,
            ts=resolved_ts,
            reported_by=reported_by,
            title=title,
            severity=severity,
            surface=surface,
            component=component,
            context=context,
            symptom=symptom,
            repro=repro,
            expected=expected,
        )
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"[ok] registered {bug_id} -> {target}")


@bugs_app.command("status")
def bugs_status_cmd(
    include_closed: bool = typer.Option(
        False, "--all", help="Include closed/terminal bugs (default: open only)."
    ),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """List folded bug records (open by default), one ``id`` per line."""
    target = _target(specs_dir)
    service = _service(target)
    records = service.status(include_closed=include_closed)
    for record in records:
        severity = record.severity or "-"
        typer.echo(f"{record.id}\t{record.status}\t{severity}")
    scope = "all" if include_closed else "open"
    typer.echo(f"[ok] {len(records)} {scope} bug(s).")


@bugs_app.command("stats")
def bugs_stats_cmd(
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """Print aggregate bug counts by status and by severity."""
    target = _target(specs_dir)
    service = _service(target)
    stats = service.stats()
    typer.echo(f"total\t{stats.total}")
    for status, count in sorted(stats.by_status.items()):
        typer.echo(f"status:{status}\t{count}")
    for severity, count in sorted(stats.by_severity.items()):
        typer.echo(f"severity:{severity}\t{count}")


def _parse_set_options(raw_sets: list[str]) -> dict[str, str]:
    changes: dict[str, str] = {}
    for item in raw_sets:
        if "=" not in item:
            raise typer.BadParameter(f"--set {item!r} must be 'field=value'")
        field_name, _, value = item.partition("=")
        field_name = field_name.strip()
        if not field_name:
            raise typer.BadParameter(f"--set {item!r} has an empty field name")
        changes[field_name] = value
    return changes


@bugs_app.command("update")
def bugs_update_cmd(
    bug_id: str = typer.Argument(..., help="The record id to update."),
    set_: list[str] = typer.Option(
        ...,
        "--set",
        help="A governance/write-once 'field=value' pair (repeatable). Core fields are "
        "refused at the seam (A2.2a).",
    ),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """The one governance-write seam for every governance/write-once field OTHER than
    ``status`` — the auditor's ``audited``/``resolved_commit`` rewrite and any other
    non-status governance write go through this verb. No content validation is added
    beyond the seam's own structural refusals (immutable-core changed, write-once
    field re-set with a differing value) — a refuse-stale race is reported as a
    non-zero exit naming the re-read-and-retry remedy, never a block on a human.

    ``--set status=...`` is REFUSED — the model itself refuses the key ``"status"``
    (:meth:`~dadaia_workspace.core.models.bugs.BugRecord.apply_governance_update`),
    naming the matching transition command instead
    (``dadaia bugs resolve|supersede|defer|reject``)."""
    target = _target(specs_dir)
    changes: Mapping[str, str] = _parse_set_options(set_)
    service = _service(target)
    try:
        updated = service.apply_update(bug_id, changes)
    except (
        RecordNotFoundError,
        StaleRecordWriteError,
        ValueError,
    ) as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"[ok] updated {', '.join(sorted(changes))} for {updated.id}")


def _run_transition(
    target: Path, bug_id: str, method: Callable[..., BugRecord], fields: Mapping[str, str | None]
) -> None:
    """Shared body for the four transition commands below — *method* is the unbound
    :class:`~dadaia_workspace.core.models.bugs.BugRecord` transition method
    (``BugRecord.resolve``/``.supersede``/``.defer``/``.reject``), passed directly by
    the caller (D7/D8, never a second verb->method mapping). Every option is threaded
    through as-is (``None`` when the operator omitted it), so the model's own
    transition method is the ONE place "what's required" is decided."""
    service = _service(target)
    present = {key: value for key, value in fields.items() if value is not None}
    try:
        updated = service.transition(bug_id, method, **present)
    except (RecordNotFoundError, StaleRecordWriteError, ValueError) as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"[ok] {updated.status} {updated.id}")


@bugs_app.command("resolve")
def bugs_resolve_cmd(
    bug_id: str = typer.Argument(..., help="The record id to resolve."),
    cause: str | None = typer.Option(None, "--cause", help="What caused the bug."),
    caused_by: str | None = typer.Option(
        None,
        "--caused-by",
        help="Prior bug id this one was caused by, or the literal 'none'.",
    ),
    resolved_release: str | None = typer.Option(
        None, "--resolved-release", help="The release id that shipped the fix."
    ),
    solution: str | None = typer.Option(None, "--solution", help="What the fix does."),
    evidence_loop: str | None = typer.Option(
        None, "--evidence-loop", help="The red-loop command that reproduced the bug."
    ),
    evidence_seam: str | None = typer.Option(
        None, "--evidence-seam", help="The regression test file/node that pins the fix."
    ),
    evidence_diff: str | None = typer.Option(
        None,
        "--evidence-diff",
        help="'net-negative|net-positive|net-neutral: <rationale>'.",
    ),
    diff_direction: str | None = typer.Option(
        None, "--diff-direction", help="net-negative|net-neutral|net-positive."
    ),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """The ONE way a record reaches ``status="resolved"`` — every option above is
    REQUIRED by the model's own transition method
    (:meth:`~dadaia_workspace.core.models.bugs.BugRecord.resolve`); omitting one is
    refused with every missing/invalid field named at once, and the record is left
    completely untouched (never a partial write)."""
    target = _target(specs_dir)
    _run_transition(
        target,
        bug_id,
        BugRecord.resolve,
        {
            "cause": cause,
            "caused_by": caused_by,
            "resolved_release": resolved_release,
            "solution": solution,
            "evidence_loop": evidence_loop,
            "evidence_seam": evidence_seam,
            "evidence_diff": evidence_diff,
            "diff_direction": diff_direction,
        },
    )


@bugs_app.command("supersede")
def bugs_supersede_cmd(
    bug_id: str = typer.Argument(..., help="The record id to supersede."),
    by: str | None = typer.Option(
        None, "--by", help="The backlog/bug/release slug that supersedes this record."
    ),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """The ONE way a record reaches ``status="superseded"`` — ``--by`` is REQUIRED."""
    target = _target(specs_dir)
    _run_transition(target, bug_id, BugRecord.supersede, {"by": by})


@bugs_app.command("defer")
def bugs_defer_cmd(
    bug_id: str = typer.Argument(..., help="The record id to defer."),
    reason: str | None = typer.Option(None, "--reason", help="Why the bug is deferred."),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """The ONE way a record reaches ``status="deferred"`` — ``--reason`` is
    REQUIRED."""
    target = _target(specs_dir)
    _run_transition(target, bug_id, BugRecord.defer, {"reason": reason})


@bugs_app.command("reject")
def bugs_reject_cmd(
    bug_id: str = typer.Argument(..., help="The record id to reject."),
    reason: str | None = typer.Option(None, "--reason", help="Why the bug is rejected."),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """The ONE way a record reaches ``status="rejected"`` — ``--reason`` is
    REQUIRED."""
    target = _target(specs_dir)
    _run_transition(target, bug_id, BugRecord.reject, {"reason": reason})


@bugs_app.command("archive")
def bugs_archive_cmd(
    now: str | None = typer.Option(
        None, "--now", help="ISO-8601 UTC timestamp to treat as 'now' (testing). Default: real now."
    ),
    threshold_days: int = typer.Option(
        BUG_ARCHIVE_THRESHOLD_DAYS,
        "--threshold-days",
        help="Age (days) past which a terminal record is archived.",
    ),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """Move terminal records older than ``--threshold-days`` from the live ledger to
    ``specs/bugs/_archive/bugs_histo.jsonl``, through the same record-store seam.
    Idempotent: a second run with nothing newly eligible is a byte-identical no-op."""
    target = _target(specs_dir)
    parsed_now = datetime.fromisoformat(now.replace("Z", "+00:00")) if now else None
    service = _service(target, with_archive=True)
    result = service.archive(now=parsed_now, threshold_days=threshold_days)
    typer.echo(f"[ok] archived {result.archived} record(s), {result.kept} kept.")
