"""CLI command: ``dadaia doctor`` — the ONE compliance surface (0.4.7 FR5, T-047-02).

Three sections in fixed order — ``workspace`` (zones, root, harness dirs), ``specs``
(the SPEC-DOC + RELEASE-TREE rules), ``ledgers`` (BL-SCHEMA/CONFLICT/STALE) — collected
from one rule registry (:mod:`dadaia_workspace.core.doctor_rules`), rendered by one
grammar, exited by one rule. ``dadaia specs doctor`` and
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
    alive_context_trees,
    resolve_context_for_cli,
    resolve_context_specs_dir_for_cli,
    resolve_specs_dir_for_cli,
)
from dadaia_workspace.cli.help_digest import command_paths
from dadaia_workspace.cli.redact import ContextRedactor
from dadaia_workspace.core.doctor_rules import (
    Rule,
    SectionFinding,
    SectionReport,
    merge_sections,
    render_finding,
    run_section,
)
from dadaia_workspace.core.exceptions import (
    ContextNotFoundError,
    SchemaVersionError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.kernel_tunables import DADAIA_BIN
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.backlog import doctor as backlog_doctor
from dadaia_workspace.features.spec_context.doctor import DoctorService, workspace_rules
from dadaia_workspace.features.specs import Severity, SpecsDoctor, doctor_adr
from dadaia_workspace.features.specs.doctor_types import SpecsDoctorIssue
from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES
from dadaia_workspace.features.specs.rules import render_fix_help
from dadaia_workspace.features.workspace import onboarding

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
    """Candidates = every known registered context name/repo slug."""
    caller_name, caller_slug = _resolve_caller_context_and_slug(workspace_root)
    try:
        contexts = container.build_spec_context_service(workspace_root).list_all()
    except (WorkspaceNotInitializedError, SchemaVersionError):
        contexts = []
    candidates: list[str] = []
    for ctx in contexts:
        candidates.append(ctx.name)
        candidates.append(ctx.repo_slug)
    return ContextRedactor(candidates, exclude=(caller_name, caller_slug))


# ── the three sections ──────────────────────────────────────────────────────────


def _workspace_section(
    service: DoctorService | None, scope: str | None, *, expired_only: bool
) -> SectionReport:
    """`workspace`: the instance walk. Its findings already ARE the normalized record —
    the feature owns the translation of its own verdict vocabulary, so the adapter here
    is the identity and no mapping table exists anywhere. No instance around the run
    (CI over a bare checkout), nothing to walk: an empty section, never a refusal."""
    if service is None:
        return _empty_section("workspace")
    return run_section(
        "workspace",
        workspace_rules(expired_only=expired_only, context=scope),
        service,
        lambda _rule, finding: finding,
    )


def _specs_render[C](rule: Rule[C, SpecsDoctorIssue], issue: SpecsDoctorIssue) -> SectionFinding:
    """Render one specs-doctor issue as a section finding."""
    location = f" ({issue.path})" if issue.path else ""
    return SectionFinding(
        code=issue.code,
        verdict=issue.severity.value,
        message=f"{issue.description}{location}",
        canonical=False,
        error=issue.severity is Severity.ERROR,
    )


def _empty_section(name: str) -> SectionReport:
    """A section with nothing to read: no findings, nothing to fail."""
    return SectionReport(name=name, findings=())


def _specs_section(doctor: SpecsDoctor | None) -> SectionReport:
    if doctor is None:
        return _empty_section("specs")
    return run_section(
        "specs",
        SPECS_RULES,
        doctor,
        _specs_render,
    )


def _ledgers_render(
    _rule: Rule[backlog_doctor.DoctorContext, backlog_doctor.Finding],
    finding: backlog_doctor.Finding,
) -> SectionFinding:
    """Render one backlog finding as a section finding."""
    slug = f" [{finding.slug}]" if finding.slug else ""
    return SectionFinding(
        code=finding.code.value,
        verdict=finding.severity.value,
        message=f"{slug.strip()} {finding.message}".strip(),
        canonical=False,
        error=finding.severity is backlog_doctor.Severity.ERROR,
    )


def _ledgers_section(
    specs_dir: Path | None,
    source_root: str | None,
    alias_map: str | None,
) -> SectionReport:
    """The `ledgers` section — three contributors, one name.

    The backlog document's BL-* rules, the ADR ledger's own reader, and the five ledger
    SCRIPTS: each ledger with a writer script is validated by THAT script's
    `check`, run as a subprocess here. The doctor holds no second implementation of any
    ledger schema — this is the one delegation point.
    """
    from dadaia_workspace.cli.anchors import derive_cli_anchors
    from dadaia_workspace.core.models.histo import HistoRecord
    from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore
    from dadaia_workspace.infrastructure.ledger_scripts import script_findings

    if specs_dir is None:
        return _empty_section("ledgers")

    src, catalog_path, alias_map_path = resolve_backlog_roots(specs_dir, source_root, alias_map)
    context = backlog_doctor.build_context(
        specs_dir=specs_dir,
        source_root=src,
        catalog_path=catalog_path,
        alias_map_path=alias_map_path,
        cli_anchors=derive_cli_anchors(),
        histo_store=JsonlRecordStore(
            specs_dir / "backlog" / "_archive" / "backlog_histo.jsonl",
            to_dict=HistoRecord.to_dict,
            from_dict=HistoRecord.from_dict,
        ),
    )
    return merge_sections(
        [
            run_section(
                "ledgers",
                backlog_doctor.RULES,
                context,
                _ledgers_render,
            ),
            run_section(
                "ledgers",
                doctor_adr.LEDGER_RULES,
                specs_dir,
                _specs_render,
            ),
            SectionReport(name="ledgers", findings=tuple(script_findings(specs_dir))),
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
        # repo_root: specs/ sits directly at the repo root; feeds SPEC-DOC-028 and SPEC-DOC-045.
        repo_root=specs_dir.parent,
        # The ONE Typer walk (0.4.7 FR2), done here and handed in as plain data;
        # `features` never imports `cli`.
        command_paths=command_paths(),
        bug_store_factory=container.build_bug_record_store,
    )


def _detect_public_dir(specs_dir: Path) -> Path | None:
    """``<repo-root>/specs/`` alongside ``<repo-root>/dadaia_workspace/public/``."""
    candidate = specs_dir.parent / "dadaia_workspace" / "public"
    return candidate if candidate.is_dir() else None


def _resolve_run(
    specs_dir: str | None, context: str | None
) -> tuple[Path | None, DoctorService | None, str | None, Path | None]:
    """What this run reads: ``(workspace_root, service, context, specs_dir)``. No instance
    around the run (CI over a bare checkout, no ``.dadaia/states/`` above its cwd) leaves
    the first three ``None`` — an explicit ``--specs-dir`` still gets its `specs` and
    `ledgers` sections. Nothing to read at all is the one refusal; naming two trees is a
    usage error, judged before any resolution."""
    if specs_dir is not None and context is not None:
        raise typer.BadParameter("Pass either --context or --specs-dir, not both.")
    try:
        workspace_root = resolve_workspace_root()
    except WorkspaceNotInitializedError as exc:
        if context is None and specs_dir is not None:
            return None, None, None, resolve_specs_dir_for_cli(specs_dir)
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from None
    service = container.build_doctor_service(workspace_root)
    if specs_dir is not None:
        return workspace_root, service, None, resolve_specs_dir_for_cli(specs_dir)
    name = context or _bound_context()
    if name is None:
        return workspace_root, service, None, None
    try:
        container.build_spec_context_service(workspace_root).show(name)
    except ContextNotFoundError as exc:
        if context is None:  # a stale ambient bind is no bind — only a NAMED ghost refuses
            return workspace_root, service, None, None
        typer.echo(f"Error: {exc}", err=True)
        typer.echo(f"fix: {DADAIA_BIN} context list", err=True)
        raise typer.Exit(1) from None
    target = resolve_context_specs_dir_for_cli(workspace_root, name)
    # The ONE place a context's tree is resolved: a tree `specs init` has not stamped yet
    # is onboarding level 2 — nothing for the specs/ledgers sections to judge (AC3.1).
    return workspace_root, service, name, target if onboarding.specs_ready(target) else None


def _bound_context() -> str | None:
    try:
        return resolve_context_for_cli(None)
    except ValueError:
        return None


def _onboarding_section(
    workspace_root: Path | None, scope: str | None, *, expired_only: bool
) -> SectionReport:
    """The derived next step (FR6 AC6.1) as one info finding — never an error."""
    if workspace_root is None or expired_only:
        return _empty_section("workspace")
    step = onboarding.next_step(workspace_root, alive_context_trees(workspace_root), scope)
    if step is None:
        return _empty_section("workspace")
    finding = SectionFinding(
        code=onboarding.CODE,
        verdict="info",
        message=f"Next: {step.reason}",
        canonical=False,
        error=False,
        fix=step.command,
    )
    return SectionReport(name="workspace", findings=(finding,))


def _render_for(workspace_root: Path | None, *, redact: bool) -> Callable[[str], str]:
    """The render boundary: the redactor over the instance's known names, or the
    identity — no instance holds no names to mask."""
    if redact and workspace_root is not None:
        return _build_redactor(workspace_root).text
    return _identity


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
            "Scope the run to the workspace TTL lane: the workspace section reports "
            "only expired entries and --fix skips the specs repairs. The reaper lane "
            "itself is one lane and runs whole either way."
        ),
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Machine-readable output: sections and fixed."
    ),
    quiet: bool = typer.Option(
        False, "--quiet", help="Print only what --fix deleted (nothing on a compliant run)."
    ),
    redact: bool = typer.Option(
        False,
        "--redact",
        help=(
            "Mask every Spec Context name and repo slug other than this caller's "
            "resolved context. Default output is unchanged."
        ),
    ),
) -> None:
    """Report workspace, specs and ledger compliance; optionally repair."""
    workspace_root, service, scope, target = _resolve_run(specs_dir, context)
    specs_doctor = _build_specs_doctor(target, public_dir)

    fixed = _apply_fixes(
        service, specs_doctor, target, source_root, alias_map, fix=fix, expired_only=expired_only
    )
    reports = [
        merge_sections(
            [
                _workspace_section(service, scope, expired_only=expired_only),
                _onboarding_section(workspace_root, scope, expired_only=expired_only),
            ]
        ),
        _specs_section(specs_doctor),
        _ledgers_section(target, source_root, alias_map),
    ]
    # Render boundary ONLY: no doctor ever sees the redactor; every finding and fix action
    # keeps carrying true names inside the sections themselves.
    render = _render_for(workspace_root, redact=redact)

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
    service: DoctorService | None,
    specs_doctor: SpecsDoctor | None,
    specs_dir: Path | None,
    source_root: str | None,
    alias_map: str | None,
    *,
    fix: bool,
    expired_only: bool,
) -> list[str]:
    """The `--fix` scope: the workspace repairs, the specs rules' own `FIX_BY_CODE`
    fixes, and the `ledgers` rules that carry one. Fixes run BEFORE the sections are
    built, so what the run then reports is the post-repair truth.

    `--expired-only` is a SCOPE, never a second reaper: `service.fix()` is the one lane
    and runs whole either way (T-047-20 deleted the early stop it used to buy). All the
    flag still does on the write path is skip the specs and ledgers repairs, which keeps
    the SessionStart lane off the specs tree."""
    if not fix:
        return []
    fixed = list(service.fix()) if service is not None else []
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
                        {
                            "code": f.code,
                            "verdict": f.verdict,
                            "message": render(f.message),
                            "fix": render(f.fix),
                        }
                        for f in report.printable
                    ],
                }
                for report in reports
            },
            "fixed": [render(action) for action in fixed],
        },
        indent=2,
    )


def _emit_human(
    reports: list[SectionReport], fixed: list[str], render: Callable[[str], str], *, fix: bool
) -> None:
    """One line per finding — `<CODE> <verdict> <message>`, each finding's OWN verdict
    word; nothing else."""
    for report in reports:
        for finding in report.printable:
            typer.echo(render(render_finding(finding)))
    if fix:
        typer.echo(f"\nApplied {len(fixed)} repair(s):")
        for action in fixed:
            typer.echo(f"  - {render(action)}")
