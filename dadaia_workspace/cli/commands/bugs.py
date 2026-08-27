"""CLI command group: ``dadaia bugs append|status|stats|update|archive`` (v0.5.0 FR2).

One record per bug (``core.models.bugs.BugRecord``), appended once — no event stream, no
fold (D11, D-F). ``append`` registers a brand-new record (``status: "open"``); every
governance write — the fixer's resolve, the auditor's ``audited``/``resolved_commit``
rewrite — goes through ``update`` (AS-16, A2.13): the ONE write seam
(``features.bugs.service.BugService``), redacted, atomic, refuse-stale. ``archive``
(A2.8) moves terminal records older than 90 days to ``specs/bugs/_archive/bugs_histo.jsonl``.
Writes land under an ADDITIVE path (never concurrency-blocked).

The event kinds ``resolved``/``picked``/``archived`` no longer exist on this CLI —
resolution/supersession/deferral/rejection are governance-field writes, made through
``update``; the reservation marker (``picked``) and its annotation (``archived``)
disappear entirely (FR2: "the value, its transition and picked_by all disappear").
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import typer
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from dadaia_workspace import container
from dadaia_workspace.cli._specs_resolution import (
    repo_slug_for_context,
    resolve_context_for_cli,
    resolve_specs_dir_for_cli,
)
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.models.bugs import (
    BUG_ARCHIVE_THRESHOLD_DAYS,
    BugRecordImmutableFieldError,
    BugRecordWriteOnceFieldSetError,
)
from dadaia_workspace.core.protocols.record_store import RecordNotFoundError, StaleRecordWriteError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.bugs.service import BugDuplicateIdError, BugService

__all__ = ["bugs_app"]

bugs_app = typer.Typer(help="One-record-per-bug telemetry (append/status/stats/update/archive).")

#: The packaged schema id (file lives at ``public/schemas/bugs/<id>.schema.json``).
_SCHEMA_ID = "bug-record-v1"


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory (explicit flag, else the resolution authority)."""
    return resolve_specs_dir_for_cli(specs_dir)


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


def _schema_root() -> Path:
    """Resolve the packaged ``public/schemas/`` root inside the wheel/source tree.

    Package root is three levels up from this module (``cli/commands/bugs.py``); the schema
    source lives at ``public/schemas/bugs/``.
    """
    package_root = Path(__file__).resolve().parents[2]
    return package_root / "public" / "schemas" / "bugs"


def _load_validator() -> Draft202012Validator:
    schema_path = _schema_root() / f"{_SCHEMA_ID}.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _now_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _service(target: Path, *, with_archive: bool = False) -> BugService:
    return BugService(
        container.build_bug_record_store(target),
        archive_store=container.build_bug_archive_store(target) if with_archive else None,
        denylist_terms=container.load_denylist_terms(),
    )


def _print_coherence_warnings(service: BugService) -> None:
    """A2.3: surface governance-completeness gaps as a WARNING, never a block (D15) —
    printed to stderr so stdout stays stable for every scripted consumer of ``status``/
    ``stats`` (CLI-output stability)."""
    gaps = service.coherence_violations()
    if not gaps:
        return
    typer.echo(
        f"[warn] {len(gaps)} record(s) incomplete for their status "
        "(missing governance fields) — run 'specs doctor' for the per-record detail",
        err=True,
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
    component: str = typer.Option("", "--component", help="Free text: path#symbol precision."),
    context: str = typer.Option("", "--context", help="The spec-context the bug was found in."),
    symptom: str | None = typer.Option(None, "--symptom", help="What happened."),
    repro: str | None = typer.Option(None, "--repro", help="How to reproduce."),
    expected: str | None = typer.Option(None, "--expected", help="What the contract promises."),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """Register a brand-new bug record (``status: "open"``) — validated against
    ``bug-record-v1`` before it touches the ledger.

    ADDITIVE and never concurrency-blocked. On schema-validation failure (a missing
    immutable-core field, a bad ``--severity``/``--surface`` enum value), or a
    ``--bug-id`` that already exists, nothing is written and the command exits
    non-zero — the SAME schema-first-then-write shape ``append`` has always had (never
    a typer-level required-option crash, so every rejection carries the SAME
    ``[error] bug record invalid: ...`` message shape).
    """
    target = _resolve_append_specs_dir(specs_dir, context or None)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        raise typer.Exit(code=1)

    resolved_ts = ts or _now_iso()
    payload: dict[str, object] = {
        "id": bug_id,
        "ts": resolved_ts,
        "reported_by": reported_by,
        "title": title,
        "severity": severity,
        "surface": surface,
        "component": component,
        "context": context,
        "symptom": symptom,
        "repro": repro,
        "expected": expected,
        "status": "open",
        "cause": None,
        "caused_by": None,
        "lineage_source": None,
        "registration_commit": None,
        "registration_granularity": None,
        "resolved_commit": None,
        "resolution_granularity": None,
        "resolved_release": None,
        "audited": None,
    }
    try:
        _load_validator().validate(payload)
    except ValidationError as exc:
        typer.echo(f"[error] bug record invalid: {exc.message}", err=True)
        raise typer.Exit(code=1) from exc
    # Schema validation just proved every immutable-core field is a non-empty string —
    # narrow the `str | None` CLI options to `str` for the service call below.
    assert title is not None
    assert severity is not None
    assert surface is not None
    assert symptom is not None
    assert repro is not None
    assert expected is not None

    service = _service(target)
    try:
        path = service.register(
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
    except BugDuplicateIdError as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"[ok] registered {bug_id} -> {path}")


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
    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        raise typer.Exit(code=1)

    service = _service(target)
    records = service.status(include_closed=include_closed)
    for record in records:
        severity = record.severity or "-"
        typer.echo(f"{record.id}\t{record.status}\t{severity}")
    scope = "all" if include_closed else "open"
    typer.echo(f"[ok] {len(records)} {scope} bug(s).")
    _print_coherence_warnings(service)


@bugs_app.command("stats")
def bugs_stats_cmd(
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """Print aggregate bug counts by status and by severity."""
    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        raise typer.Exit(code=1)

    service = _service(target)
    stats = service.stats()
    typer.echo(f"total\t{stats.total}")
    for status, count in sorted(stats.by_status.items()):
        typer.echo(f"status:{status}\t{count}")
    for severity, count in sorted(stats.by_severity.items()):
        typer.echo(f"severity:{severity}\t{count}")
    _print_coherence_warnings(service)


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
    """AS-16 — the one governance-write seam: the fixer's resolve, the auditor's
    ``audited``/``resolved_commit`` rewrite, and any other governance/write-once field
    change all go through this verb. No content validation is added beyond the seam's
    own structural refusals (immutable-core changed, write-once field re-set with a
    differing value) — a refuse-stale race is reported as a non-zero exit naming the
    re-read-and-retry remedy, never a block on a human (D15/AS-16)."""
    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        raise typer.Exit(code=1)

    changes: Mapping[str, str] = _parse_set_options(set_)
    service = _service(target)
    try:
        updated = service.apply_update(bug_id, changes)
    except (
        BugRecordImmutableFieldError,
        BugRecordWriteOnceFieldSetError,
        RecordNotFoundError,
        StaleRecordWriteError,
        ValueError,
    ) as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"[ok] updated {', '.join(sorted(changes))} for {updated.id}")


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
    """A2.8 — move terminal records older than ``--threshold-days`` from the live
    ledger to ``specs/bugs/_archive/bugs_histo.jsonl``, through the same record-store
    seam. Idempotent: a second run with nothing newly eligible is a byte-identical
    no-op."""
    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        raise typer.Exit(code=1)

    parsed_now = datetime.fromisoformat(now.replace("Z", "+00:00")) if now else None
    service = _service(target, with_archive=True)
    result = service.archive(now=parsed_now, threshold_days=threshold_days)
    typer.echo(f"[ok] archived {result.archived} record(s), {result.kept} kept.")
