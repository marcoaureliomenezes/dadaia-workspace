"""CLI command group: `dadaia ci <verb>` — local CI-equivalent preflight gate + chokepoints."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

import typer

from dadaia_workspace.container import is_source_repo_root as _is_source_repo_root
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.exceptions import CiPreflightScopeError, WorkspaceNotInitializedError
from dadaia_workspace.core.gitflow import Gitflow
from dadaia_workspace.core.invocation import (
    alive_context_names,
    context_name_for_repo_slug,
    repo_slug_under_repos,
    resolve_context_specs_dir,
)
from dadaia_workspace.core.specs_version import read_gitflow
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.ci_preflight import (
    all_passed,
    checks_for,
    failed_names,
    run_preflight,
    subprocess_runner,
)
from dadaia_workspace.features.spec_context.service import install_git_hooks

app = typer.Typer(help="Local CI-equivalent preflight gate + git-hook chokepoints.")


def _repo_root() -> Path:
    """Resolve the enclosing git repo root, or fail with a clear message."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise typer.BadParameter("not inside a git repository") from exc
    return Path(out.stdout.strip())


@app.command()
def preflight(
    quick: bool = typer.Option(False, "--quick", help="Skip the slow e2e suite."),
    fail_fast: bool = typer.Option(
        True, "--fail-fast/--no-fail-fast", help="Stop at the first failing check."
    ),
) -> None:
    """Run the five local CI checks; exit non-zero if any fail.

    The checks, in order: ruff format --check, ruff check, mypy --strict,
    lint-imports, pytest. Run it before pushing — locally-solvable failures must
    never reach a push.
    """
    root = _repo_root()
    # The checks are structurally bound to this repo: they lint `dadaia_workspace/` and
    # `tests/`, type-check `dadaia_workspace/`, and read this repo's setup.cfg. In a
    # consumer repo none of those paths exist and the consumer venv has no ruff/mypy, so
    # the gate reported a phantom lint FAIL and blamed a missing poetry — sending the
    # operator to install a tool that would not have helped
    # (bug ci-preflight-unusable-outside-the-source-repo). Refuse honestly instead. The
    # source-repo test is the existing one, not a second definition.
    if not _is_source_repo_root(root):
        raise CiPreflightScopeError(
            f"`dadaia ci preflight` targets the dadaia-workspace source repo; "
            f"{str(root)!r} is not it. The gate lints and type-checks the library's own "
            "paths, which do not exist here. Run your repo's own CI checks instead."
        )
    checks = checks_for(quick=quick)
    typer.echo(f"Running {len(checks)} preflight check(s){' (quick)' if quick else ''}…")
    results = run_preflight(checks, subprocess_runner(root), fail_fast=fail_fast)

    for result in results:
        marker = "PASS" if result.passed else "FAIL"
        typer.echo(f"  [{marker}] {result.name}")

    if not all_passed(results):
        typer.secho(
            f"\nPre-push gate FAILED: {', '.join(failed_names(results))}",
            fg=typer.colors.RED,
            err=True,
        )
        for result in results:
            if not result.passed:
                tail = "\n".join(result.output.strip().splitlines()[-20:])
                if tail:
                    typer.echo(f"\n--- {result.name} ---\n{tail}", err=True)
        raise typer.Exit(1)

    typer.secho("\nAll preflight checks passed.", fg=typer.colors.GREEN)


def _no_canon_violations(paths: Iterable[str]) -> list[str]:
    """The canon predicate for a specs/ tree stamped below the canonical pattern: the
    v6 canon does not describe it, so no path in it is a v6 violation."""
    return []


def _gitflow_for(repo_root: Path) -> Gitflow:
    """ADR 0046, once per push: the repo's own constitution, else its owning context's
    main-repo constitution (an associated repo), else the default with one warning."""
    specs_dir, context = repo_root / "specs", None
    try:
        workspace: Path | None = resolve_workspace_root(repo_root)
    except WorkspaceNotInitializedError:
        workspace = None
    slug = repo_slug_under_repos(workspace, repo_root) if workspace else None
    if workspace and slug:
        name = context_name_for_repo_slug(workspace, slug)
        context = name if name in alive_context_names(workspace) else None
    if workspace and context and not (specs_dir / "constitution.md").is_file():
        specs_dir = resolve_context_specs_dir(workspace, context)
    gitflow, warning = read_gitflow(specs_dir)
    if warning:
        fix = (
            f"\nfix: {fix_line(workspace, 'specs', 'init', '--context', context)}"
            if workspace and context
            else ""
        )
        typer.echo(f"[pre-push] WARNING: {warning}{fix}", err=True)
    return gitflow


@app.command("push-gate-check")
def push_gate_check() -> None:
    """Pre-push gate: branch policy by the project gitflow + the range-scoped denylist scan.

    Branch model: the constitution's gitflow block (`dd-gitflow-default`).

    Reads the pre-push ref lines from stdin (``<local-ref> <local-sha> <remote-ref>
    <remote-sha>``). Every non-deletion ref (tags included) is scanned for new objects
    carrying a denylisted term — a work-branch push is the first publication to ``origin``.
    Branch deletions are never scanned; tag pushes are scanned but never gated on branch
    policy. No security verdict is checked here — that runs as a PR gate.

    The object source, denylist terms and baseline patterns are all built here and
    injected; a call site that fails to wire the object reader is a defect, never a
    bypass. No repo or context name is a term source.
    """
    from dadaia_workspace.container import (
        build_git_object_reader,
        load_denylist_baseline_patterns,
        load_denylist_terms,
    )
    from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION, read_pattern_version
    from dadaia_workspace.features.chokepoints import push_gate_decision
    from dadaia_workspace.features.chokepoints.branch_policy import parse_push_stdin
    from dadaia_workspace.features.specs.canon import canon_violations

    repo_root = _repo_root()

    # Bug pre-push-canon-scan-not-range-scoped (operator ruling 2026-09-13): the v6
    # canon is a property of a v6 tree. A specs/ tree still stamped below
    # CANONICAL_SPECS_VERSION (pattern 5: Markdown backlog, `v`-prefixed release dirs,
    # lowercase memory files) has NOTHING for the canon scan to enforce until
    # `dadaia specs upgrade` migrates it — the doctor already reports that drift;
    # the push gate must not lock every specs edit behind the migration.
    specs_dir = repo_root / "specs"
    specs_version = read_pattern_version(specs_dir)
    canon_fn = canon_violations
    if specs_dir.is_dir() and specs_version < CANONICAL_SPECS_VERSION:
        # An unstamped (pre-framework) tree counts as below the canon too — ADR 0013.
        typer.echo(
            f"[pre-push] specs/ tree is stamped pattern {specs_version} "
            f"(< {CANONICAL_SPECS_VERSION}): the v6 canon scan does not apply until "
            "`dadaia specs upgrade` migrates it; the denylist scan still runs.",
            err=True,
        )
        canon_fn = _no_canon_violations

    denylist_terms = load_denylist_terms()
    baseline_patterns = load_denylist_baseline_patterns()

    mode = (
        "operator denylist + baseline"
        if denylist_terms
        else "baseline only (no operator denylist; private names go in "
        "$DADAIA_PRIVACY_DENYLIST or .dadaia/states/privacy_denylist.json)"
    )
    typer.echo(f"[pre-push] denylist scan mode: {mode}", err=True)

    stdin_text = sys.stdin.read() if not sys.stdin.isatty() else ""
    refs, malformed = parse_push_stdin(stdin_text)
    decision = push_gate_decision(
        refs,
        object_source=build_git_object_reader(),
        repo=repo_root,
        canon_violations_fn=canon_fn,
        gitflow=_gitflow_for(repo_root),
        malformed_lines=malformed,
        denylist_terms=denylist_terms,
        baseline_patterns=baseline_patterns,
    )
    if decision.warn:
        typer.echo(decision.warn, err=True)

    if not decision.allowed:
        typer.secho(decision.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


_SHA40_RE = re.compile(r"^[0-9a-fA-F]{40}$")


@app.command("install-hook")
def install_hook(
    force: bool = typer.Option(False, "--force", help="Overwrite existing git hooks."),
    repo: Path | None = typer.Option(None, "--repo", help="Target repo. Default: cwd's repo."),
) -> None:
    """Install the pre-push CI/security gate."""
    try:
        installed = install_git_hooks(repo or _repo_root(), force=force)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from None
    if not installed:
        typer.secho("pre-push hook already exists; use --force to overwrite.", fg="yellow")
        raise typer.Exit(1)
    for target in installed:
        typer.secho(f"Installed pre-push CI + security gate -> {target}", fg=typer.colors.GREEN)
