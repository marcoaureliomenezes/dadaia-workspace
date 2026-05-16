"""Scaffolder for SDD release-lifecycle specs directory structure.

Pure module — no I/O outside the supplied specs_dir/templates_dir.
Creates the canonical SDD directory tree for new repositories.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path

import jinja2


@dataclass
class ScaffoldResult:
    """Result of a scaffold() call."""

    created: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


_CONSTITUTION_STUB = """\
# Constitution — {project_name}

> **Created:** {today}

## Propósito

Declaração atômica do propósito do projeto e suas invariantes fundamentais.

## Invariantes

1. (Definir invariantes aqui)

## Exclusões canônicas

- (Definir o que este projeto não é)
"""

_CANDIDATES_STUB = """\
# Backlog — Candidatas

> Formato canônico: `- <name> — <one-liner> (owner: <agent>, contexto: <link>)`

## Candidatas ativas

(Sem candidatas ainda.)

## Histórico de promoções

(Vazio — nenhuma candidata promovida ainda.)
"""

_IDEAS_STUB = """\
# Backlog — Ideias

> Ideias brutas, sem comprometimento de escopo. Mover para `candidates.md`
> quando refinadas.

## Ideias

(Sem ideias registradas ainda.)
"""


def _render_template(
    templates_dir: Path,
    template_name: str,
    context: dict[str, str],
) -> str:
    """Render a Jinja2 template file with the given context."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_dir)),
        undefined=jinja2.Undefined,
        autoescape=False,
    )
    template = env.get_template(template_name)
    return template.render(context)


def scaffold(
    specs_dir: Path,
    project_name: str,
    force: bool,
    templates_dir: Path,
) -> ScaffoldResult:
    """Scaffold the SDD release-lifecycle directory structure.

    Args:
        specs_dir: Target specs/ directory (will be created if absent).
        project_name: Human-readable project name used in rendered templates.
        force: If True, overwrite existing files. If False, skip existing files.
        templates_dir: Directory containing Jinja2 .j2 template files.

    Returns:
        ScaffoldResult with lists of created, skipped, and error entries.
    """
    result = ScaffoldResult()
    today = datetime.date.today().isoformat()
    template_context: dict[str, str] = {
        "project_name": project_name,
        "today": today,
        "last_release_id": "none",
    }

    def _write(path: Path, content: str) -> None:
        """Write content to path; respect force flag."""
        if path.exists() and not force:
            result.skipped.append(path)
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            result.created.append(path)
        except OSError as exc:
            result.errors.append(f"Failed to write {path}: {exc}")

    def _touch(path: Path) -> None:
        """Create an empty .gitkeep file; respect force flag."""
        if path.exists() and not force:
            result.skipped.append(path)
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
            result.created.append(path)
        except OSError as exc:
            result.errors.append(f"Failed to create {path}: {exc}")

    # 1 — constitution.md (stub; operator-owned — only create if absent)
    constitution_path = specs_dir / "constitution.md"
    if constitution_path.exists() and not force:
        result.skipped.append(constitution_path)
    else:
        try:
            constitution_path.parent.mkdir(parents=True, exist_ok=True)
            content = _CONSTITUTION_STUB.format(
                project_name=project_name, today=today
            )
            constitution_path.write_text(content, encoding="utf-8")
            result.created.append(constitution_path)
        except OSError as exc:
            result.errors.append(f"Failed to write {constitution_path}: {exc}")

    # 2 — memory/architecture.html
    try:
        arch_html = _render_template(
            templates_dir, "memory-architecture.html.j2", template_context
        )
        _write(specs_dir / "memory" / "architecture.html", arch_html)
    except Exception as exc:
        result.errors.append(f"Template render error (architecture): {exc}")

    # 3 — memory/tech-stack.html
    try:
        tech_html = _render_template(
            templates_dir, "memory-tech-stack.html.j2", template_context
        )
        _write(specs_dir / "memory" / "tech-stack.html", tech_html)
    except Exception as exc:
        result.errors.append(f"Template render error (tech-stack): {exc}")

    # 4 — memory/product/index.html (empty catalog)
    try:
        product_html = _render_template(
            templates_dir, "memory-product-index.html.j2", template_context
        )
        _write(specs_dir / "memory" / "product" / "index.html", product_html)
    except Exception as exc:
        result.errors.append(f"Template render error (product-index): {exc}")

    # 5 — releases/ACTIVE.md
    _write(
        specs_dir / "releases" / "ACTIVE.md",
        "release: none\nphase: none\n",
    )

    # 6 — backlog/candidates.md
    _write(specs_dir / "backlog" / "candidates.md", _CANDIDATES_STUB)

    # 7 — backlog/ideas.md
    _write(specs_dir / "backlog" / "ideas.md", _IDEAS_STUB)

    # 8, 9, 10 — .gitkeep files
    _touch(specs_dir / "_archive" / "releases" / ".gitkeep")
    _touch(specs_dir / "_archive" / "legacy-features" / ".gitkeep")
    _touch(specs_dir / "assets" / ".gitkeep")

    return result
