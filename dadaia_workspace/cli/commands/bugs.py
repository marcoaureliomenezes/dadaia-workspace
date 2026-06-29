"""CLI command group: `dadaia bugs <verb>` JSONL telemetry."""

from __future__ import annotations

import json
import sys

import typer

from dadaia_workspace.core.specs_resolver import resolve_specs_dir
from dadaia_workspace.features.bugs.events import (
    append_event,
    bug_stats,
    bug_status,
    make_event,
    migrate_markdown_bugs,
)

app = typer.Typer(help="Append-only bug event telemetry commands.")


@app.command("append")
def append_cmd(
    bug_id: str,
    event: str,
    reported_by: str = typer.Option(..., "--reported-by"),
    specs_dir: str | None = typer.Option(None, "--specs-dir"),
    title: str | None = typer.Option(None, "--title"),
    severity: str | None = typer.Option(None, "--severity"),
    surface: str | None = typer.Option(None, "--surface"),
    component: str | None = typer.Option(None, "--component"),
    context: str | None = typer.Option(None, "--context"),
    tag: list[str] | None = typer.Option(None, "--tag"),
    symptom: str | None = typer.Option(None, "--symptom"),
    repro: str | None = typer.Option(None, "--repro"),
    expected: str | None = typer.Option(None, "--expected"),
    notes: str | None = typer.Option(None, "--notes"),
    release: str | None = typer.Option(None, "--release"),
    superseded_by: str | None = typer.Option(None, "--superseded-by"),
    reason: str | None = typer.Option(None, "--reason"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    target = resolve_specs_dir(specs_dir)
    try:
        payload = make_event(
            bug_id=bug_id,
            event=event,
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
        )
        path = append_event(target, payload)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)
    _emit({"path": str(path), "event": payload}, json_output=json_output)


@app.command("status")
def status_cmd(
    bug_id: str | None = typer.Argument(None),
    specs_dir: str | None = typer.Option(None, "--specs-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    payload = bug_status(resolve_specs_dir(specs_dir), bug_id)
    _emit(payload, json_output=json_output)


@app.command("stats")
def stats_cmd(
    specs_dir: str | None = typer.Option(None, "--specs-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _emit(bug_stats(resolve_specs_dir(specs_dir)), json_output=json_output)


@app.command("migrate-md")
def migrate_md_cmd(
    specs_dir: str | None = typer.Option(None, "--specs-dir"),
    apply: bool = typer.Option(False, "--apply", help="Write events and move Markdown bugs."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        payload = migrate_markdown_bugs(resolve_specs_dir(specs_dir), apply=apply)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)
    _emit(payload, json_output=json_output)


def _emit(payload: object, *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        typer.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True))
