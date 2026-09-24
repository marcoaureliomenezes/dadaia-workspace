"""CLI command group: `dadaia specs <verb>`."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from dadaia_workspace.cli._specs_resolution import (
    repo_slug_for_context,
    resolve_context_for_cli,
    resolve_specs_dir_for_cli,
)
from dadaia_workspace.core import specs_version
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.migrate import upgrade as upgrade_feature
from dadaia_workspace.features.migrate.registry import UpgradeRefused
from dadaia_workspace.features.migrate.upgrade import UpgradeResult
from dadaia_workspace.features.specs import canon
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

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

    A tree below the one live hop (v6) refuses, no filesystem write, naming the
    dadaia-workspace 0.4.x prerequisite. A tree at v6 walks to v7; every tree gets its
    fixed law sections and template-artifact repairs, so the doctor ends clean.
    """
    resolved = _resolve_specs_dir(specs_dir)
    try:
        result = upgrade_feature.upgrade(resolved, target=target, dry_run=dry_run)
    except UpgradeRefused as exc:
        typer.echo(f"[refused] {exc}", err=True)
        sys.exit(1)
    _echo_upgrade(resolved, result)
    sys.exit(0)


def _echo_upgrade(specs: Path, result: UpgradeResult) -> None:
    will = "would " if result.dry_run else ""
    for path in result.placeholder_removed:
        typer.echo(f"[placeholder-repair] {will}remove {path}")
    for path in result.status_rewritten:
        typer.echo(f"[status-vocabulary] {will}rewrite {path}")
    for path in result.tech_stack_folded:
        typer.echo(f"[tech-stack] {will}fold {path} into memory/ARCHITECTURE.md")
    for path in result.fixed_restored:
        typer.echo(f"[fixed-section] {will}write {path}")
    if result.from_version < result.to_version:
        typer.echo(
            f"[stamp] {will}stamp {specs / 'constitution.md'} "
            f"{result.from_version} -> {result.to_version}"
        )
    if result.no_op:
        typer.echo(
            f"[ok] {specs} already at pattern version {result.from_version} "
            f"(target {result.to_version}) — no-op."
        )


_FIX = "fix: .dadaia/.venv/bin/dadaia specs init"
_BACKUP = "specs-bkp"


@app.command("init")
def init(
    context: str | None = typer.Option(
        None, "--context", help="Spec Context whose main repo gets specs/. Default: bound."
    ),
    specs_dir: str | None = typer.Option(
        None, "--specs-dir", help="Explicit specs/ directory instead of a context's."
    ),
    name: str | None = typer.Option(
        None, "--name", help="Project name for the constitution. Default: the repo name."
    ),
    replace_foreign: bool = typer.Option(
        False,
        "--replace-foreign",
        help=f"Move a foreign specs/ to {_BACKUP}/ (git mv, staged) without asking.",
    ),
) -> None:
    """Bring a repo's specs/ to the canon, never committing.

    Absent: scaffold. Dadaia (stamped >= 6): upgrade, then fill missing files. Foreign:
    after consent, `git mv specs specs-bkp` (staged) and scaffold.
    """
    if specs_dir is not None:
        target, rerun = resolve_specs_dir_for_cli(specs_dir), f"--specs-dir {specs_dir}"
    else:
        try:
            ctx = resolve_context_for_cli(context)
        except ValueError as exc:
            typer.echo(f"[error] {exc}\n{_FIX} --context <name>", err=True)
            raise typer.Exit(2) from exc
        root = resolve_workspace_root()
        target, rerun = (
            root / "repos" / repo_slug_for_context(root, ctx) / "specs",
            f"--context {ctx}",
        )

    kind = canon.classify(target)
    if kind == "foreign":
        _move_foreign(target, rerun, replace_foreign)
    elif kind == "dadaia":
        _echo_upgrade(target, upgrade_feature.upgrade(target))

    written = canon.scaffold(target, project_name=name or target.parent.name)
    for path in [*written, *canon.scaffold_repo_law(target.parent)]:
        typer.echo(f"[created] {path}")
    if kind != "dadaia":
        typer.echo(f"[ok] {target} at pattern version {specs_version.CANONICAL_SPECS_VERSION}")


def _move_foreign(target: Path, rerun: str, replace_foreign: bool) -> None:
    """``specs/`` -> ``specs-bkp/`` after consent; exits on a refusal, writing nothing."""
    backup = target.parent / _BACKUP
    if backup.exists():
        typer.echo(
            f"[error] {backup} already exists — move or delete it first.\n"
            f"fix: git -C {target.parent} rm -r -q {_BACKUP}",
            err=True,
        )
        raise typer.Exit(1)
    if not replace_foreign:
        question = f"{target} is not a dadaia specs tree. Move it to {_BACKUP}/ and scaffold?"
        if not (sys.stdin.isatty() and typer.confirm(question, default=False)):
            typer.echo(
                f"[refused] {target} is a foreign specs tree; nothing written.\n"
                f"{_FIX} {rerun} --replace-foreign",
                err=True,
            )
            raise typer.Exit(2)
    GitSubprocessClient().move(target.parent, target.name, _BACKUP)
    typer.echo(f"[moved] {target} -> {backup} (staged, not committed)")
