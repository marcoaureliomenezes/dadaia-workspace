"""dadaia reports subcommands — inspect and validate agent handoff reports."""

from __future__ import annotations

import datetime as _dt
import json as _json
import os
from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import (
    HandoffSchemaError,
    NoActiveReleaseError,
    NoAgentSequenceError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.handoff_index import Handoff, ValidationResult, scan_handoffs
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.reports.retention import (
    CleanupCandidate,
    ReportRetentionService,
)

app = typer.Typer(help="Inspect and validate agent handoff reports.")
console = Console()
err_console = Console(stderr=True)

# Maximum HTML file size (bytes) before flagging as oversized
_OVERSIZED_THRESHOLD_BYTES = 30 * 1024  # 30 KB


def _parse_duration(value: str) -> _dt.timedelta:
    raw = value.strip().lower()
    try:
        if raw.endswith("h"):
            amount = int(raw[:-1])
            duration = _dt.timedelta(hours=amount)
        elif raw.endswith("d"):
            amount = int(raw[:-1])
            duration = _dt.timedelta(days=amount)
        else:
            raise ValueError
    except ValueError as exc:
        raise typer.BadParameter("duration must use h or d suffix, for example 48h or 2d") from exc
    if duration <= _dt.timedelta(0):
        raise typer.BadParameter("duration must be greater than zero")
    return duration


def _retention_service() -> ReportRetentionService:
    try:
        workspace_root = resolve_workspace_root()
        return container.build_reports_retention_service(workspace_root)
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(3) from None


def _candidate_payload(candidate: CleanupCandidate) -> dict[str, object]:
    return {
        "artifact_path": candidate.artifact_path,
        "reason": candidate.reason,
        "paths": [str(path) for path in candidate.paths],
        "effective_timestamp": candidate.effective_timestamp.isoformat().replace("+00:00", "Z"),
        "important": candidate.important,
    }


# ---------------------------------------------------------------------------
# retention subcommands
# ---------------------------------------------------------------------------


@app.command(name="cleanup")
def cleanup(
    older_than: str = typer.Option("48h", "--older-than", help="TTL threshold, e.g. 48h or 2d."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="List eligible deletions without deleting."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of text."
    ),
) -> None:
    """Delete expired non-important report artifacts and related handoffs."""
    service = _retention_service()
    try:
        ttl = _parse_duration(older_than)
    except typer.BadParameter as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(2) from None
    result = service.cleanup(older_than=ttl, dry_run=dry_run)
    if json_output:
        typer.echo(
            _json.dumps(
                {
                    "dry_run": result.dry_run,
                    "candidate_count": len(result.candidates),
                    "deleted_count": len(result.deleted_paths),
                    "candidates": [_candidate_payload(c) for c in result.candidates],
                    "deleted_paths": [str(path) for path in result.deleted_paths],
                    "skipped_paths": [str(path) for path in result.skipped_paths],
                }
            )
        )
        raise typer.Exit(0)

    action = "Would delete" if dry_run else "Deleted"
    console.print(
        f"{action} {len(result.deleted_paths) if not dry_run else len(result.candidates)} item(s)."
    )
    for candidate in result.candidates:
        console.print(f"- {candidate.artifact_path}: {candidate.reason}")
        for path in candidate.paths:
            console.print(f"  {path}")
    raise typer.Exit(0)


@app.command(name="mark-important")
def mark_important(
    report_or_handoff_path: str = typer.Argument(..., help="Report or handoff path to protect."),
    reason: str | None = typer.Option(None, "--reason", help="Optional operator reason."),
) -> None:
    """Mark a report or handoff as important so cleanup skips it."""
    service = _retention_service()
    try:
        artifact = service.mark_important(report_or_handoff_path, reason=reason)
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(2) from None
    console.print(f"Marked important: {artifact}")
    raise typer.Exit(0)


@app.command(name="unmark-important")
def unmark_important(
    report_or_handoff_path: str = typer.Argument(..., help="Report or handoff path to unprotect."),
) -> None:
    """Remove important protection from a report or handoff."""
    service = _retention_service()
    try:
        artifact = service.unmark_important(report_or_handoff_path)
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(2) from None
    console.print(f"Unmarked important: {artifact}")
    raise typer.Exit(0)


@app.command(name="important")
def important(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of text."
    ),
) -> None:
    """List reports currently marked important."""
    service = _retention_service()
    items = service.important_reports()
    if json_output:
        typer.echo(_json.dumps({"important": items}))
        raise typer.Exit(0)
    if not items:
        console.print("No important reports.")
    else:
        for path, meta in sorted(items.items()):
            reason = meta.get("reason", "")
            suffix = f" — {reason}" if reason else ""
            console.print(f"{path}{suffix}")
    raise typer.Exit(0)


def _write_efficiency_audit_marker(workspace_root: Path, report: str, by: str) -> Path:
    """Write ``.dadaia/states/last_efficiency_audit.json`` with the current RFC3339 stamp.

    Schema ``{schema_version, last_efficiency_audit, by, report}`` — the marker the
    ``DoctorService`` EFF-1 staleness check reads (v0.1.60 FR7). Producing a fresh marker is
    the production clear path for the EFF-1 warning.
    """
    marker = workspace_root / ".dadaia" / "states" / "last_efficiency_audit.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1",
        "last_efficiency_audit": _dt.datetime.now(tz=_dt.UTC).isoformat().replace("+00:00", "Z"),
        "by": by,
        "report": report,
    }
    marker.write_text(_json.dumps(payload, indent=2), encoding="utf-8")
    return marker


@app.command(name="mark-efficiency-audit")
def mark_efficiency_audit(
    report: str = typer.Option(
        ..., "--report", help="Workspace-relative path to the efficiency-audit report."
    ),
    by: str = typer.Option("", "--by", help="Agent that produced the report."),
) -> None:
    """Record that an efficiency audit was produced — clears the doctor EFF-1 staleness issue."""
    try:
        workspace_root = resolve_workspace_root()
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(3) from None
    marker = _write_efficiency_audit_marker(workspace_root, report, by)
    console.print(f"Recorded efficiency-audit marker: {marker}")
    raise typer.Exit(0)


@app.command(name="status")
def status(
    older_than: str = typer.Option("48h", "--older-than", help="TTL threshold, e.g. 48h or 2d."),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of text."
    ),
) -> None:
    """Show report-retention counters without deleting anything."""
    service = _retention_service()
    try:
        ttl = _parse_duration(older_than)
    except typer.BadParameter as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(2) from None
    payload = service.status(older_than=ttl)
    if json_output:
        typer.echo(_json.dumps(payload))
        raise typer.Exit(0)
    for key, value in payload.items():
        console.print(f"{key}: {value}")
    raise typer.Exit(0)


# ---------------------------------------------------------------------------
# validate subcommand
# ---------------------------------------------------------------------------


@app.command(name="validate")
def validate(
    paths: list[Path] | None = typer.Argument(
        default=None, help="Paths to .handoff.json files to validate."
    ),
    all_: bool = typer.Option(
        False, "--all", help="Validate all *.handoff.json files under the workspace handoff root."
    ),
    release: str | None = typer.Option(
        None,
        "--release",
        help="Filter to a specific release ID (matches against handoff release_id field).",
    ),
    strict: bool = typer.Option(
        False,
        "--strict/--no-strict",
        help="Exit 1 on any validation violation. Default: non-strict (warnings only).",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON output instead of human-readable text."
    ),
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help=(
            "Explicit workspace root to validate against, bypassing cwd-based "
            "ancestor-walk resolution. Use when the target handoff/artifact lives in a "
            "workspace other than the one containing cwd (e.g. a throwaway/nested "
            "workspace) — otherwise artifact.path resolves against the wrong root."
        ),
    ),
    reviewed_root: Path | None = typer.Option(
        None,
        "--reviewed-root",
        help=(
            "Resolve self_pull.refs against THIS filesystem root first (e.g. a linked "
            "worktree checked out at the commit a verdict was authored/reviewed against), "
            "before the ordinary repos/<context>/<ref> and <workspace>/<ref> candidates. "
            "Fixes a false 'ref does not exist' when validating a handoff whose "
            "self_pull.refs were resolved against a tree other than whatever "
            "repos/<context> currently has checked out on disk."
        ),
    ),
) -> None:
    """Validate one or more agent handoff JSON files.

    \b
    Exit codes:
      0  All files valid (or violations found in non-strict mode)
      1  One or more violations in strict mode
      2  One or more file paths not found
      3  Bad invocation (no paths and not --all) or workspace not initialized

    \b
    Examples:
      dadaia reports validate path/to/report.handoff.json
      dadaia reports validate --all
      dadaia reports validate --all --strict
      dadaia reports validate --all --json
      dadaia reports validate path/to/report.handoff.json --workspace /path/to/other/ws
      dadaia reports validate path/to/verdict.handoff.json --reviewed-root /path/to/worktree
    """
    # Invocation guard: must have paths or --all
    if not paths and not all_:
        err_console.print("[red]Error:[/red] provide one or more PATHS or use [bold]--all[/bold].")
        raise typer.Exit(3)

    try:
        workspace_root = workspace.resolve() if workspace is not None else resolve_workspace_root()
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(3) from None

    # Bug ancestor-walk-workspace-root-silent-mistarget (T-043-47/A30.5): always name
    # the resolved workspace root (stderr — never pollutes --json's stdout list shape)
    # so a false INVALID/missing_artifact caused by resolving against the wrong
    # ancestor is never silently misread. --workspace above is the primary fix; this
    # diagnostic covers every invocation, including the cwd-default path.
    err_console.print(f"[dim]Resolved workspace root: {workspace_root}[/dim]")

    index = container.build_handoff_index(workspace_root)

    # Collect paths to validate
    target_paths: list[Path] = []
    if all_:
        results_root = workspace_root / ".dadaia" / "handoff"
        target_paths = sorted(results_root.rglob("*.handoff.json")) if results_root.exists() else []
    elif paths:
        missing = [p for p in paths if not p.exists()]
        if missing:
            for m in missing:
                err_console.print(f"[red]Error:[/red] File not found: {m}")
            raise typer.Exit(2)
        target_paths = list(paths)

    # Version routing (v1/v1.1/v1.2, and refusal of any future/unknown token) lives in
    # the schema's own ``schema_version`` enum now — Handoff.validate applies ONE
    # validation path for every schema_version, never a second ad-hoc detector here.
    try:
        results: list[ValidationResult] = [
            index.validate_file(p, reviewed_root=reviewed_root) for p in target_paths
        ]
    except HandoffSchemaError as exc:
        err_console.print(
            f"[red]Error:[/red] Could not load handoff schema: {exc}\n"
            "Run [bold]dadaia public stage && dadaia public install --target all[/bold] first."
        )
        raise typer.Exit(3) from None

    # Apply release filter if requested
    if release:
        filtered: list[ValidationResult] = []
        for r in results:
            if r.valid:
                if Handoff.load(r.path).release_id == release:
                    filtered.append(r)
            else:
                filtered.append(r)
        results = filtered

    # Output
    n_valid = sum(1 for r in results if r.valid)
    n_invalid = len(results) - n_valid

    if json_output:
        payload = [
            {
                "path": str(r.path),
                "valid": r.valid,
                "errors": [{"field_path": e.field_path, "message": e.message} for e in r.errors],
                "hash_status": r.hash_status,
            }
            for r in results
        ]
        console.print_json(data=payload)
    else:
        for r in results:
            if r.valid:
                console.print(f"[green]VALID[/green]   {r.path}")
            else:
                console.print(f"[red]INVALID[/red] {r.path}")
                for err in r.errors:
                    console.print(f"         [yellow]{err.field_path}[/yellow]: {err.message}")

        console.print(
            f"\nSummary: [green]{n_valid} valid[/green], [red]{n_invalid} invalid[/red] "
            f"(of {len(results)} files)"
        )

    # Exit-code truthfulness (validation-029 F-12): an INVALID file is a hard failure
    # — printing INVALID while exiting 0 masked tampered/malformed handoffs from every
    # consuming script. --strict remains the elevation for soft warnings only.
    if n_invalid > 0:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# lint subcommand (T-22)
# ---------------------------------------------------------------------------


@app.command(name="lint")
def lint(
    directory: Path | None = typer.Argument(
        default=None,
        help="Directory to lint recursively. Defaults to .dadaia/reports/ plus .dadaia/handoff/.",
    ),
) -> None:
    """Lint reports and handoffs for missing links, oversized HTMLs, and fields.

    \b
    Flags emitted:
      ORPHAN: <path>              HTML file with no handoff artifact.path reference
      OVERSIZED: <path> (<size>KB) HTML file larger than 30 KB
      MISSING_FIELDS: <path>      Handoff missing findings, scope, or metrics fields

    \b
    Exit code is always 0 (lint, not blocker). Summary printed at end.

    \b
    Examples:
      dadaia reports lint
      dadaia reports lint .dadaia/reports/
      dadaia reports lint .dadaia/handoff/
    """
    workspace_root = resolve_workspace_root()

    reports_root = workspace_root / ".dadaia" / "reports"
    handoff_root = workspace_root / ".dadaia" / "handoff"
    directories = [reports_root, handoff_root] if directory is None else [directory]

    existing_directories = [item for item in directories if item.exists()]
    if not existing_directories:
        err_console.print(
            f"[yellow]Warning:[/yellow] Directory not found: {', '.join(str(d) for d in directories)}"
        )
        raise typer.Exit(0)

    flags: list[str] = []
    # The one discovery + artifact-path rule: every referenced artifact ref, both the
    # raw declared string and its resolved workspace-relative form (a handoff can
    # legitimately declare either shape — see Handoff.artifact_path's docstring).
    referenced_artifacts: set[str] = set()
    for handoff in scan_handoffs(handoff_root):
        raw_ref = handoff.artifact_path_raw
        if not raw_ref:
            continue
        referenced_artifacts.add(raw_ref)
        resolved = handoff.artifact_path(workspace_root)
        if resolved is not None:
            referenced_artifacts.add(_workspace_relative_ref(resolved, workspace_root))

    for root in existing_directories:
        for dirpath_str, _dirnames, filenames in os.walk(root):
            dirpath = Path(dirpath_str)
            for filename in filenames:
                filepath = dirpath / filename

                if filename.lower().endswith(".html"):
                    report_ref = _workspace_relative_ref(filepath, workspace_root)
                    if report_ref not in referenced_artifacts:
                        flags.append(f"ORPHAN: {filepath}")

                    size_bytes = filepath.stat().st_size
                    if size_bytes > _OVERSIZED_THRESHOLD_BYTES:
                        size_kb = size_bytes / 1024
                        flags.append(f"OVERSIZED: {filepath} ({size_kb:.1f}KB)")

                elif filename.lower().endswith(".handoff.json"):
                    handoff = Handoff.load(filepath)
                    if handoff.malformed_error is not None:
                        flags.append(f"MISSING_FIELDS: {filepath} (malformed JSON)")
                        continue

                    missing_fields: list[str] = []
                    if "findings" not in handoff.raw:
                        missing_fields.append("findings")
                    if "scope" not in handoff.raw:
                        missing_fields.append("scope")
                    if "metrics" not in handoff.raw:
                        missing_fields.append("metrics")

                    if missing_fields:
                        fields_str = ", ".join(missing_fields)
                        flags.append(f"MISSING_FIELDS: {filepath} (missing: {fields_str})")

    if flags:
        for flag in flags:
            console.print(flag)
        console.print(f"\n{len(flags)} issue(s) found.")
    else:
        console.print("OK: No issues found.")

    raise typer.Exit(0)


# ---------------------------------------------------------------------------
# doctor subcommand (T-PANEL-02)
# ---------------------------------------------------------------------------


@app.command(name="doctor")
def doctor(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of human-readable text."
    ),
) -> None:
    """Diagnose structural invariants in .dadaia/reports/ and .dadaia/handoff/.

    \b
    Invariants checked:
      RPT-1: handoff artifact.path must point to an existing .html under .dadaia/reports/.

    \b
    Flags emitted:
      [dangling-artifact-path] <sidecar> → <artifact.path>  (RPT-1 violation)

    \b
    Exit codes:
      0  No issues found.
      1  One or more invariant violations detected.

    \b
    Examples:
      dadaia reports doctor
      dadaia reports doctor --json
    """
    workspace_root = resolve_workspace_root()
    handoff_root = workspace_root / ".dadaia" / "handoff"
    _RPT1_PREFIX = ".dadaia/reports/"
    issues: list[dict[str, str | None]] = []
    for handoff in scan_handoffs(handoff_root):
        artifact_path_str = handoff.artifact_path_raw
        if not artifact_path_str:
            # No artifact.path declared — sidecar is valid (handoff-first emission).
            continue
        reason: str | None = None
        if not artifact_path_str.startswith(_RPT1_PREFIX):
            reason = f"artifact.path must start with '{_RPT1_PREFIX}'"
        else:
            resolved = handoff.artifact_path(workspace_root)
            if resolved is None:
                reason = "path traversal or boundary escape detected"
            elif not resolved.exists():
                reason = "file does not exist"
            elif resolved.suffix.lower() != ".html":
                reason = f"not an .html file — got {resolved.suffix!r}"
        if reason is not None:
            issues.append(
                {
                    "code": "RPT-1",
                    "message": (
                        f"[dangling-artifact-path] {handoff.path} → {artifact_path_str!r} "
                        f"({reason})"
                    ),
                    "sidecar_path": str(handoff.path),
                    "artifact_path": artifact_path_str,
                }
            )

    if json_output:
        typer.echo(
            _json.dumps(
                {
                    "ok": not issues,
                    "issue_count": len(issues),
                    "issues": issues,
                }
            )
        )
        raise typer.Exit(0 if not issues else 1)

    if not issues:
        console.print("[green]OK[/green] No RPT-1 issues found.")
        raise typer.Exit(0)

    for issue in issues:
        console.print(f"[red]{issue['code']}[/red] {issue['message']}", markup=False)
    console.print(f"\n{len(issues)} issue(s) found.")
    raise typer.Exit(1)


def _workspace_relative_ref(path: Path, workspace_root: Path) -> str:
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# next subcommand (T-RN-02 / FR-RN-1)
# ---------------------------------------------------------------------------


@app.command(name="next")
def next_(
    context: str | None = typer.Option(
        None, "--context", help="Context name to resolve (defaults to the primary context)."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of human-readable text."
    ),
) -> None:
    """Discover the next expected agent given the current reports state.

    Reads the active release's PLAN.md owner sequence and checks which agents have
    already emitted a ``.handoff.json`` for that release.

    \b
    Exit codes:
      0  Resolved (an agent is pending, or all agents have emitted handoffs)
      3  No active release / no agent sequence in PLAN.md / workspace not initialized
    """
    try:
        workspace_root = resolve_workspace_root()
        service = container.build_reports_next_service(workspace_root, context=context)
        result = service.resolve_next()
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(3) from None
    except (NoActiveReleaseError, NoAgentSequenceError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(3) from None

    if json_output:
        console.print(
            _json.dumps(
                {
                    "next_agent": result.next_agent,
                    "release_id": result.release_id,
                    "completed_agents": result.completed_agents,
                    "pending_agents": result.pending_agents,
                }
            )
        )
        raise typer.Exit(0)

    completed = ", ".join(result.completed_agents) if result.completed_agents else "(none)"
    if result.next_agent is None:
        console.print("All agents have emitted handoffs for this release.")
        console.print(f"  Release: {result.release_id}")
        console.print(f"  Completed: {completed}")
    else:
        pending = ", ".join(result.pending_agents)
        console.print(f"Next expected agent: {result.next_agent}")
        console.print(f"  Release: {result.release_id}")
        console.print(f"  Already completed: {completed}")
        console.print(f"  Pending: {pending}")
    raise typer.Exit(0)
