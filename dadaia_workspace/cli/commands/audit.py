"""``dadaia audit`` — the two verbs an audit moves by (0.4.7 FR4).

- ``dadaia audit disposition <dir> <finding-id> --disposition …`` rewrites one finding's
  governance triple.
- ``dadaia audit close <dir> --sha <window-end-sha>`` archives a fully dispositioned
  audit: one histo record, then the directory is gone.

Composition only: the histo store and the operator denylist are built here, as every
other ledger verb builds them, so ``features/specs/audit.py`` stays free of
``container`` and of a second store location. Each verb writes exactly one governance
event (FR2).
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from dadaia_workspace import container
from dadaia_workspace.cli._governance_event import record_governance_event
from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.core.models.histo import HistoRecord
from dadaia_workspace.features.specs.audit import AuditError, close_audit, disposition_finding
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

audit_app = typer.Typer(help="Audit finding and archive commands.")

_SPECS_DIR_OPTION = typer.Option(
    None,
    "--specs-dir",
    help="Path to specs/ directory. Default: resolve from bound context session.",
)


def _target(specs_dir: str | None) -> Path:
    target = resolve_specs_dir_for_cli(specs_dir)
    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)
    return target


@audit_app.command("disposition")
def audit_disposition_cmd(
    audit: str = typer.Argument(..., help="The audit directory name under specs/audits/."),
    finding_id: str = typer.Argument(..., help="The finding id, e.g. 20260101-slug-F003."),
    disposition: str = typer.Option(
        ...,
        "--disposition",
        help="resolved | superseded (both need --release) | deferred | rejected (both need --reason).",
    ),
    release: str | None = typer.Option(
        None, "--release", help="The remediation release that closed the finding."
    ),
    reason: str | None = typer.Option(
        None, "--reason", help="Why the finding was not fixed (deferred/rejected)."
    ),
    specs_dir: str | None = _SPECS_DIR_OPTION,
) -> None:
    """Rewrite one finding's disposition, release and reason, in place.

    The ONE path (0.4.7 FR4): the triple used to be rewritten with file tools, so a
    finding could change verdict with nothing recording that it had. The finding's
    immutable core is refused by the record model, never by this command.
    """
    target = _target(specs_dir)
    try:
        record = disposition_finding(
            target, audit, finding_id, disposition=disposition, release=release, reason=reason
        )
    except (AuditError, KeyError, OSError) as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    record_governance_event(
        verb="disposition",
        ledger="audits",
        record_id=record.id,
        record=record.to_dict(),
        specs_dir=target,
    )
    typer.echo(f"[ok] {record.id} -> {record.disposition}")


@audit_app.command("close")
def audit_close_cmd(
    audit: str = typer.Argument(..., help="The audit directory name under specs/audits/."),
    sha: str = typer.Option(..., "--sha", help="The window-end commit sha the audit covered."),
    specs_dir: str | None = _SPECS_DIR_OPTION,
) -> None:
    """Archive one fully dispositioned audit: the histo record is appended LAST, then
    the directory is deleted — all-or-nothing (0.4.7 FR4)."""
    target = _target(specs_dir)
    store: JsonlRecordStore[HistoRecord] = JsonlRecordStore(
        target / "audits" / "_archive" / "audits_histo.jsonl",
        to_dict=HistoRecord.to_dict,
        from_dict=HistoRecord.from_dict,
    )
    try:
        record = close_audit(
            target,
            audit,
            sha=sha,
            histo_append=store.append,
            denylist_terms=container.load_denylist_terms(),
        )
    except (AuditError, OSError) as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    record_governance_event(
        verb="close",
        ledger="audits",
        record_id=record.id,
        record=record.to_dict(),
        specs_dir=target,
    )
    typer.echo(
        f"[ok] archived audit {record.id} ({record.summary}) -> "
        "specs/audits/_archive/audits_histo.jsonl"
    )
