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

_BACKLOG_STUB = """\
## ACTIVE

## LEDGER
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
    # v6 canon (FR1, specs_pattern_version 5 -> 6): every scaffold README.md retires
    # into its area's AGENTS.md — root and memory/ already carried one; backlog/,
    # bugs/, releases/ and audits/ now do too.
    try:
        _write(
            specs_dir / "AGENTS.md",
            (templates_dir / "specs-AGENTS.md").read_text(encoding="utf-8"),
        )
        _write(
            specs_dir / "memory" / "AGENTS.md",
            (_scaffold_memory_dir / "AGENTS.md").read_text(encoding="utf-8"),
        )
        for area in ("backlog", "bugs", "releases", "audits"):
            _write(
                specs_dir / area / "AGENTS.md",
                (_scaffold_dir / area / "AGENTS.md").read_text(encoding="utf-8"),
            )
    except Exception as exc:
        result.errors.append(f"Scaffold rules error: {exc}")

    # 2-4 — born-markdown memory scaffolds (.md only).
    # memory-markdown-source-v1: .md is the sole source of truth; the legacy
    # .yaml/.html scaffolds and the placeholder.html stub were retired (no committed
    # HTML — the panel renders .md in-memory, D-4).
    # v6 canon (FR1/A1.5/A1.6, T-050-06): the top-level trio renamed to
    # ARCHITECTURE.md, TECHSTACK.md, QUALITY.md — source and dest share the name.
    _memory_md_stubs = [
        ("ARCHITECTURE.md", specs_dir / "memory" / "ARCHITECTURE.md"),
        ("TECHSTACK.md", specs_dir / "memory" / "TECHSTACK.md"),
        ("QUALITY.md", specs_dir / "memory" / "QUALITY.md"),
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

    # 6 — backlog/BACKLOG.md (SPEC v0.12.0 FR1/FR3, ADR #14): the single-source
    # document skeleton — both section headings, nothing else. Matches exactly what
    # `features.spec_artifacts.new_artifacts.backlog_new` creates when it finds no
    # document; a fresh scaffold and a fresh `backlog new` share one skeleton shape.
    _write(specs_dir / "backlog" / "BACKLOG.md", _BACKLOG_STUB)

    # 7, 8 — releases/ landing zones (v6 canon: at most one live {version}/ plus
    # _ideas/{version}/ for pre-approval drafts and _archive/{version}/ for closed
    # releases — RELEASE.jsonl-ready). Root specs/_archive/ and specs/assets/ retire:
    # neither is a v6 canon root member (TREE-8).
    _touch(specs_dir / "releases" / "_ideas" / ".gitkeep")
    _touch(specs_dir / "releases" / "_archive" / ".gitkeep")

    # 9 — ADRs/ (v6 canon root member; FR19 owns the decision-record law/index — "No
    # CLI verb, no doctor rule beyond FR1's folder shape").
    _touch(specs_dir / "ADRs" / ".gitkeep")

    # 10, 11, 12 — per-artifact _archive dirs (v0.1.46 AC-4, FROZEN gate-class landing
    # zone). Each additive artifact family (backlog/audits/bugs) gets its own _archive/
    # subdir where terminal/dispositioned entries are git-mv'd. The gate classifies these
    # three subdirs FROZEN (features/spec_context/gate_policy.py); creating them here
    # ensures new + upgraded workspaces have the landing zone before any archive move
    # (the bugs->JSONL migration moves source .md into specs/bugs/_archive/ in-process).
    _touch(specs_dir / "backlog" / "_archive" / ".gitkeep")
    _touch(specs_dir / "audits" / "_archive" / ".gitkeep")
    _touch(specs_dir / "bugs" / "_archive" / ".gitkeep")

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

## Validation Dependency Table

| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |
|---|---|---|---|---|
| WS-1 | (deliverable of this segment) | (how it is validated in isolation) | none | none |
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

- [ ] T1 - (Add tasks here)
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
