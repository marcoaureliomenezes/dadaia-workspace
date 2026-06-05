"""CLI command group: `dadaia ci <verb>` — local CI-equivalent preflight gate."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer

from dadaia_workspace.features.ci_preflight import (
    all_passed,
    checks_for,
    failed_names,
    run_preflight,
    subprocess_runner,
)

app = typer.Typer(help="Local CI-equivalent preflight gate (pre-push).")

# .../dadaia_workspace/cli/commands/ci.py -> parents[2] == .../dadaia_workspace
_HOOK_SOURCE = Path(__file__).resolve().parents[2] / "public" / "scripts" / "pre-push-ci-gate.sh"


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
    """Run ruff + mypy --strict + pytest locally; exit non-zero if any fail.

    This is the gate the pre-push hook calls. Locally-solvable failures must
    never reach a push.
    """
    root = _repo_root()
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


@app.command("install-hook")
def install_hook(
    force: bool = typer.Option(False, "--force", help="Overwrite an existing pre-push hook."),
) -> None:
    """Install the pre-push CI gate into .git/hooks/pre-push for this repo."""
    root = _repo_root()
    hooks_dir = root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        raise typer.BadParameter(f"{hooks_dir} not found (is this a git repository?)")
    target = hooks_dir / "pre-push"
    if target.exists() and not force:
        typer.secho(
            f"pre-push hook already exists at {target}; use --force to overwrite.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(1)
    shutil.copyfile(_HOOK_SOURCE, target)
    target.chmod(0o755)
    typer.secho(f"Installed pre-push CI gate -> {target}", fg=typer.colors.GREEN)
