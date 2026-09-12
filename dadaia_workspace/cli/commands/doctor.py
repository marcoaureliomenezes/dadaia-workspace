"""CLI command: ``dadaia doctor`` — the ONE compliance surface (0.4.7 FR5, T-047-02).

Three sections in fixed order — ``workspace`` (zones, root, harness dirs), ``specs``
(the SPEC-DOC + RELEASE-TREE rules), ``ledgers`` (BL-SCHEMA/CONFLICT/STALE) — collected
from one rule registry (:mod:`dadaia_workspace.core.doctor_rules`), rendered by one
grammar, scored by one formula, exited by one rule. ``dadaia specs doctor`` and
``dadaia backlog doctor`` are DELETED, not aliased: three commands with three finding
types, three renderings and three exit rules were the structural cause of a doctor bug
family in which each doctor could independently report health over a tree the other two
never read.

This module is the ONE place the three sections meet — the features stay mutually
independent (each contributes rules over its own context and its own issue type, with
its own adapter at the seam).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import typer

from dadaia_workspace import container
from dadaia_workspace.cli._backlog_roots import resolve_backlog_roots
from dadaia_workspace.cli._specs_resolution import (
    resolve_context_for_cli,
    resolve_context_specs_dir_for_cli,
    resolve_specs_dir_for_cli,
)
from dadaia_workspace.cli.redact import ContextRedactor
from dadaia_workspace.core.doctor_rules import (
    Rule,
    SectionFinding,
    SectionReport,
    merge_sections,
    run_section,
    total_line,
)
from dadaia_workspace.core.exceptions import SchemaVersionError, WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.backlog import doctor as backlog_doctor
from dadaia_workspace.features.spec_context.doctor import DoctorService, workspace_rules
from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs import ledgers as specs_ledgers
from dadaia_workspace.features.specs.doctor_types import SpecsDoctorIssue
from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES
from dadaia_workspace.features.specs.rules import render_fix_help

app = typer.Typer(help="Diagnose and repair workspace, specs and ledger compliance.")

#: Canonical templates directory — inside the installed package.
_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "public" / "templates"


# ── redaction (unchanged: a render-boundary concern, never seen by a doctor) ─────


def _resolve_caller_context_and_slug(workspace_root: Path) -> tuple[str | None, str | None]:
    """Best-effort resolution of the caller's own context name + repo slug (SPEC v0.9.0
    FR8a: "other than the caller's resolved context"). Never raises — an unresolved
    caller (no bind, no DADAIA_CONTEXT, cwd outside any repo) simply means nothing is
    excluded, so `--redact` masks every context/slug it encounters."""
    try:
        name = resolve_context_for_cli(None)
    except ValueError:
        return None, None
    slug: str | None = None
    try:
        for ctx in container.build_spec_context_service(workspace_root).list_all():
            if ctx.name == name:
                slug = ctx.repo_slug
                break
    except (WorkspaceNotInitializedError, SchemaVersionError):
        pass
    return name, slug


def _build_redactor(workspace_root: Path) -> ContextRedactor:
    """Candidates = every known registered context name/repo slug, PLUS every context
    name that appears in an advisory presence record (`[stale-presence] context
    '<name>'`, PRESENCE-GC) — a presence record can outlive its context's registry
    entry, so the registry alone is not enough to cover A8.1's PRESENCE-GC line."""
    from dadaia_workspace.features.spec_context import presence

    caller_name, caller_slug = _resolve_caller_context_and_slug(workspace_root)
    try:
        contexts = container.build_spec_context_service(workspace_root).list_all()
    except (WorkspaceNotInitializedError, SchemaVersionError):
        contexts = []
    candidates: list[str] = []
    for ctx in contexts:
        candidates.append(ctx.name)
        candidates.append(ctx.repo_slug)
    candidates.extend(ref.context for ref in presence.stale_records(workspace_root))
    return ContextRedactor(candidates, exclude=(caller_name, caller_slug))


# ── the three sections ──────────────────────────────────────────────────────────


def _workspace_section(service: DoctorService, *, expired_only: bool) -> SectionReport:
    """`workspace`: the instance walk. Its findings already ARE the normalized record —
    the feature owns the translation of its own verdict vocabulary, so the adapter here
    is the identity and no mapping table exists anywhere."""
    return run_section(
        "workspace",
        "entries",
        workspace_rules(expired_only=expired_only),
        service,
        lambda _rule, finding: finding,
    )


def _specs_render(
    rule: Rule[SpecsDoctor, SpecsDoctorIssue], issue: SpecsDoctorIssue
) -> SectionFinding:
    """The compliance unit of the `specs` section is the RULE: a rule that emitted no
    error or warning is canonical, whatever the size of the tree it walked."""
    location = f" ({issue.path})" if issue.path else ""
    return SectionFinding(
        code=issue.code,
        verdict=issue.severity.value,
        message=f"{issue.description}{location}",
        canonical=False,
        error=issue.severity is Severity.ERROR,
        unit=rule.codes[0],
    )


def _empty_section(name: str, unit: str) -> SectionReport:
    """A section with nothing to read: no findings, no units, nothing to fail."""
    return SectionReport(name=name, unit=unit, findings=(), canonical=0, total=0)


def _specs_section(doctor: SpecsDoctor | None) -> SectionReport:
    if doctor is None:
        return _empty_section("specs", "rules")
    return run_section(
        "specs",
        "rules",
        SPECS_RULES,
        doctor,
        _specs_render,
        total_units=len(SPECS_RULES),
    )


def _ledgers_render(
    _rule: Rule[backlog_doctor.DoctorContext, backlog_doctor.Finding],
    finding: backlog_doctor.Finding,
) -> SectionFinding:
    """The compliance unit of the `ledgers` section is the RECORD (a backlog item). A
    document-level error carries no record: it disqualifies nothing and still fails the
    run."""
    slug = f" [{finding.slug}]" if finding.slug else ""
    return SectionFinding(
        code=finding.code.value,
        verdict=finding.severity.value,
        message=f"{slug.strip()} {finding.message}".strip(),
        canonical=False,
        error=finding.severity is backlog_doctor.Severity.ERROR,
        unit=finding.slug,
    )


def _ledger_schema_render(
    _rule: Rule[specs_ledgers.LedgersContext, specs_ledgers.LedgerIssue],
    issue: specs_ledgers.LedgerIssue,
) -> SectionFinding:
    """The compliance unit of a schema-validated ledger is the RECORD, located
    `path:line` — the same unit the backlog rules score, so the two rule groups add
    into one score line."""
    return SectionFinding(
        code=issue.code,
        verdict=Severity.ERROR.value,
        message=f"{issue.unit} {issue.message}",
        canonical=False,
        error=True,
        unit=issue.unit,
    )


def _ledgers_section(
    specs_dir: Path | None, source_root: str | None, alias_map: str | None
) -> SectionReport:
    """The `ledgers` section: the backlog document's BL-* rules plus one schema rule per
    committed governance ledger (0.4.7 FR6). Two features contribute, neither imports
    the other, and the two reports merge into one section here — the composition root."""
    from dadaia_workspace.cli.anchors import derive_cli_anchors
    from dadaia_workspace.core.models.backlog import BacklogHistoRecord, ConsumedBacklogHistoRecord
    from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

    if specs_dir is None:
        return _empty_section("ledgers", "records")

    src, catalog_path, alias_map_path = resolve_backlog_roots(specs_dir, source_root, alias_map)
    context = backlog_doctor.build_context(
        specs_dir=specs_dir,
        source_root=src,
        catalog_path=catalog_path,
        alias_map_path=alias_map_path,
        cli_anchors=derive_cli_anchors(),
        histo_store=JsonlRecordStore(
            specs_dir / "backlog" / "_archive" / "backlog_histo.jsonl",
            to_dict=BacklogHistoRecord.to_dict,
            from_dict=BacklogHistoRecord.from_dict,
        ),
        consumed_histo_store=JsonlRecordStore(
            specs_dir / "backlog" / "_archive" / "consumed_backlog_histo.jsonl",
            to_dict=ConsumedBacklogHistoRecord.to_dict,
            from_dict=ConsumedBacklogHistoRecord.from_dict,
        ),
    )
    ledgers_context = specs_ledgers.build_ledgers_context(specs_dir)
    return merge_sections(
        [
            run_section(
                "ledgers",
                "records",
                backlog_doctor.RULES,
                context,
                _ledgers_render,
                total_units=len(context.items),
            ),
            run_section(
                "ledgers",
                "records",
                specs_ledgers.RULES,
                ledgers_context,
                _ledger_schema_render,
                total_units=ledgers_context.total_records,
            ),
        ]
    )


# ── composition ─────────────────────────────────────────────────────────────────


def _build_specs_doctor(specs_dir: Path | None, public_dir: str | None) -> SpecsDoctor | None:
    """``None`` in, ``None`` out: a workspace with no specs tree has no specs doctor."""
    if specs_dir is None:
        return None
    resolved_public = Path(public_dir).resolve() if public_dir else _detect_public_dir(specs_dir)
    return SpecsDoctor(
        specs_dir,
        public_dir=resolved_public,
        templates_dir=_TEMPLATES_DIR,
        # repo_root: specs/ sits directly at the repo root — the same convention
        # _resolve_live_shas documents; feeds SPEC-DOC-028 and SPEC-DOC-045.
        repo_root=specs_dir.parent,
        live_shas=_resolve_live_shas(specs_dir),
        bug_store_factory=container.build_bug_record_store,
    )


def _detect_public_dir(specs_dir: Path) -> Path | None:
    """``<repo-root>/specs/`` alongside ``<repo-root>/dadaia_workspace/public/``."""
    candidate = specs_dir.parent / "dadaia_workspace" / "public"
    return candidate if candidate.is_dir() else None


def _resolve_live_shas(specs_dir: Path) -> tuple[str, ...] | None:
    """The live verdict-sha set (head, first parent, develop tip) — plain data fed into
    SPEC-DOC-044's stale-verdict check through the ONE
    ``features.chokepoints.verdict.live_verdict_shas`` rule the pre-push gate also uses.
    ``None`` (not a git repo, unresolvable HEAD or integration tip) keeps that check
    silent rather than letting ``--fix`` delete staged ship evidence.
    """
    from dadaia_workspace.features.chokepoints.verdict import INTEGRATION_TIP_REF, live_verdict_shas

    repo_root = specs_dir.parent
    reader = container.build_git_object_reader()
    try:
        head_sha = reader.resolve_ref(repo_root, "HEAD")
        if head_sha is None or reader.resolve_ref(repo_root, INTEGRATION_TIP_REF) is None:
            return None
        return live_verdict_shas(reader, repo_root, head_sha)
    except Exception:  # noqa: BLE001 — a failed git read degrades to None, never a crash
        return None


def _resolve_specs_dir(specs_dir: str | None, context: str | None) -> Path | None:
    """The tree the `specs`/`ledgers` sections read, or ``None`` when this workspace has
    none to read — an unbound session in a workspace with no specs tree still gets its
    `workspace` section (the SessionStart reaper runs exactly there). An EXPLICIT
    ``--specs-dir``/``--context`` that cannot be resolved still refuses: naming a tree
    that is not there is an operator error, not an absent tree.
    """
    if specs_dir is not None and context is not None:
        raise typer.BadParameter("Pass either --context or --specs-dir, not both.")
    if context is not None:
        return resolve_context_specs_dir_for_cli(resolve_workspace_root(), context)
    if specs_dir is not None:
        return resolve_specs_dir_for_cli(specs_dir)
    try:
        return resolve_specs_dir_for_cli(None)
    except (ValueError, typer.BadParameter):
        return None


@app.callback(invoke_without_command=True)
def doctor(
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from the bound context session.",
    ),
    context: str | None = typer.Option(
        None,
        "--context",
        help="Context name; resolves repos/<context>/specs. Mutually exclusive with --specs-dir.",
    ),
    public_dir: str | None = typer.Option(
        None,
        "--public-dir",
        help=(
            "Path to dadaia_workspace/public/, enabling the template and scaffold drift "
            "checks. Default: auto-detected from specs_dir/../dadaia_workspace/public/."
        ),
    ),
    source_root: str | None = typer.Option(
        None,
        "--source-root",
        help="Source root for the ledgers section's code-anchor derivation. Default: the repo root.",
    ),
    alias_map: str | None = typer.Option(
        None,
        "--alias-map",
        help="Alias-map path for the ledgers section. Default: workspace .dadaia/states/.",
    ),
    fix: bool = typer.Option(False, "--fix", help=render_fix_help()),
    expired_only: bool = typer.Option(
        False,
        "--expired-only",
        help=(
            "Scope the run to TTL-expired entries: the workspace section reports that "
            "lane only and --fix stops after deleting them."
        ),
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Machine-readable output: sections, compliance, fixed."
    ),
    quiet: bool = typer.Option(
        False, "--quiet", help="Print only what --fix deleted (nothing on a compliant run)."
    ),
    redact: bool = typer.Option(
        False,
        "--redact",
        help=(
            "Mask every Spec Context name and repo slug other than this caller's "
            "resolved context (SPEC v0.9.0 FR8a). Default output is unchanged."
        ),
    ),
) -> None:
    """Report workspace, specs and ledger compliance; optionally repair."""
    workspace_root = resolve_workspace_root()
    try:
        service = container.build_doctor_service(workspace_root)
    except WorkspaceNotInitializedError:
        typer.echo("Error: Workspace not initialized. Run 'dadaia init' first.", err=True)
        raise typer.Exit(1) from None
    target = _resolve_specs_dir(specs_dir, context)
    specs_doctor = _build_specs_doctor(target, public_dir)

    fixed = _apply_fixes(service, specs_doctor, fix=fix, expired_only=expired_only)
    reports = [
        _workspace_section(service, expired_only=expired_only),
        _specs_section(specs_doctor),
        _ledgers_section(target, source_root, alias_map),
    ]
    # Render boundary ONLY: no doctor ever sees the redactor; every finding and fix action
    # keeps carrying true names inside the sections themselves.
    render = _build_redactor(workspace_root).text if redact else _identity

    if json_out:
        typer.echo(_json_payload(reports, fixed, render, target))
    elif quiet:
        for action in fixed:
            typer.echo(render(action))
    else:
        _emit_human(reports, fixed, render, fix=fix)

    if any(report.failed for report in reports):
        raise typer.Exit(1)


def _identity(text: str) -> str:
    return text


def _apply_fixes(
    service: DoctorService, specs_doctor: SpecsDoctor | None, *, fix: bool, expired_only: bool
) -> list[str]:
    """The `--fix` scope, unchanged by the fold: the workspace repairs plus the specs
    rules' own `FIX_BY_CODE` fixes; `--expired-only` stops after the TTL deletions. The
    `ledgers` section has no fix."""
    if not fix:
        return []
    fixed = list(service.fix(expired_only=expired_only))
    if not expired_only and specs_doctor is not None:
        fixed.extend(f"[specs] {issue.code}: {issue.path}" for issue in specs_doctor.fix())
    return fixed


def _json_payload(
    reports: list[SectionReport],
    fixed: list[str],
    render: Callable[[str], str],
    specs_dir: Path | None,
) -> str:
    return json.dumps(
        {
            # `specs_dir` names the tree this run resolved — the one piece of run
            # identity a machine consumer cannot derive, and the seam two resolution
            # contract tests assert against (`bind-resolution-seam-is-a-single-home`).
            "specs_dir": str(specs_dir) if specs_dir else None,
            "sections": {
                report.name: {
                    "findings": [
                        {"code": f.code, "verdict": f.verdict, "message": render(f.message)}
                        for f in report.printable
                    ],
                    "compliance": {
                        "canonical": report.canonical,
                        "total": report.total,
                        "percent": report.percent,
                    },
                }
                for report in reports
            },
            "compliance": _total_compliance(reports),
            "fixed": [render(action) for action in fixed],
        },
        indent=2,
    )


def _emit_human(
    reports: list[SectionReport], fixed: list[str], render: Callable[[str], str], *, fix: bool
) -> None:
    """One line per finding — `<CODE> <verdict> <message>`, each finding's OWN verdict
    word — then that section's score, then the run's total."""
    for report in reports:
        for finding in report.printable:
            typer.echo(render(f"{finding.code} {finding.verdict} {finding.message}"))
        typer.echo(report.score_line())
    if fix:
        typer.echo(f"\nApplied {len(fixed)} repair(s):")
        for action in fixed:
            typer.echo(f"  - {render(action)}")
    typer.echo(total_line(reports))


def _total_compliance(reports: list[SectionReport]) -> dict[str, int]:
    canonical = sum(r.canonical for r in reports)
    total = sum(r.total for r in reports)
    return {
        "canonical": canonical,
        "total": total,
        "percent": round(100 * canonical / total) if total else 100,
    }
