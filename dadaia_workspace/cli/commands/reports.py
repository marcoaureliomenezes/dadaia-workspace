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
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.panel.reports_doctor import ReportsDoctor
from dadaia_workspace.features.reports.retention import (
    CleanupCandidate,
    ReportRetentionService,
)
from dadaia_workspace.features.reports.validation import ValidationResult

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
# Version detection helpers (T-21)
# ---------------------------------------------------------------------------


def _detect_sidecar_version(doc: dict[str, object]) -> str:
    """Return '1.1' if doc declares handoff-v1.1, else '1.0'."""
    schema_version = doc.get("schema_version", "")
    schema_id = doc.get("$id", "")
    if schema_version == "handoff-v1.1" or "v1.1" in str(schema_id):
        return "1.1"
    return "1.0"


def _check_v10_compat(path: Path, doc: dict[str, object]) -> tuple[bool, list[str]]:
    """Check a v1.0 sidecar for missing required v1.1 fields.

    Returns:
        (is_error, messages) — is_error=True triggers exit 1;
        is_error=False means warnings only (exit 0).
    """
    messages: list[str] = []
    is_error = False

    # Missing findings[] entirely → hard error
    if "findings" not in doc:
        messages.append(
            "ERROR: Missing required field 'findings[]'. "
            "This sidecar appears to be v1.0 and is incompatible with v1.1."
        )
        is_error = True
        return is_error, messages

    # findings[] present but items missing detail_md or fix_recommendation → warning
    findings = doc.get("findings", [])
    if isinstance(findings, list):
        for idx, finding in enumerate(findings):
            if isinstance(finding, dict):
                missing_subfields = []
                if "detail_md" not in finding:
                    missing_subfields.append("detail_md")
                if "fix_recommendation" not in finding:
                    missing_subfields.append("fix_recommendation")
                if missing_subfields:
                    messages.append(
                        f"WARNING: findings[{idx}] missing "
                        f"{' or '.join(repr(f) for f in missing_subfields)}. "
                        f"Sidecar is v1.0-incomplete — consider upgrading to v1.1."
                    )

    # Missing scope or metrics → warning
    missing_root = []
    if "scope" not in doc:
        missing_root.append("scope")
    if "metrics" not in doc:
        missing_root.append("metrics")
    if missing_root:
        messages.append(
            f"WARNING: Missing {' or '.join(repr(f) for f in missing_root)} fields. "
            f"Sidecar is v1.0-incomplete."
        )

    return is_error, messages


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
) -> None:
    """Validate one or more agent handoff JSON files.

    \b
    Exit codes:
      0  All files valid (or violations found in non-strict mode)
      1  One or more violations in strict mode, or v1.0 sidecar missing findings[]
      2  One or more file paths not found
      3  Bad invocation (no paths and not --all) or workspace not initialized

    \b
    Examples:
      dadaia reports validate path/to/report.handoff.json
      dadaia reports validate --all
      dadaia reports validate --all --strict
      dadaia reports validate --all --json
    """
    # Invocation guard: must have paths or --all
    if not paths and not all_:
        err_console.print("[red]Error:[/red] provide one or more PATHS or use [bold]--all[/bold].")
        raise typer.Exit(3)

    # Build service — schema must be staged
    try:
        workspace_root = resolve_workspace_root()
        service = container.build_reports_validation_service(workspace_root)
    except HandoffSchemaError as exc:
        err_console.print(
            f"[red]Error:[/red] Could not load handoff schema: {exc}\n"
            "Run [bold]dadaia public stage && dadaia public install --target all[/bold] first."
        )
        raise typer.Exit(3) from None
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(3) from None

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

    # Per-file: detect version and apply appropriate validation
    results: list[ValidationResult] = []
    compat_errors: list[str] = []  # v1.0 hard errors (missing findings[])
    compat_warnings: list[tuple[Path, list[str]]] = []  # v1.0 soft warnings
    has_v10_error = False

    for p in target_paths:
        try:
            raw = p.read_text(encoding="utf-8")
            doc = _json.loads(raw)
        except (_json.JSONDecodeError, OSError):
            # Let the schema validator handle structural issues
            results.append(service.validate_file(p))
            continue

        version = _detect_sidecar_version(doc)
        if version == "1.0":
            is_error, messages = _check_v10_compat(p, doc)
            if is_error:
                has_v10_error = True
                for msg in messages:
                    compat_errors.append(f"{p}: {msg}")
            elif messages:
                compat_warnings.append((p, messages))
            # Also run schema validation so errors are reported
            results.append(service.validate_file(p))
        else:
            # v1.1: full schema validation
            results.append(service.validate_file(p))

    # Apply release filter if requested
    if release:
        filtered: list[ValidationResult] = []
        for r in results:
            if r.valid:
                try:
                    doc = _json.loads(r.path.read_text(encoding="utf-8"))
                    if doc.get("release_id") == release:
                        filtered.append(r)
                except Exception:  # noqa: BLE001
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

        # Print v1.0 compat errors
        for msg in compat_errors:
            err_console.print(f"[red]{msg}[/red]")

        # Print v1.0 compat warnings
        for warn_path, warn_msgs in compat_warnings:
            for msg in warn_msgs:
                console.print(f"[yellow]{warn_path}: {msg}[/yellow]")

        console.print(
            f"\nSummary: [green]{n_valid} valid[/green], [red]{n_invalid} invalid[/red] "
            f"(of {len(results)} files)"
        )

    # Exit code logic: hard error if v1.0 missing findings[], or strict mode violations
    if has_v10_error:
        raise typer.Exit(1)
    if strict and n_invalid > 0:
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
    referenced_artifacts = _handoff_artifact_paths(handoff_root, workspace_root)

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
                    try:
                        raw = filepath.read_text(encoding="utf-8")
                        doc = _json.loads(raw)
                    except (_json.JSONDecodeError, OSError):
                        flags.append(f"MISSING_FIELDS: {filepath} (malformed JSON)")
                        continue

                    missing_fields: list[str] = []
                    if "findings" not in doc:
                        missing_fields.append("findings")
                    if "scope" not in doc:
                        missing_fields.append("scope")
                    if "metrics" not in doc:
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
    reports_doctor = ReportsDoctor(workspace_root)
    result = reports_doctor.check()

    if json_output:
        typer.echo(
            _json.dumps(
                {
                    "ok": result.ok,
                    "issue_count": len(result.issues),
                    "issues": [
                        {
                            "code": i.code,
                            "message": i.message,
                            "sidecar_path": str(i.sidecar_path),
                            "artifact_path": i.artifact_path,
                        }
                        for i in result.issues
                    ],
                }
            )
        )
        raise typer.Exit(0 if result.ok else 1)

    if result.ok:
        console.print("[green]OK[/green] No RPT-1 issues found.")
        raise typer.Exit(0)

    for issue in result.issues:
        console.print(f"[red]{issue.code}[/red] {issue.message}", markup=False)
    console.print(f"\n{len(result.issues)} issue(s) found.")
    raise typer.Exit(1)


def _handoff_artifact_paths(handoff_root: Path, workspace_root: Path) -> set[str]:
    refs: set[str] = set()
    if not handoff_root.exists():
        return refs
    for filepath in handoff_root.rglob("*.handoff.json"):
        try:
            doc = _json.loads(filepath.read_text(encoding="utf-8"))
        except (_json.JSONDecodeError, OSError):
            continue
        artifact = doc.get("artifact", {})
        if isinstance(artifact, dict):
            path = artifact.get("path")
            if isinstance(path, str) and path:
                refs.add(path)
                artifact_path = (
                    workspace_root / path if path.startswith(".dadaia/") else filepath.parent / path
                )
                refs.add(_workspace_relative_ref(artifact_path, workspace_root))
    return refs


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
    ctx = context or os.environ.get("DADAIA_CONTEXT")
    try:
        workspace_root = resolve_workspace_root()
        service = container.build_reports_next_service(workspace_root, context=ctx)
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
