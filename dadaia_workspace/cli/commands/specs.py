"""CLI command group: `dadaia specs <verb>`."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import typer

from dadaia_workspace import container
from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs.doctor_common import read_active_md
from dadaia_workspace.features.specs.scaffolder import (
    scaffold,
    scaffold_hotfix_release,
    scaffold_release_segment,
)

app = typer.Typer(help="SDD release-lifecycle structural checks and helpers.")

# Sub-app for `dadaia specs hotfix <verb>`
hotfix_app = typer.Typer(help="Hotfix release helpers.")
app.add_typer(hotfix_app, name="hotfix")

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
            "TREE-4: create missing dirs with README + .gitkeep; MEM-PLACEHOLDER-1: "
            "remove unfilled placeholder atoms from old scaffolds). "
            "Warn-only invariants (TREE-1, TREE-2, TREE-5) are never auto-fixed. "
            "After fixing, re-checks and reports residual issues."
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

    # Always surface TREE-1/TREE-2 migration hints (even under --fix).
    migration_issues = [i for i in issues if i.code in ("TREE-1", "TREE-2")]
    if migration_issues:
        for mi in migration_issues:
            typer.echo(f"[MIGRATION] {mi.description}", err=True)

    if fix:
        fixed = doctor_svc.fix(issues)
        if fixed:
            typer.echo(f"[fix] Applied {len(fixed)} auto-fix(es):")
            for f_issue in fixed:
                typer.echo(f"  [fixed] {f_issue.code}: {f_issue.path}")
        # Re-check after fixes to get residual state.
        issues = doctor_svc.check()

    if json_output:
        payload = {
            "specs_dir": str(target),
            "issues": [i.to_dict() for i in issues],
            "summary": {
                "errors": sum(1 for i in issues if i.severity == Severity.ERROR),
                "warnings": sum(1 for i in issues if i.severity == Severity.WARNING),
            },
        }
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if not issues:
            typer.echo(f"[ok] {target} — 0 errors, 0 warnings.")
        else:
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

    has_errors = any(i.severity == Severity.ERROR for i in issues)
    sys.exit(1 if has_errors else 0)


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
        (i.code, i.description) for i in pre_doctor.check() if i.severity == Severity.ERROR
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
    new_errors = [i for i in post_errors if (i.code, i.description) not in pre_errors]
    pre_existing = [i for i in post_errors if (i.code, i.description) in pre_errors]
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
    # Resolve specs_dir
    target = Path(specs_dir).resolve() if specs_dir else Path.cwd() / "specs"

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


@hotfix_app.command("open")
def hotfix_open(
    version_id: str = typer.Argument(
        ...,
        help="SemVer version ID for the hotfix release (e.g. v0.5.1). PATCH must be >= 1.",
    ),
    patches: str = typer.Option(
        ...,
        "--patches",
        help="Release ID this hotfix patches (e.g. agent-sdd-alignment-v1 or v0.5.0).",
    ),
    severity: str = typer.Option(
        "MEDIUM",
        "--severity",
        help="Hotfix severity: LOW, MEDIUM, HIGH, or CRITICAL.",
    ),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing files.",
    ),
) -> None:
    """Open a new hotfix release scaffold under specs/releases/<version-id>/.

    Creates SPEC.md (from release_hotfix.md.j2 template) and TASKS.md stub.
    PLAN.md is intentionally omitted — the SPEC declares whether it is needed (D24).

    Pre-condition (human audit, D4): there should be a matching bullet in
    specs/backlog/candidates.md ## Hotfixes pendentes before running this command.

    Reconciliation (ADR-2/ADR-5): the alpha/rc model unifies all releases — a
    hotfix is just a release that usually ships at ``alpha-1``. Prefer
    ``dadaia specs release open <version>`` (which opens the parent + ``alpha-1``
    and sets the ACTIVE segment) for new hotfixes going forward. This condensed,
    flat ``hotfix open`` command is retained for back-compatibility and for the
    D4 backlog-origin audit; it does not create segment folders.
    """
    target = _resolve_specs_dir(specs_dir)

    # Human-audit warning for D4: check if ## Hotfixes pendentes has any bullets
    candidates_path = target / "backlog" / "candidates.md"
    if candidates_path.exists():
        text = candidates_path.read_text(encoding="utf-8")
        in_hotfixes = False
        has_hotfix_bullet = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                in_hotfixes = bool(re.match(r"^##\s+Hotfixes\s+pendentes", stripped))
                continue
            if in_hotfixes and stripped.startswith("- "):
                has_hotfix_bullet = True
                break
        if not has_hotfix_bullet:
            typer.echo(
                "[WARNING] No bullets found in specs/backlog/candidates.md "
                "## Hotfixes pendentes. Per D4, a hotfix release must originate from "
                "an entry in that section. Proceeding anyway — this is a human audit gate.",
                err=True,
            )
    else:
        typer.echo(
            "[WARNING] specs/backlog/candidates.md not found — cannot verify ## Hotfixes pendentes. "
            "Per D4, a hotfix must originate from that section.",
            err=True,
        )

    try:
        result = scaffold_hotfix_release(
            specs_dir=target,
            version_id=version_id,
            patches_release_id=patches,
            severity=severity,
            templates_dir=_TEMPLATES_DIR,
            force=force,
        )
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    for path in result.created:
        action = "[overwrite]" if force else "[created]"
        typer.echo(f"{action} {path}")
    for path in result.skipped:
        typer.echo(f"[skip] {path}")
    for error in result.errors:
        typer.echo(f"[error] {error}", err=True)

    if result.errors:
        sys.exit(1)

    typer.echo(
        f"[ok] Hotfix release {version_id} scaffolded under {target / 'releases' / version_id}. "
        "Next steps:\n"
        "  1. Edit SPEC.md — fill incident summary, root cause, fix scope.\n"
        "  2. Get SPEC.md Status: Aprovado from product-engineer.\n"
        "  3. Update specs/releases/ACTIVE.md to point to this release.\n"
        "  4. Add tasks to TASKS.md and begin implementation."
    )


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
    # `open` creates. Re-running it on a release that already exists used to rewind
    # ACTIVE.md's phase back to SPEC while reporting `[ok]` — a silent state regression
    # on a live release. Refuse, and name the verb that actually advances one.
    if not force and (target / "releases" / version_id).exists():
        typer.echo(
            f"[error] release {version_id} already exists at "
            f"{target / 'releases' / version_id}. `release open` creates a release; it "
            "does not re-open one, and re-running it would rewind ACTIVE.md's phase. "
            "To open the next segment: dadaia specs segment open <alpha-N|rc-N>. "
            "To deliberately re-scaffold this release: --force.",
            err=True,
        )
        raise typer.Exit(2)
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
