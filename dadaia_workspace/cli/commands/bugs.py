"""CLI command group: ``dadaia bugs append|status|stats`` (v0.1.46 AC-1).

Event-sourced JSONL bug telemetry surface. Distinct from the legacy ``dadaia bug`` (singular)
Markdown command — the two coexist this release; the rewritten guardrail rule points agents
at ``dadaia bugs append``. Writes land under ``specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl`` — an
ADDITIVE path (no lease taken).

``append`` validates the event against the packaged ``bug-event-v1`` JSON Schema before it
touches the store; ``status`` folds the stream to list open bugs; ``stats`` aggregates by
status and severity. All three print observable STDOUT for scripting.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import typer
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.core.models.bugs import BugEvent, BugEventKind
from dadaia_workspace.features.bugs.service import BugService
from dadaia_workspace.infrastructure.jsonl_bug_store import JsonlBugStore

__all__ = ["bugs_app"]

bugs_app = typer.Typer(help="Event-sourced JSONL bug telemetry (append/status/stats).")

#: The packaged schema id (file lives at ``public/schemas/bugs/<id>.schema.json``).
_SCHEMA_ID = "bug-event-v1"


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory (explicit flag → bound context → cwd/specs)."""
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


@bugs_app.command("append")
def bugs_append_cmd(
    bug_id: str = typer.Option(..., "--bug-id", help="Stable kebab-case bug identifier."),
    event: BugEventKind = typer.Option(
        BugEventKind.REPORTED, "--event", help="Event kind (reported/resolved/…)."
    ),
    reported_by: str = typer.Option(
        "software-engineer", "--reported-by", help="Agent/runtime recording the event."
    ),
    ts: str | None = typer.Option(None, "--ts", help="ISO-8601 UTC timestamp. Default: now."),
    title: str | None = typer.Option(None, "--title", help="reported: short title."),
    severity: str | None = typer.Option(
        None, "--severity", help="reported: LOW/MEDIUM/HIGH/CRITICAL."
    ),
    surface: str | None = typer.Option(None, "--surface", help="reported: failing surface."),
    component: str | None = typer.Option(None, "--component", help="reported: subsystem."),
    context: str | None = typer.Option(None, "--context", help="reported: spec-context."),
    tag: list[str] | None = typer.Option(None, "--tag", help="reported: tag (repeatable)."),
    symptom: str | None = typer.Option(None, "--symptom", help="reported: what happened."),
    repro: str | None = typer.Option(None, "--repro", help="reported: how to reproduce."),
    expected: str | None = typer.Option(None, "--expected", help="reported: contract promise."),
    notes: str | None = typer.Option(None, "--notes", help="reported: notes (redacted)."),
    release: str | None = typer.Option(None, "--release", help="resolved: fixing release."),
    resolution_evidence: str | None = typer.Option(
        None,
        "--resolution-evidence",
        help="resolved (REQUIRED, v0.1.73 resolution law): reporter-artifact repro + "
        "every surface the bug names (or the explicit re-scope). Min 20 chars.",
    ),
    superseded_by: str | None = typer.Option(
        None, "--superseded-by", help="superseded: superseding slug."
    ),
    reason: str | None = typer.Option(None, "--reason", help="deferred/rejected: rationale."),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """Validate a bug event against ``bug-event-v1`` and append it to the JSONL stream.

    ADDITIVE — takes no lease. On a schema-validation failure nothing is written and the
    command exits non-zero with the validation message.
    """
    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        raise typer.Exit(code=1)

    # v0.1.73 FR3 (resolution law, BLOCKING form): a resolved event without evidence is
    # refused BEFORE anything is written — the recurrence audit showed ~40% of the
    # v0.1.66-71 arc's resolutions were need-unmet; evidence = reporter-artifact repro
    # + every surface the bug names (or the explicit re-scope).
    if event is BugEventKind.RESOLVED and (
        resolution_evidence is None or len(resolution_evidence.strip()) < 20
    ):
        typer.echo(
            "[error] resolved requires --resolution-evidence (>=20 chars): "
            "reporter-artifact repro + every surface the bug names (resolution law).",
            err=True,
        )
        raise typer.Exit(code=1)

    model = BugEvent(
        bug_id=bug_id,
        event=event.value,
        ts=ts or _now_iso(),
        reported_by=reported_by,
        title=title,
        severity=severity,
        surface=surface,
        component=component,
        context=context,
        tags=tuple(tag or ()),
        symptom=symptom,
        repro=repro,
        expected=expected,
        notes=notes,
        release=release,
        superseded_by=superseded_by,
        reason=reason,
        evidence=resolution_evidence,
    ).redact()

    payload = model.to_dict()
    try:
        _load_validator().validate(payload)
    except ValidationError as exc:
        typer.echo(f"[error] bug event invalid: {exc.message}", err=True)
        raise typer.Exit(code=1) from exc

    path = JsonlBugStore(target / "bugs").append_event(model)
    typer.echo(f"[ok] appended {event.value} for {bug_id} -> {path}")


@bugs_app.command("status")
def bugs_status_cmd(
    include_closed: bool = typer.Option(
        False, "--all", help="Include closed/terminal bugs (default: open only)."
    ),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context session."
    ),
) -> None:
    """List folded bug states (open by default), one ``bug_id`` per line."""
    target = _resolve_specs_dir(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        raise typer.Exit(code=1)

    service = BugService(JsonlBugStore(target / "bugs"))
    states = service.status(include_closed=include_closed)
    for state in states:
        severity = state.severity or "-"
        typer.echo(f"{state.bug_id}\t{state.status}\t{severity}")
    scope = "all" if include_closed else "open"
    typer.echo(f"[ok] {len(states)} {scope} bug(s).")


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

    service = BugService(JsonlBugStore(target / "bugs"))
    stats = service.stats()
    typer.echo(f"total\t{stats.total}")
    for status, count in sorted(stats.by_status.items()):
        typer.echo(f"status:{status}\t{count}")
    for severity, count in sorted(stats.by_severity.items()):
        typer.echo(f"severity:{severity}\t{count}")
