"""CLI command group: `dadaia specs <verb>`."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import typer

from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs.scaffolder import scaffold, scaffold_hotfix_release

app = typer.Typer(help="SDD release-lifecycle structural checks and helpers.")

# Sub-app for `dadaia specs hotfix <verb>`
hotfix_app = typer.Typer(help="Hotfix release helpers.")
app.add_typer(hotfix_app, name="hotfix")


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
        help="Path to specs/ directory. Default: resolve from primary_context.json.",
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
