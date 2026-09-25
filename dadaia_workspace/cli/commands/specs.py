"""CLI command group: `dadaia specs <verb>`."""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import typer

from dadaia_workspace import container
from dadaia_workspace.cli._specs_resolution import (
    resolve_context_for_cli,
    resolve_context_specs_dir_for_cli,
    resolve_specs_dir_for_cli,
)
from dadaia_workspace.core import specs_version
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.gitflow import DEFAULT, Gitflow, from_mapping
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.migrate import upgrade as upgrade_feature
from dadaia_workspace.features.migrate.registry import UpgradeRefused
from dadaia_workspace.features.migrate.upgrade import UpgradeResult
from dadaia_workspace.features.specs import canon

app = typer.Typer(help="SDD release-lifecycle structural checks and helpers.")


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


def _init_fix(*argv: str) -> str:
    """``fix:`` re-running ``specs init`` — workspace-relative when no instance is around."""
    try:
        root = resolve_workspace_root()
    except WorkspaceNotInitializedError:
        root = Path()
    return f"fix: {fix_line(root, 'specs', 'init', *argv)}"


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
        help=f"Consent to move a foreign specs/ to {_BACKUP}/ (git mv, staged).",
    ),
    principal: str | None = typer.Option(
        None, "--principal", help="Principal branch. Default: kept, else origin/HEAD, else main."
    ),
    integration: str | None = typer.Option(
        None, "--integration", help="Integration branch. Default: kept, else develop."
    ),
    work_prefix: str | None = typer.Option(
        None,
        "--work-prefix",
        help="Work-branch prefix before <M.m.p>. Default: kept, else feature/.",
    ),
) -> None:
    """Bring a repo's specs/ to the canon, never committing.

    Absent: scaffold. Dadaia (stamped >= 6): upgrade, then fill missing files. Foreign:
    after consent, `git mv specs specs-bkp` (staged) and scaffold.
    """
    rerun: tuple[str, ...] = ("--specs-dir", str(specs_dir))
    if specs_dir is None:
        try:
            ctx = resolve_context_for_cli(context)
        except ValueError as exc:
            typer.echo(f"[error] {exc}\n{_init_fix('--context', '<name>')}", err=True)
            raise typer.Exit(2) from exc
        specs_dir = str(resolve_context_specs_dir_for_cli(resolve_workspace_root(), ctx))
        rerun = ("--context", ctx)
    target = resolve_specs_dir_for_cli(specs_dir)
    flow = _gitflow(target, principal, integration, work_prefix, rerun)

    kind = canon.classify(target)
    if kind == "foreign":
        _move_foreign(target, rerun, replace_foreign)
    elif kind == "dadaia":
        _echo_upgrade(target, upgrade_feature.upgrade(target))

    project = name or target.parent.name
    written = canon.scaffold(target, project_name=project)
    for path in [*written, *canon.scaffold_repo_law(target.parent, project_name=project)]:
        typer.echo(f"[created] {path}")
    specs_version.merge_frontmatter(target, gitflow=flow)
    typer.echo(
        f"[gitflow] principal {flow.principal}, integration {flow.integration}, "
        f"work {flow.work_pattern}"
    )
    if kind != "dadaia":
        typer.echo(f"[ok] {target} at pattern version {specs_version.CANONICAL_SPECS_VERSION}")


def _gitflow(
    target: Path,
    principal: str | None,
    integration: str | None,
    work_prefix: str | None,
    rerun: tuple[str, ...],
) -> Gitflow:
    """Flags over the tree's own valid block, over detection (``origin/HEAD``, else
    ``main``); an invalid result refuses before anything is written."""
    kept, warning = specs_version.read_gitflow(target)
    if warning is not None:
        kept = replace(
            DEFAULT, principal=container.build_git_client().default_branch(target.parent)
        )
    try:
        return from_mapping(
            {
                "principal": principal or kept.principal,
                "integration": integration or kept.integration,
                "work": work_prefix or kept.work_prefix,
            }
        )
    except ValueError as exc:
        fixed = ("--principal", "main", "--integration", "develop", "--work-prefix", "feature/")
        typer.echo(f"[error] {exc}\n{_init_fix(*rerun, *fixed)}", err=True)
        raise typer.Exit(2) from exc


def _move_foreign(target: Path, rerun: tuple[str, ...], replace_foreign: bool) -> None:
    """``specs/`` -> ``specs-bkp/`` (a UTC-stamped sibling when that exists) under
    ``--replace-foreign``; exits on a refusal, writing nothing."""
    if not replace_foreign:
        typer.echo(
            f"[refused] {target} is a foreign specs tree; nothing written.\n"
            f"{_init_fix(*rerun, '--replace-foreign')}",
            err=True,
        )
        raise typer.Exit(2)
    backup = target.parent / _BACKUP
    if backup.exists():
        backup = backup.with_name(f"{_BACKUP}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}")
    container.build_git_client().move(target.parent, target.name, backup.name)
    typer.echo(f"[moved] {target} -> {backup} (staged, not committed)")
