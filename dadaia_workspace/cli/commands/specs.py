"""CLI command group: `dadaia specs <verb>`."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.features.specs.scaffolder import scaffold

app = typer.Typer(help="SDD release-lifecycle structural checks and helpers.")

# `specs release open` / `specs segment open` RETIRED (v0.5.0 FR4/T-050-21A): both
# wrote ACTIVE.md via `_write_active`; the phase is now read from RELEASE.json and no
# file stands in ACTIVE.md's place, so both verbs are dead the moment there is nothing
# left for them to write. `scaffold_release_segment` (features.specs.scaffolder)
# stays — it still scaffolds the SPEC/PLAN/TASKS stubs of a dir-based segment
# (ADR-1/ADR-5) and is exercised directly by its own unit tests.


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    return resolve_specs_dir_for_cli(specs_dir)


@app.command("upgrade")
def upgrade(
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Path to specs/ directory. Default: bound context."
    ),
    target: int | None = typer.Option(
        None, "--target", help="Target pattern version. Default: the canonical version."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only — no writes."),
) -> None:
    """Upgrade a specs/ tree to the canonical pattern version.

    v0.5.1 T-051-16 (K10) retired the versioned migration chain this command used to
    walk (backup-first, apply steps, re-stamp, doctor pre/post-diff) — see
    ``features/migrate/registry.py``'s docstring for why. A tree below the target
    now refuses immediately, no filesystem write, naming the dadaia-workspace 0.4.x
    prerequisite. A tree already at (or above) the target is idempotent: only the
    unconditional template-artifact repair runs.
    """
    from dadaia_workspace.core import specs_version as _ver
    from dadaia_workspace.features.migrate import upgrade as _upgrade_feat
    from dadaia_workspace.features.migrate.registry import UpgradeRefused

    resolved = _resolve_specs_dir(specs_dir)
    current = _ver.read_pattern_version(resolved)
    goal = _ver.CANONICAL_SPECS_VERSION if target is None else target

    try:
        result = _upgrade_feat.upgrade(resolved, target=target, dry_run=dry_run)
    except UpgradeRefused as exc:
        typer.echo(f"[refused] {exc}", err=True)
        sys.exit(1)

    verb = "would remove" if dry_run else "removed"
    for path in result.placeholder_removed:
        typer.echo(f"[placeholder-repair] {verb} {path}")
    rewrote = "would rewrite" if dry_run else "rewrote"
    for path in result.status_rewritten:
        typer.echo(f"[status-vocabulary] {rewrote} {path}")
    if result.no_op:
        typer.echo(f"[ok] {resolved} already at pattern version {current} (target {goal}) — no-op.")
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
    # every other resolver-driven verb shares (T-044-40, `core.invocation
    # .resolve_specs_dir`) so a symlinked target is refused here too — reusing that
    # seam's existing refusal, not adding a second one (T-045-21/FR8, A8.2). `None`
    # keeps init's own default (cwd/specs, guarded by the Root Law check below) rather
    # than falling into that seam's unrelated context-resolution fallback.
    target = _resolve_specs_dir(specs_dir) if specs_dir else Path.cwd() / "specs"

    # Coherence with `dadaia doctor` (validation-027 F-04/F-10): the doctor refuses the
    # workspace-root specs/ fallback (Root Law), so init must refuse to CREATE it there.
    # An explicit --specs-dir is a deliberate operator choice and always wins.
    if specs_dir is None and (Path.cwd() / ".dadaia").is_dir():
        typer.secho(
            "Error: refusing to scaffold 'specs/' at the workspace root: the Workspace "
            "Root Law forbids a top-level specs/ directory (and 'dadaia doctor' would "
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
