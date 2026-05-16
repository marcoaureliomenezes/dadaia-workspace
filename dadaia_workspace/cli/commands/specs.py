"""CLI command group: `dadaia specs <verb>`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs.scaffolder import scaffold

app = typer.Typer(help="SDD release-lifecycle structural checks and helpers.")


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    if specs_dir:
        return Path(specs_dir).resolve()

    # Try primary_context.json first
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        primary = parent / ".dadaia" / "states" / "primary_context.json"
        if primary.exists():
            try:
                data = json.loads(primary.read_text(encoding="utf-8"))
                sd = data.get("specs_dir")
                if sd:
                    return Path(sd).resolve()
            except (OSError, ValueError):
                pass

    # Fallback: cwd/specs
    candidate = cwd / "specs"
    if candidate.exists():
        return candidate.resolve()

    raise typer.BadParameter(
        "Could not resolve specs_dir. Pass --specs-dir or activate a context "
        "with `dadaia context activate <name>`."
    )


@app.command("doctor")
def doctor(
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from primary_context.json.",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of human output."
    ),
) -> None:
    """Run structural checks on the SDD specs tree."""
    target = _resolve_specs_dir(specs_dir)
    doctor_svc = SpecsDoctor(target)
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

    has_errors = any(i.severity == Severity.ERROR for i in issues)
    sys.exit(1 if has_errors else 0)


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
    if specs_dir:
        target = Path(specs_dir).resolve()
    else:
        target = Path.cwd() / "specs"

    # Resolve project name
    if name:
        project_name = name
    else:
        project_name = target.parent.name

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
