"""CLI command group: ``dadaia bugs append|status|stats`` (v0.1.46 AC-1).

Event-sourced JSONL bug telemetry surface. Distinct from the legacy ``dadaia bug`` (singular)
Markdown command — the two coexist this release; the rewritten guardrail rule points agents
at ``dadaia bugs append``. Writes land under ``specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl`` — an
ADDITIVE path (never concurrency-blocked).

``append`` validates the event against the packaged ``bug-event-v1`` JSON Schema before it
touches the store; ``status`` folds the stream to list open bugs; ``stats`` aggregates by
status and severity. All three print observable STDOUT for scripting.

v0.4.4 FR23 (T-044-62): ``append --event resolved`` additionally refuses evidence that
cannot be checked — ``--evidence-loop``, ``--evidence-seam`` and ``--evidence-diff`` are
each REQUIRED and independently validated, the refusal naming exactly the missing one.
A ``net-positive:``-prefixed ``--evidence-diff`` does not block the append; it prints an
advisory to dispatch ``software-architect`` before the commit. Historical ``resolved``
events without these fields stay schema-valid and are never rewritten.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import typer
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from dadaia_workspace.cli._specs_resolution import (
    repo_slug_for_context,
    resolve_context_for_cli,
    resolve_specs_dir_for_cli,
)
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.models.bugs import BugEvent, BugEventKind
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.bugs.service import BugService
from dadaia_workspace.infrastructure.jsonl_bug_store import JsonlBugStore

__all__ = ["bugs_app"]

bugs_app = typer.Typer(help="Event-sourced JSONL bug telemetry (append/status/stats).")

#: The packaged schema id (file lives at ``public/schemas/bugs/<id>.schema.json``).
_SCHEMA_ID = "bug-event-v1"

#: v0.4.4 FR23 (T-044-62) — the resolved-evidence gate. The three fields must each be
#: independently checkable; a bare non-empty string is not enough (that was exactly
#: the v0.1.73 FR3 gap: 132/438 on-disk `resolved` events carried no evidence at all,
#: and 70 more were closed with one template string that cleared the old >=20-char
#: floor without saying anything checkable).
_EVIDENCE_MIN_LEN = 5
_DIFF_DIRECTION_RE = re.compile(r"^(net-negative|net-positive|net-neutral):\s*\S.*$", re.IGNORECASE)


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory (explicit flag, else the resolution authority)."""
    return resolve_specs_dir_for_cli(specs_dir)


def _resolve_append_specs_dir(specs_dir: str | None, event_context: str | None) -> Path:
    """Resolve the ledger destination for ``bugs append``.

    Bug ``bugs-append-ledger-ignores-context-flag``: the event's ``--context`` field is
    a ROUTING key, not an inert label — an event whose context names B must never land
    silently in the bound context A's ledger. Order: explicit ``--specs-dir`` (always
    wins, unchanged) → ``--context``'s own ``repos/<name>/specs`` (refused loudly when
    that directory does not exist) → the pre-existing bound-context/cwd resolution.
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
                "refusing to land the event in a different context's ledger."
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
        help="resolved (legacy free-text narrative, v0.1.73 FR3 — superseded as the "
        "blocking check by FR23/v0.4.4; optional). See --evidence-loop/--evidence-seam/"
        "--evidence-diff for the checkable evidence FR23 requires.",
    ),
    evidence_loop: str | None = typer.Option(
        None,
        "--evidence-loop",
        help="resolved (FR23, REQUIRED, v0.4.4): the red-loop command that reproduced "
        "the bug on the executed path, before any hypothesis.",
    ),
    evidence_seam: str | None = typer.Option(
        None,
        "--evidence-seam",
        help="resolved (FR23, REQUIRED, v0.4.4): the test file/node (the regression "
        "seam) that pins the fix.",
    ),
    evidence_diff: str | None = typer.Option(
        None,
        "--evidence-diff",
        help="resolved (FR23, REQUIRED, v0.4.4): the diff direction on the touched "
        "feature — lines/branches/flags added vs removed. Prefix with "
        "'net-negative:'/'net-positive:'/'net-neutral:'. A net-positive value routes "
        "to a software-architect review before the commit; it does not block the "
        "append.",
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

    ADDITIVE and never concurrency-blocked. On schema-validation failure nothing is written and the
    command exits non-zero with the validation message.
    """
    target = _resolve_append_specs_dir(specs_dir, context)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        raise typer.Exit(code=1)

    # v0.4.4 FR23 (T-044-62, replaces v0.1.73 FR3's blanket >=20-char free-text floor):
    # a `resolved` event is refused BEFORE anything is written unless it carries three
    # INDEPENDENTLY checkable fields — the red-loop command, the test seam, and the
    # diff direction on the touched feature. Each is checked on its own so the message
    # always names exactly what is missing (A23.1); this is the ONE validation on the
    # existing append path — no second command, no bypass flag (A23.5).
    if event is BugEventKind.RESOLVED:
        missing: list[str] = []
        if evidence_loop is None or len(evidence_loop.strip()) < _EVIDENCE_MIN_LEN:
            missing.append("--evidence-loop (the red-loop command that reproduced the bug)")
        if evidence_seam is None or len(evidence_seam.strip()) < _EVIDENCE_MIN_LEN:
            missing.append("--evidence-seam (the test file/node that pins the regression)")
        if evidence_diff is None or not _DIFF_DIRECTION_RE.match(evidence_diff.strip()):
            missing.append(
                "--evidence-diff (the diff direction on the touched feature: prefix "
                "'net-negative:'/'net-positive:'/'net-neutral:', lines/branches/flags "
                "added vs removed)"
            )
        if missing:
            typer.echo(
                "[error] resolved requires three checkable evidence fields (FR23 "
                "resolution law); missing: " + "; ".join(missing),
                err=True,
            )
            raise typer.Exit(code=1)

    # v0.4.3 T-043-18/FR14 (mirrors the resolved/--resolution-evidence precedent
    # above): a picked event without --release is refused BEFORE anything is
    # written — schema and CLI both require it in the SAME change, safe only because
    # zero historical picked events exist (architect ruling, 2026-08-17T16:15:00Z).
    if event is BugEventKind.PICKED and not release:
        typer.echo(
            "[error] picked requires --release (the M.m.p release or hotfix id the "
            "bug is reserved under — bug-reservation law).",
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
        evidence_loop=evidence_loop,
        evidence_seam=evidence_seam,
        evidence_diff=evidence_diff,
    ).redact()

    payload = model.to_dict()
    try:
        _load_validator().validate(payload)
    except ValidationError as exc:
        typer.echo(f"[error] bug event invalid: {exc.message}", err=True)
        raise typer.Exit(code=1) from exc

    # The service is the enforced side of the stream-coherence authority — appending
    # through the raw store here is what let incoherent events into the ledger.
    service = BugService(JsonlBugStore(target / "bugs"))
    try:
        path = service.append_event(model)
    except ValueError as exc:
        typer.echo(f"[error] bug event incoherent: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"[ok] appended {event.value} for {bug_id} -> {path}")
    # FR23: a net-positive diff on the touched feature does not hard-block the append
    # — it routes. The route is a printed advisory, not a second refusal: the append
    # already succeeded above.
    if (
        event is BugEventKind.RESOLVED
        and evidence_diff is not None
        and evidence_diff.strip().lower().startswith("net-positive:")
    ):
        typer.echo("[notice] net-positive diff -> dispatch software-architect before the commit")


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
        line = f"{state.bug_id}\t{state.status}\t{severity}"
        # v0.4.3 T-043-18/FR14: surfaces picked-by ONLY when non-empty — a never-picked
        # bug's line stays byte-identical to before (backward-compatible output shape).
        if state.picked_by:
            line += f"\tpicked-by:{','.join(state.picked_by)}"
        typer.echo(line)
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
