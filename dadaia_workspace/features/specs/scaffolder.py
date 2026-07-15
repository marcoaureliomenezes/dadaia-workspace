"""Scaffolder for SDD release-lifecycle specs directory structure.

Pure module — no I/O outside the supplied specs_dir/templates_dir.
Creates the canonical SDD directory tree for new repositories.
"""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import jinja2
from jinja2.sandbox import SandboxedEnvironment

from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION, RELEASE_SEMVER_RE


@dataclass
class ScaffoldResult:
    """Result of a scaffold() call."""

    created: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


_CONSTITUTION_STUB = """\
---
specs_pattern_version: {specs_pattern_version}
---
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
    # SandboxedEnvironment blocks access to Python internals (e.g. dunder
    # attributes) so a hostile project_name/version cannot reach a sandbox
    # escape via template syntax. autoescape stays off: templates render
    # Markdown, not HTML.
    env = SandboxedEnvironment(
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
            content = _CONSTITUTION_STUB.format(
                project_name=project_name,
                today=today,
                specs_pattern_version=CANONICAL_SPECS_VERSION,
            )
            constitution_path.write_text(content, encoding="utf-8")
            result.created.append(constitution_path)
        except OSError as exc:
            result.errors.append(f"Failed to write {constitution_path}: {exc}")

    # Locate canonical public assets adjacent to templates_dir.
    _scaffold_dir = templates_dir.parent / "scaffold"
    _scaffold_memory_dir = _scaffold_dir / "memory"

    # 2 — scoped SDD rules. This exact template is what doctor compares against.
    try:
        _write(
            specs_dir / "AGENTS.md",
            (templates_dir / "specs-AGENTS.md").read_text(encoding="utf-8"),
        )
        _write(
            specs_dir / "memory" / "AGENTS.md",
            (_scaffold_memory_dir / "AGENTS.md").read_text(encoding="utf-8"),
        )
    except Exception as exc:
        result.errors.append(f"Scaffold rules error: {exc}")

    # 2-4 — born-markdown memory scaffolds (.md only).
    # memory-markdown-source-v1: .md is the sole source of truth; the legacy
    # .yaml/.html scaffolds and the placeholder.html stub were retired (no committed
    # HTML — the panel renders .md in-memory, D-4).
    _memory_md_stubs = [
        ("architecture.md", specs_dir / "memory" / "architecture.md"),
        ("tech-stack.md", specs_dir / "memory" / "tech-stack.md"),
        ("quality-assurance.md", specs_dir / "memory" / "quality-assurance.md"),
        ("product/index.md", specs_dir / "memory" / "product" / "index.md"),
    ]
    for rel, dest in _memory_md_stubs:
        try:
            src = _scaffold_memory_dir / rel
            _write(dest, src.read_text(encoding="utf-8"))
        except Exception as exc:
            result.errors.append(f"Scaffold error ({rel}): {exc}")

    # An empty product catalog is valid and makes a fresh tree self-pull ready.
    _write(
        specs_dir / "memory" / "product" / "catalog.json",
        json.dumps(
            {"generated_at": f"{today}T00:00:00Z", "context": project_name, "features": []},
            indent=2,
        )
        + "\n",
    )

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

    # 11, 12, 13 — per-artifact _archive dirs (v0.1.46 AC-4, FROZEN gate-class landing
    # zone). Each additive artifact family (backlog/audits/bugs) gets its own _archive/
    # subdir where terminal/dispositioned entries are git-mv'd. The gate classifies these
    # three subdirs FROZEN (features/spec_context/gate_policy.py); creating them here
    # ensures new + upgraded workspaces have the landing zone before any archive move
    # (the bugs->JSONL migration moves source .md into specs/bugs/_archive/ in-process).
    _touch(specs_dir / "backlog" / "_archive" / ".gitkeep")
    _touch(specs_dir / "audits" / "_archive" / ".gitkeep")
    _touch(specs_dir / "bugs" / "_archive" / ".gitkeep")

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
    if not RELEASE_SEMVER_RE.match(version_id):
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


# Segment naming (ADR-1/ADR-5): alpha-N or rc-N (1-indexed, hyphenated).
_SEGMENT_RE = re.compile(r"^(alpha|rc)-\d+$")

_SEGMENT_SPEC_STUB = """\
# SPEC: {version_id} {segment} - <slug>

**Status:** Draft
**Release ID:** {version_id}
**Segment:** {segment}
**Owner:** product-engineer
**Created:** {today}

---

## Objective

(Define this segment's objective.)
"""

_SEGMENT_PLAN_STUB = """\
# PLAN: {version_id} {segment} - <slug>

**Status:** Draft
**Release ID:** {version_id}
**Segment:** {segment}
**Owner:** product-engineer
**Created:** {today}

---

## Approach

(Define the implementation approach for this segment.)
"""

_SEGMENT_TASKS_STUB = """\
# TASKS: {version_id} {segment} - <slug>

**Status:** Draft
**Release ID:** {version_id}
**Segment:** {segment}
**Owner:** product-engineer
**Created:** {today}

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T1 — (Add tasks here)

- **Status:** [ ]
- **Owner:** software-engineer
- **Acceptance:** (acceptance criteria)
"""


def scaffold_release_segment(
    specs_dir: Path,
    version_id: str,
    segment: str,
    force: bool = False,
) -> ScaffoldResult:
    """Scaffold a release **segment** under specs/releases/<version_id>/<segment>/.

    Creates SPEC.md + PLAN.md + TASKS.md stubs for an `alpha-N` or `rc-N` segment
    (ADR-1/ADR-5). The parent release directory is created if absent.

    Args:
        specs_dir: Target specs/ directory.
        version_id: SemVer release id (e.g. ``v0.1.6``); must match ``^v\\d+\\.\\d+\\.\\d+$``.
        segment: Segment name; must match ``^(alpha|rc)-\\d+$`` (e.g. ``alpha-1``, ``rc-2``).
        force: Overwrite existing files when True; otherwise skip them.

    Returns:
        ScaffoldResult with created/skipped/errors.

    Raises:
        ValueError: If version_id is not SemVer or segment is malformed.
    """
    if not RELEASE_SEMVER_RE.match(version_id):
        raise ValueError(
            f"version_id {version_id!r} does not match SemVer pattern "
            "^v<MAJOR>.<MINOR>.<PATCH>$ (e.g. v0.1.6)."
        )
    if not _SEGMENT_RE.match(segment):
        raise ValueError(
            f"segment {segment!r} is not valid. Use 'alpha-<N>' or 'rc-<N>' "
            "(1-indexed, hyphenated), e.g. alpha-1, rc-2."
        )

    result = ScaffoldResult()
    today = datetime.date.today().isoformat()
    seg_dir = specs_dir / "releases" / version_id / segment
    ctx = {"version_id": version_id, "segment": segment, "today": today}

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

    _write(seg_dir / "SPEC.md", _SEGMENT_SPEC_STUB.format(**ctx))
    _write(seg_dir / "PLAN.md", _SEGMENT_PLAN_STUB.format(**ctx))
    _write(seg_dir / "TASKS.md", _SEGMENT_TASKS_STUB.format(**ctx))

    return result
