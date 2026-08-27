"""CLI command group: `dadaia specs <verb>`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from dadaia_workspace import container
from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs.doctor_common import read_active_md
from dadaia_workspace.features.specs.doctor_types import SpecsDoctorIssue
from dadaia_workspace.features.specs.scaffolder import (
    scaffold,
    scaffold_release_segment,
)

app = typer.Typer(help="SDD release-lifecycle structural checks and helpers.")

# Sub-apps for the alpha/rc release-segment model (ADR-1/ADR-5).
release_app = typer.Typer(help="Release scaffolding (parent + alpha/rc segments).")
app.add_typer(release_app, name="release")
segment_app = typer.Typer(help="Open the next alpha/rc segment of the active release.")
app.add_typer(segment_app, name="segment")


def _write_active(specs_dir: Path, release: str, segment: str | None, phase: str) -> None:
    """Write specs/releases/ACTIVE.md (schema v2 — optional segment line)."""
    lines = [f"release: {release}"]
    if segment:
        lines.append(f"segment: {segment}")
    lines.append(f"phase: {phase}")
    (specs_dir / "releases" / "ACTIVE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    return resolve_specs_dir_for_cli(specs_dir)


def _resolve_public_dir(specs_dir: Path) -> Path | None:
    """Try to locate ``dadaia_workspace/public/`` relative to the specs directory.

    The conventional layout is:
    ``<repo-root>/specs/`` alongside ``<repo-root>/dadaia_workspace/public/``.

    Walk up from ``specs_dir`` until we find a sibling ``dadaia_workspace/public/``
    directory. Returns ``None`` when not found; template drift checks then use
    structure-only validation.
    """
    candidate = specs_dir.parent / "dadaia_workspace" / "public"
    if candidate.is_dir():
        return candidate
    return None


def _print_migration_hints(issues: list[SpecsDoctorIssue]) -> None:
    """Always surface TREE-1/TREE-2 migration hints (even under --fix)."""
    migration_issues = [i for i in issues if i.code in ("TREE-1", "TREE-2")]
    for mi in migration_issues:
        typer.echo(f"[MIGRATION] {mi.description}", err=True)


def _apply_doctor_fix(
    doctor_svc: SpecsDoctor, issues: list[SpecsDoctorIssue]
) -> list[SpecsDoctorIssue]:
    """Apply --fix, print what was fixed, and return the residual issue set."""
    fixed = doctor_svc.fix(issues)
    if fixed:
        typer.echo(f"[fix] Applied {len(fixed)} auto-fix(es):")
        for f_issue in fixed:
            typer.echo(f"  [fixed] {f_issue.code}: {f_issue.path}")
    return doctor_svc.check()


def _print_json_result(target: Path, issues: list[SpecsDoctorIssue]) -> None:
    payload = {
        "specs_dir": str(target),
        "issues": [i.to_dict() for i in issues],
        "summary": {
            "errors": sum(1 for i in issues if i.severity == Severity.ERROR),
            "warnings": sum(1 for i in issues if i.severity == Severity.WARNING),
        },
    }
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


def _print_human_result(target: Path, issues: list[SpecsDoctorIssue]) -> None:
    if not issues:
        typer.echo(f"[ok] {target} — 0 errors, 0 warnings.")
        return
    errors = [i for i in issues if i.severity == Severity.ERROR]
    warnings = [i for i in issues if i.severity == Severity.WARNING]
    typer.echo(
        f"[{'fail' if errors else 'warn'}] {target} — "
        f"{len(errors)} error(s), {len(warnings)} warning(s):"
    )
    for issue in issues:
        marker = "ERR " if issue.severity == Severity.ERROR else "WARN"
        location = f" ({issue.path})" if issue.path else ""
        typer.echo(f"  [{marker}] {issue.code}: {issue.description}{location}")
    # Authoritative final verdict line (bug: specs-doctor-dual-error-counter).
    # A memory-lint issue may embed its own "Summary: … 0 ERROR" text; this final
    # line is the single source of truth so the last output line never contradicts
    # the real result.
    typer.echo(
        f"[{'fail' if errors else 'ok'}] overall: {len(errors)} error(s), "
        f"{len(warnings)} warning(s) — {target}"
    )


def _render_recipe_steps(issues: list[SpecsDoctorIssue]) -> list[str]:
    """Render ``--recipe``'s ordered, copy-pasteable steps — one per finding, in
    ``check()`` order (A1.3). Never a second step table: every step is a rendering of
    the SAME finding object ``--json`` emits (code/path/description) — nothing here is
    looked up from a second, code-keyed table that could drift from the findings.
    """
    steps: list[str] = []
    for n, issue in enumerate(issues, start=1):
        location = f" ({issue.path})" if issue.path else ""
        steps.append(f"{n}. [{issue.code}]{location} {issue.description}")
    return steps


def _print_recipe(issues: list[SpecsDoctorIssue]) -> None:
    steps = _render_recipe_steps(issues)
    if not steps:
        typer.echo("[recipe] 0 finding(s) — nothing to do.")
        return
    typer.echo(f"[recipe] {len(steps)} step(s) — copy-paste in order:")
    for step in steps:
        typer.echo(step)


@app.command("doctor")
def doctor(
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
    context: str | None = typer.Option(
        None,
        "--context",
        help=("Context name; resolves repos/<context>/specs. Mutually exclusive with --specs-dir."),
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of human output."
    ),
    recipe: bool = typer.Option(
        False,
        "--recipe",
        help=(
            "Emit ordered, concrete, copy-pasteable steps for every finding — a "
            "rendering of the SAME finding objects --json emits (A1.3), never a "
            "second step table. Takes precedence over --json."
        ),
    ),
    public_dir: str | None = typer.Option(
        None,
        "--public-dir",
        help=(
            "Path to dadaia_workspace/public/. "
            "Enables canonical template and scaffold drift checks. "
            "Default: auto-detected from specs_dir/../dadaia_workspace/public/."
        ),
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help=(
            "Apply auto-fixes for fixable issues (TREE-3: render missing memory HTML; "
            "TREE-4: create missing dirs with AGENTS.md + .gitkeep; MEM-PLACEHOLDER-1: "
            "remove unfilled placeholder atoms from old scaffolds). "
            "Warn-only invariants (TREE-1, TREE-2, TREE-5, TREE-8) are never "
            "auto-fixed. After fixing, re-checks and reports residual issues."
        ),
    ),
) -> None:
    """Run structural checks on the SDD specs tree.

    ``--context`` resolves the context's ``specs/`` tree via the same
    ``container.resolve_context_specs_dir`` seam used by the four lifecycle workflows,
    and is mutually exclusive with ``--specs-dir``. The resolver falls back to the
    workspace-root ``specs/`` tree
    when ``repos/<context>/specs`` does not exist (self-hosting workspaces), instead
    of hand-rolling a ``repos/<context>/specs`` path that may not exist.
    """
    if specs_dir is not None and context is not None:
        raise typer.BadParameter("Pass either --context or --specs-dir, not both.")
    if context is not None:
        target = container.resolve_context_specs_dir(resolve_workspace_root(), context)
    else:
        target = _resolve_specs_dir(specs_dir)
    if public_dir is not None:
        resolved_public: Path | None = Path(public_dir).resolve()
    else:
        resolved_public = _resolve_public_dir(target)
    doctor_svc = SpecsDoctor(
        target,
        public_dir=resolved_public,
        templates_dir=_TEMPLATES_DIR,
    )
    issues = doctor_svc.check()

    _print_migration_hints(issues)

    if fix:
        issues = _apply_doctor_fix(doctor_svc, issues)

    if recipe:
        _print_recipe(issues)
    elif json_output:
        _print_json_result(target, issues)
    else:
        _print_human_result(target, issues)

    has_errors = any(i.severity == Severity.ERROR for i in issues)
    sys.exit(1 if has_errors else 0)


def _error_identities(issue: SpecsDoctorIssue) -> set[tuple[str, str]]:
    """Stable identities for a doctor error — one per underlying violation.

    An aggregating issue cannot be compared as a whole: LINT-1 joins one line per
    violating memory atom into a single description, so repairing some atoms shrinks that
    string and an untouched pre-existing violation reads as newly introduced. The operator
    is then told to restore the backup, discarding a good version bump while leaving the
    very error in place — precisely the harm the pre/post comparison exists to prevent
    (bug specs-upgrade-blames-itself-for-a-preexisting-error-when-a-migration-legitimately
    -skips-an-atom). Comparing line by line gives every violation its own identity, so a
    genuinely new one is still caught.
    """
    lines = [line.strip() for line in (issue.description or "").splitlines() if line.strip()]
    if len(lines) <= 1:
        return {(issue.code, issue.description or "")}
    return {(issue.code, line) for line in lines}


@app.command("upgrade")
def upgrade(
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context."
    ),
    target: int | None = typer.Option(
        None, "--target", help="Target pattern version. Default: the canonical version."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only — no backup, no writes."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the interactive confirmation."),
) -> None:
    """Upgrade a specs/ tree to the canonical pattern version.

    Backup-first (``specs_bkp/<from>→<to>-<UTC>/``) → apply the migration chain →
    re-stamp the constitution → re-run ``dadaia specs doctor``. Idempotent: already
    at target ⇒ no-op. On a non-clean doctor after upgrade, the backup is the
    recovery point.
    """
    from dadaia_workspace.core import specs_version as _ver
    from dadaia_workspace.features.migrate import upgrade as _upgrade_feat

    resolved = _resolve_specs_dir(specs_dir)
    current = _ver.read_pattern_version(resolved)
    goal = _ver.CANONICAL_SPECS_VERSION if target is None else target

    if current >= goal:
        # Still run the template-artifact repair (bug
        # scaffold-repair-cannot-remediate-invalid-placeholder-atom): a current-version
        # tree may carry an unfilled placeholder atom from an old scaffold.
        result = _upgrade_feat.upgrade(resolved, target=target, dry_run=dry_run)
        verb = "would remove" if dry_run else "removed"
        for path in result.placeholder_removed:
            typer.echo(f"[placeholder-repair] {verb} {path}")
        if result.no_op:
            typer.echo(
                f"[ok] {resolved} already at pattern version {current} (target {goal}) — no-op."
            )
        sys.exit(0)

    if dry_run:
        result = _upgrade_feat.upgrade(resolved, target=target, dry_run=True)
        typer.echo(f"[dry-run] {current} → {result.to_version}")
        typer.echo(f"  backup would be: {result.backup_path}")
        for key, step_result in result.steps:
            typer.echo(f"  step {key}: {len(step_result.moved)} move(s) planned")
        sys.exit(0)

    if not yes:
        confirm = typer.confirm(
            f"Upgrade {resolved} from pattern version {current} → {goal}? (a backup is taken first)"
        )
        if not confirm:
            typer.echo("[abort] upgrade cancelled.")
            sys.exit(1)

    # Snapshot pre-existing doctor errors BEFORE the migration so we only fail on errors
    # the migration NEWLY introduces — not on pre-existing, unrelated ones (bug:
    # specs-upgrade-fails-on-preexisting-doctor-error). Restoring the backup for a
    # pre-existing error is actively harmful: it discards a good version bump while
    # leaving the very same error in place.
    pre_doctor = SpecsDoctor(
        resolved, public_dir=_resolve_public_dir(resolved), templates_dir=_TEMPLATES_DIR
    )
    pre_errors = {
        identity
        for i in pre_doctor.check()
        if i.severity == Severity.ERROR
        for identity in _error_identities(i)
    }

    result = _upgrade_feat.upgrade(resolved, target=target)
    typer.echo(f"[upgrade] {result.from_version} → {result.to_version}")
    typer.echo(f"  backup: {result.backup_path}")
    for path in result.placeholder_removed:
        typer.echo(f"[placeholder-repair] removed {path}")
    for key, step_result in result.steps:
        for src, dst in step_result.moved:
            typer.echo(f"  [{key}] moved {src} → {dst}")

    # Verify with doctor; only the migration's OWN regressions justify a restore.
    doctor_svc = SpecsDoctor(
        resolved, public_dir=_resolve_public_dir(resolved), templates_dir=_TEMPLATES_DIR
    )
    post_errors = [i for i in doctor_svc.check() if i.severity == Severity.ERROR]
    new_errors = [i for i in post_errors if _error_identities(i) - pre_errors]
    pre_existing = [i for i in post_errors if not (_error_identities(i) - pre_errors)]
    if new_errors:
        typer.echo(
            f"[fail] upgrade introduced {len(new_errors)} new doctor error(s). "
            f"Restore from: {result.backup_path}",
            err=True,
        )
        for issue in new_errors:
            typer.echo(f"  {issue.code}: {issue.description}", err=True)
        sys.exit(1)
    if pre_existing:
        typer.echo(
            f"[warn] {resolved} upgraded to pattern version {result.to_version}; the migration "
            f"is clean, but {len(pre_existing)} pre-existing doctor error(s) remain (not caused "
            f"by the upgrade) — fix separately, do NOT restore:"
        )
        for issue in pre_existing:
            typer.echo(f"  {issue.code}: {issue.description}")
        sys.exit(0)
    typer.echo(f"[ok] {resolved} upgraded to pattern version {result.to_version}; doctor clean.")
    sys.exit(0)


# Canonical templates directory — inside the installed package
_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "public" / "templates"


@app.command("init")
def init(
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to target specs/ directory. Default: ./specs/",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Project name for rendered templates. Default: parent directory name.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing files. Without this flag, existing files are skipped.",
    ),
) -> None:
    """Bootstrap a SDD release-lifecycle specs/ directory structure."""
    # Resolve specs_dir. An explicit --specs-dir routes through the same resolver seam
    # every other resolver-driven verb shares (T-044-40, `core.specs_resolver
    # .resolve_specs_dir`) so a symlinked target is refused here too — reusing that
    # seam's existing refusal, not adding a second one (T-045-21/FR8, A8.2). `None`
    # keeps init's own default (cwd/specs, guarded by the Root Law check below) rather
    # than falling into that seam's unrelated context-resolution fallback.
    target = _resolve_specs_dir(specs_dir) if specs_dir else Path.cwd() / "specs"

    # Coherence with `specs doctor` (validation-027 F-04/F-10): the doctor refuses the
    # workspace-root specs/ fallback (Root Law), so init must refuse to CREATE it there.
    # An explicit --specs-dir is a deliberate operator choice and always wins.
    if specs_dir is None and (Path.cwd() / ".dadaia").is_dir():
        typer.secho(
            "Error: refusing to scaffold 'specs/' at the workspace root: the Workspace "
            "Root Law forbids a top-level specs/ directory (and 'specs doctor' would "
            "refuse it). Run inside a repo, or pass --specs-dir repos/<slug>/specs.",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Resolve project name
    project_name = name or target.parent.name

    result = scaffold(
        specs_dir=target,
        project_name=project_name,
        force=force,
        templates_dir=_TEMPLATES_DIR,
    )

    # Print created/skipped/error summary
    for path in result.created:
        action = "[overwrite]" if force else "[created]"
        typer.echo(f"{action} {path}")
    for path in result.skipped:
        typer.echo(f"[skip] {path}")
    for error in result.errors:
        typer.echo(f"[error] {error}", err=True)

    if result.errors:
        sys.exit(1)


@release_app.command("open")
def release_open(
    version_id: str = typer.Argument(..., help="SemVer release id, e.g. v0.1.6."),
    specs_dir: str | None = typer.Option(None, "--specs-dir", help="Path to specs/."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing segment files."),
) -> None:
    """Open a new release: scaffold the parent + its first segment (alpha-1).

    Sets specs/releases/ACTIVE.md to ``release: <version> / segment: alpha-1 /
    phase: SPEC`` (schema v2, ADR-1/ADR-5).
    """
    target = _resolve_specs_dir(specs_dir)
    try:
        result = scaffold_release_segment(target, version_id, "alpha-1", force=force)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(2) from exc
    for path in result.created:
        typer.echo(f"[created] {path}")
    for error in result.errors:
        typer.echo(f"[error] {error}", err=True)
    if result.errors:
        raise typer.Exit(1)
    _write_active(target, version_id, "alpha-1", "SPEC")
    typer.echo(
        f"[ok] Release {version_id} opened at segment alpha-1; "
        "ACTIVE.md -> release/segment/phase set. Author SPEC.md next."
    )


@segment_app.command("open")
def segment_open(
    segment: str = typer.Argument(..., help="Segment to open, e.g. alpha-2 or rc-1."),
    specs_dir: str | None = typer.Option(None, "--specs-dir", help="Path to specs/."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing segment files."),
) -> None:
    """Open the next segment (alpha-N/rc-N) of the active release.

    Reads the active release from ACTIVE.md, scaffolds the segment, and advances
    ACTIVE.md's ``segment:`` to it (phase reset to SPEC).
    """
    target = _resolve_specs_dir(specs_dir)
    release, _segment, _phase, err = read_active_md(target / "releases" / "ACTIVE.md")
    if err is not None or not release or release == "none":
        typer.echo(
            f"[error] no active release in ACTIVE.md ({err or 'release: none'}). "
            "Open a release first: dadaia specs release open <version>.",
            err=True,
        )
        raise typer.Exit(2)
    try:
        result = scaffold_release_segment(target, release, segment, force=force)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(2) from exc
    for path in result.created:
        typer.echo(f"[created] {path}")
    for error in result.errors:
        typer.echo(f"[error] {error}", err=True)
    if result.errors:
        raise typer.Exit(1)
    _write_active(target, release, segment, "SPEC")
    typer.echo(f"[ok] Segment {segment} opened for {release}; ACTIVE.md segment advanced.")
