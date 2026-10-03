"""CLI command: ``dadaia doctor`` — the ONE compliance surface (0.4.7 FR5, T-047-02).

Three sections in fixed order — ``workspace`` (zones, root, harness dirs), ``specs``
(the SPEC-DOC rules), ``ledgers`` (BL-SCHEMA/CONFLICT/STALE) — collected
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
import re
from collections.abc import Callable
from pathlib import Path

import typer

from dadaia_workspace import container
from dadaia_workspace.cli._specs_resolution import (
    alive_context_trees,
    own_bind_for_cli,
    resolve_context_for_cli,
    resolve_context_specs_dir_for_cli,
    resolve_specs_dir_for_cli,
)
from dadaia_workspace.cli.help_digest import command_paths
from dadaia_workspace.cli.redact import build_context_redactor
from dadaia_workspace.core.doctor_rules import (
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
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.backlog import doctor as backlog_doctor
from dadaia_workspace.features.spec_context.doctor import DoctorService, workspace_rules
from dadaia_workspace.features.specs import SpecsDoctor, doctor_adr
from dadaia_workspace.features.specs.doctor_types import finding_path
from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES
from dadaia_workspace.features.specs.rules import render_fix_help
from dadaia_workspace.features.workspace import onboarding

app = typer.Typer(help="Diagnose and repair workspace, specs and ledger compliance.")

#: Canonical templates directory — inside the installed package.
_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "public" / "templates"


# ── the three sections ──────────────────────────────────────────────────────────


def _workspace_section(
    service: DoctorService | None, root: Path | None, scope: str | None, *, expired_only: bool
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
        root,
    )


def _empty_section(name: str) -> SectionReport:
    """A section with nothing to read: no findings, nothing to fail."""
    return SectionReport(name=name, findings=())


def _specs_section(doctor: SpecsDoctor | None, root: Path | None) -> SectionReport:
    if doctor is None:
        return _empty_section("specs")
    return run_section(
        "specs",
        SPECS_RULES,
        doctor,
        root,
        doctor.specs_dir,
    )


def _ledgers_section(
    root: Path | None,
    specs_dir: Path | None,
) -> SectionReport:
    """The `ledgers` section — three contributors, one name.

    The backlog document's BL-* rules, the ADR ledger's own reader, and the five ledger
    SCRIPTS: each ledger with a writer script is validated by THAT script's
    `check`, run as a subprocess here. The doctor holds no second implementation of any
    ledger schema — this is the one delegation point.
    """
    from dadaia_workspace.infrastructure.ledger_scripts import script_findings

    if specs_dir is None:
        return _empty_section("ledgers")

    tracked = container.build_git_client().tracked(specs_dir.parent)
    context = backlog_doctor.build_context(specs_dir, tracked)
    return merge_sections(
        [
            run_section("ledgers", backlog_doctor.RULES, context, root, specs_dir),
            run_section(
                "ledgers",
                doctor_adr.LEDGER_RULES,
                specs_dir,
                root,
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
        # repo_root: specs/ sits directly at the repo root; feeds MEM-DRIFT-2.
        repo_root=specs_dir.parent,
        # The ONE Typer walk (0.4.7 FR2), done here and handed in as plain data;
        # `features` never imports `cli`.
        command_paths=command_paths(),
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
        raise typer.Exit(1) from None
    target = resolve_context_specs_dir_for_cli(workspace_root, name)
    # The ONE place a context's tree is resolved: a tree `specs init` has not stamped yet
    # is onboarding level 2 — nothing for the specs/ledgers sections to judge (AC3.1).
    return (
        workspace_root,
        service,
        name,
        target if target and onboarding.specs_ready(target) else None,
    )


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
    try:
        trees = alive_context_trees(workspace_root)
        bind, session = own_bind_for_cli()
    except SchemaVersionError:  # `check` reports REG-SCHEMA; no next step is guessed
        return _empty_section("workspace")
    step = onboarding.next_step(
        workspace_root, trees, scope, None if session is None else bool(bind)
    )
    if step is None:
        return _empty_section("workspace")
    finding = SectionFinding(
        code=onboarding.CODE,
        verdict="info",
        message=step.text().split("\n")[0],
        canonical=False,
        error=False,
        fix=step.command,
        extra=(("step", step.id), ("kind", step.kind)),
    )
    return SectionReport(name="workspace", findings=(finding,))


def _render_for(workspace_root: Path | None, *, redact: bool) -> Callable[[str], str]:
    """The render boundary: the redactor over the instance's known names and paths, or
    the identity — no instance holds no names to mask."""
    if redact and workspace_root is not None:
        try:
            contexts = container.build_spec_context_service(workspace_root).list_all()
        except (WorkspaceNotInitializedError, SchemaVersionError):
            contexts = []
        redactor = build_context_redactor(contexts)  # paths print workspace-relative:
        root = re.compile(re.escape(f"{workspace_root.as_posix()}/").replace("/", r"[\\/]"))
        return lambda text: redactor.text(root.sub("", text))  # either separator matches
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
    fix: bool = typer.Option(False, "--fix", help=render_fix_help()),
    expired_only: bool = typer.Option(
        False,
        "--expired-only",
        help=(
            "Scope the run to the workspace TTL lane: the workspace section reports "
            "only expired entries and --fix deletes only those and stale session records "
            "— no slop move, no repo walk, no specs repairs (the SessionStart lane)."
        ),
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Machine-readable output: sections and fixed."
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Print only what --fix did and exit 0 — no report is built.",
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

    fixed = _apply_fixes(service, specs_doctor, fix=fix, expired_only=expired_only)
    render = _render_for(workspace_root, redact=redact)
    if quiet:
        for action in fixed:
            typer.echo(render(action))
        return
    reports = [
        merge_sections(
            [
                _workspace_section(service, workspace_root, scope, expired_only=expired_only),
                _onboarding_section(workspace_root, scope, expired_only=expired_only),
            ]
        ),
        _specs_section(specs_doctor, workspace_root),
        _ledgers_section(workspace_root, target),
    ]
    # Render boundary ONLY: no doctor ever sees the redactor; every finding and fix action
    # keeps carrying true names inside the sections themselves.
    if json_out:
        typer.echo(_json_payload(reports, fixed, render, target))
    else:
        _emit_human(reports, fixed, render, fix=fix)

    if any(report.failed for report in reports):
        raise typer.Exit(1)


def _identity(text: str) -> str:
    return text


def _apply_fixes(
    service: DoctorService | None,
    specs_doctor: SpecsDoctor | None,
    *,
    fix: bool,
    expired_only: bool,
) -> list[str]:
    """The `--fix` scope: the workspace repairs, the specs rules' own `FIX_BY_CODE`
    fixes, and the `ledgers` rules that carry one. Fixes run BEFORE the sections are
    built, so what the run then reports is the post-repair truth.

    `--expired-only` runs `service.expire()` — `fix()`'s first step alone — and skips the
    specs and ledgers repairs: the SessionStart lane costs one lstat per zone entry."""
    if not fix:
        return []
    fixed = [] if service is None else service.expire() if expired_only else service.fix()
    if not expired_only and specs_doctor is not None:
        fixed.extend(f"[specs] {issue.code}: {finding_path(issue)}" for issue in specs_doctor.fix())
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
            "specs_dir": render(str(specs_dir)) if specs_dir else None,
            "sections": {
                report.name: {
                    "findings": [
                        {
                            "code": f.code,
                            "verdict": f.verdict,
                            "message": render(f.message),
                            "fix": render(f.fix),
                            **{key: render(value) for key, value in f.extra},
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
