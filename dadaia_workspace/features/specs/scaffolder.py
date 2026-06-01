"""Scaffolder for SDD release-lifecycle specs directory structure.

Pure module — no I/O outside the supplied specs_dir/templates_dir.
Creates the canonical SDD directory tree for new repositories.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

import jinja2

from dadaia_workspace.features.specs.renderer import render_atom

# SemVer pattern for hotfix release version IDs (v<M>.<m>.<p>).
_RELEASE_SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")


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
    rendered: str = template.render(context)
    return rendered


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
            content = _CONSTITUTION_STUB.format(project_name=project_name, today=today)
            constitution_path.write_text(content, encoding="utf-8")
            result.created.append(constitution_path)
        except OSError as exc:
            result.errors.append(f"Failed to write {constitution_path}: {exc}")

    # Locate canonical scaffold stubs (public/scaffold/memory/ adjacent to templates_dir).
    _scaffold_memory_dir = templates_dir.parent / "scaffold" / "memory"

    # 2 — memory/architecture.md (born-markdown scaffold; T-MMS-04)
    #     Additive: also write the legacy .yaml + .html until W4 deletes them (T-MMS-12).
    try:
        md_stub_src = _scaffold_memory_dir / "architecture.md"
        _write(specs_dir / "memory" / "architecture.md", md_stub_src.read_text(encoding="utf-8"))
    except Exception as exc:
        result.errors.append(f"Scaffold error (architecture.md): {exc}")

    try:
        yaml_stub_src = _scaffold_memory_dir / "architecture.yaml"
        yaml_content = yaml_stub_src.read_text(encoding="utf-8")
        _write(specs_dir / "memory" / "architecture.yaml", yaml_content)
        arch_html = render_atom(
            yaml_stub_src,
            atom_type="memory-architecture-v1",
            templates_dir=templates_dir,
        )
        _write(specs_dir / "memory" / "architecture.html", arch_html)
    except Exception as exc:
        result.errors.append(f"Scaffold error (architecture): {exc}")

    # 3 — memory/tech-stack.md (born-markdown scaffold; T-MMS-04)
    #     Additive: also write the legacy .yaml + .html until W4 deletes them (T-MMS-12).
    try:
        md_stub_src = _scaffold_memory_dir / "tech-stack.md"
        _write(specs_dir / "memory" / "tech-stack.md", md_stub_src.read_text(encoding="utf-8"))
    except Exception as exc:
        result.errors.append(f"Scaffold error (tech-stack.md): {exc}")

    try:
        yaml_stub_src = _scaffold_memory_dir / "tech-stack.yaml"
        yaml_content = yaml_stub_src.read_text(encoding="utf-8")
        _write(specs_dir / "memory" / "tech-stack.yaml", yaml_content)
        tech_html = render_atom(
            yaml_stub_src,
            atom_type="memory-tech-stack-v1",
            templates_dir=templates_dir,
        )
        _write(specs_dir / "memory" / "tech-stack.html", tech_html)
    except Exception as exc:
        result.errors.append(f"Scaffold error (tech-stack): {exc}")

    # 4 — memory/product/index.md (born-markdown scaffold; T-MMS-04)
    #     Additive: also write the legacy .yaml + .html until W4 deletes them (T-MMS-12).
    try:
        md_stub_src = _scaffold_memory_dir / "product" / "index.md"
        _write(
            specs_dir / "memory" / "product" / "index.md",
            md_stub_src.read_text(encoding="utf-8"),
        )
    except Exception as exc:
        result.errors.append(f"Scaffold error (product-index.md): {exc}")

    try:
        yaml_stub_src = _scaffold_memory_dir / "product" / "index.yaml"
        yaml_content = yaml_stub_src.read_text(encoding="utf-8")
        _write(specs_dir / "memory" / "product" / "index.yaml", yaml_content)
        product_html = render_atom(
            yaml_stub_src,
            atom_type="memory-product-index-v1",
            templates_dir=templates_dir,
        )
        _write(specs_dir / "memory" / "product" / "index.html", product_html)
    except Exception as exc:
        result.errors.append(f"Scaffold error (product-index): {exc}")

    # 4a — memory/product/placeholder.html (satisfies the index.yaml catalog stub link)
    try:
        placeholder_src = _scaffold_memory_dir / "product" / "placeholder.html"
        _write(
            specs_dir / "memory" / "product" / "placeholder.html",
            placeholder_src.read_text(encoding="utf-8"),
        )
    except Exception as exc:
        result.errors.append(f"Scaffold error (placeholder): {exc}")

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


_HOTFIX_TASKS_STUB = """\
# Tasks: Hotfix Release — {version_id}

> **Status:** Draft
> **Release ID:** {version_id}
> **Patches release:** {patches_release_id}
> **Owner:** product-engineer
> **Created:** {today}

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## T1 — (Add hotfix tasks here)

- [ ] **Status:** OPEN
- **Owner:** software-engineer
- **Precondições:** nenhuma
- **Files modified:** (list files)
- **Mudanças:** (describe changes)
- **Aceite:** (acceptance criteria)
"""


def scaffold_hotfix_release(
    specs_dir: Path,
    version_id: str,
    patches_release_id: str,
    severity: str,
    templates_dir: Path,
    force: bool = False,
) -> ScaffoldResult:
    """Scaffold a hotfix release directory under specs/releases/<version_id>/.

    Creates SPEC.md (rendered from release_hotfix.md.j2) and TASKS.md (stub).
    PLAN.md is NOT created — the SPEC declares whether it is needed (D24).

    Args:
        specs_dir: Target specs/ directory. Must already exist.
        version_id: SemVer release ID (e.g. v0.5.1). Must match ^v\\d+\\.\\d+\\.\\d+$ and
            have PATCH >= 1 (hotfix releases have PATCH >= 1 per D1).
        patches_release_id: The feature release this hotfix patches
            (e.g. agent-sdd-alignment-v1 or v0.5.0). Must resolve to a directory
            under specs/releases/ or specs/_archive/releases/.
        severity: Hotfix severity — one of LOW, MEDIUM, HIGH, CRITICAL.
        templates_dir: Directory containing Jinja2 .j2 template files.
        force: If True, overwrite existing files. If False, skip existing files.

    Returns:
        ScaffoldResult with lists of created, skipped, and error entries.

    Raises:
        ValueError: If version_id is not valid SemVer, PATCH == 0, or
            patches_release_id does not resolve.
    """
    result = ScaffoldResult()

    # Validate version_id
    if not _RELEASE_SEMVER_RE.match(version_id):
        raise ValueError(
            f"version_id {version_id!r} does not match SemVer pattern ^v\\d+\\.\\d+\\.\\d+$. "
            "Hotfix releases must use a version like v1.2.3."
        )

    # Validate PATCH >= 1
    parts = version_id.lstrip("v").split(".")
    patch = int(parts[2])
    if patch == 0:
        raise ValueError(
            f"version_id {version_id!r} has PATCH=0. Hotfix releases require PATCH >= 1 "
            "(feature releases have PATCH=0, hotfix releases have PATCH >= 1 per D1)."
        )

    # Validate patches_release_id resolves
    candidates = [
        specs_dir / "releases" / patches_release_id,
        specs_dir / "_archive" / "releases" / patches_release_id,
    ]
    if not any(c.is_dir() for c in candidates):
        raise ValueError(
            f"patches_release_id {patches_release_id!r} does not resolve to a directory "
            f"under specs/releases/ or specs/_archive/releases/. "
            f"Checked: {[str(c) for c in candidates]}"
        )

    # Validate severity
    valid_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    if severity not in valid_severities:
        raise ValueError(
            f"severity {severity!r} is not valid. Must be one of {sorted(valid_severities)}."
        )

    today = datetime.date.today().isoformat()
    template_context: dict[str, str] = {
        "version_id": version_id,
        "patches_release_id": patches_release_id,
        "severity": severity,
        "today": today,
    }

    release_dir = specs_dir / "releases" / version_id
    release_dir.mkdir(parents=True, exist_ok=True)

    def _write(path: Path, content: str) -> None:
        if path.exists() and not force:
            result.skipped.append(path)
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            result.created.append(path)
        except OSError as exc:
            result.errors.append(f"Failed to write {path}: {exc}")

    # SPEC.md — rendered from release_hotfix.md.j2
    try:
        spec_content = _render_template(templates_dir, "release_hotfix.md.j2", template_context)
        _write(release_dir / "SPEC.md", spec_content)
    except Exception as exc:
        result.errors.append(f"Template render error (release_hotfix): {exc}")

    # TASKS.md — stub with 0 tasks
    tasks_content = _HOTFIX_TASKS_STUB.format(
        version_id=version_id,
        patches_release_id=patches_release_id,
        today=today,
    )
    _write(release_dir / "TASKS.md", tasks_content)

    return result
