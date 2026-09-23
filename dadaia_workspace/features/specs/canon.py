"""The v6 specs/ canon table — ONE source for "what a specs/ tree contains" (v0.5.1
candidate K4, "one canon table: scaffold is canon rendered, doctor is canon checked").

Six bugs in six weeks shared one property violation: a fresh scaffold failed its own
doctor (``fresh-specs-scaffold-fails-specs-doctor``, ``specs-init-creates-what-doctor
-refuses``, ``scaffold-artifacts-fail-own-workflow-gates``, ``fresh-release-scaffold
-emits-spec-doctor-warnings-042``, ``default-context-scaffold-fails-specs-doctor``,
``release-new-rejects-semver-but-doctor-requires-it`` — all resolved, all in
``specs/bugs/BUGS.jsonl``). The root cause: "what a specs tree contains" was hand-kept
in three-to-four independent places (``specs_canon._CANON_FILE_PATTERNS``,
``scaffolder.py``'s numbered ``_write`` blocks, ``doctor_structural.py``'s TREE-4/TREE-8
required sets, ``doctor_closure_audit.py``'s ``check_archive_dirs_exist``) that could
each drift from the others independently.

This module is the fold target for all four: :data:`CANON` is the ONE declarative table;
:func:`scaffold` renders every ``required_at_birth`` entry (scaffold is canon rendered);
:func:`check_tree`/:func:`is_canon_path`/:func:`canon_violations` check a real tree
against the SAME table (doctor is canon checked). The property this module exists to
hold: ``scaffold(t); check_tree(t) == []`` — proved by
``tests/unit/features/specs/test_canon_property.py``.

Pure module for its CHECKING half (:func:`is_canon_path`, :func:`canon_violations`,
:func:`verdict_violations`): plain data in, plain data out, never touches a filesystem.
Its RENDERING half (:func:`scaffold`, :func:`scaffold_entry`) does
real file I/O by design (that is the whole point of a scaffolder) but touches nothing
outside the *specs_dir*/*public_dir* it is given.

Two consumers share the checking predicate rather than each carrying its own member-set
copy (the drift class this module closes):

* ``doctor_structural.StructuralValidator.check_tree8_canon_root`` — the doctor's
  full-tree conformance sweep.
* ``features.chokepoints.service.push_gate_decision`` — the pre-push specs-canon gate
  (SPEC v0.5.0): every path a push would newly publish under ``specs/`` is checked
  against the SAME predicate, through the existing ``GitObjectReader`` port
  (``list_tree_paths``) — never a second, hand-kept member list.

The canon (operator, 2026-08-28) — the ONLY members permitted under ``specs/``:

    AGENTS.md constitution.md memory/ releases/ backlog/ bugs/ audits/ ADRs/

    releases/{AGENTS.md, _archive/{releases_histo.jsonl, <M.m.p>/**},
              <M.m.p>/{_RELEASE.json, SPEC.md, PLAN.md, TASKS.md, rc-N/{SPEC,PLAN,TASKS}.md,
                       <alpha|rc>-N/{SPEC.md, PLAN.md, TASKS.md}}}
    backlog/{AGENTS.md, BACKLOG.json, _archive/backlog_histo.jsonl}
    bugs/{AGENTS.md, BUGS.jsonl, _archive/bugs_histo.jsonl}
    audits/{AGENTS.md, _archive/audits_histo.jsonl,
            <YYYYMMDD-slug>/{AUDIT.md, FINDINGS.jsonl}}
    ADRs/{AGENTS.md, decisions.jsonl}
    memory/{AGENTS.md, ARCHITECTURE.md, QUALITY.md,
            product/index.md, product/catalog.json, product/<area>/<slug>.md}

Nothing else — no ``.gitkeep``, no dotfiles, no ``remote-bugs/``, no ``reviews/``, no
``.md`` ADRs. Every path checked is POSIX-relative to ``specs/`` (e.g.
``"releases/0.5.0/SPEC.md"``, never an absolute filesystem path or a
backslash-separated one) — the same shape both a filesystem walk (``Path.as_posix()``)
and a git tree listing (``git ls-tree``'s own native output) already produce.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.specs_version import (
    CANONICAL_SPECS_VERSION,
)
from dadaia_workspace.core.workspace_layout import (
    CANON_ROOT_MEMBERS,
    MEMORY_TOPLEVEL_FILES,
    REQUIRED_ROOT_DIRS,
    SPECS_CANON,
    CanonEntry,
)
from dadaia_workspace.features.specs.memory_canon import (
    FIXED_SECTION_BY_PATH,
    read_fixed_fragment,
    render_fixed_section,
)

#: The canon rows live in ``core.workspace_layout`` (0.4.7 FR5: ONE registry of
#: canonical names, shared with the root law, the zone table and the projected
#: ``specs/AGENTS.md`` canon table). This module is their renderer and checker.
CANON: tuple[CanonEntry, ...] = SPECS_CANON

__all__ = [
    "CANON",
    "CANON_ROOT_MEMBERS",
    "REQUIRED_ROOT_DIRS",
    "TEMPLATES",
    "CanonEntry",
    "Violation",
    "canon_violations",
    "check_tree",
    "is_canon_path",
    "scaffold",
    "scaffold_entry",
]

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

_BACKLOG_STUB = '{"schema": "backlog-v1", "active": []}\n'


# ---------------------------------------------------------------------------------
# THE RENDERER MAP — how a canon row's content is produced. Keyed by
# ``CanonEntry.shape``: ``core`` holds the NAMES (the rows), this module holds the
# CONTENT (the templates). A shape absent here is checked but never scaffolded.
#
# * ``"copy"``        — read ``public_dir / template`` verbatim, write byte-identical.
# * ``"static"``      — ``template`` IS the literal content (never ``.format()``-ed —
#                       several static templates hold literal JSON braces).
# * ``"format"``      — ``template.format(**context)``; used only where every brace in
#                       the template is a deliberate placeholder.
# * ``"json_catalog"`` — one dedicated renderer (``json.dumps``, correctly escaped) —
#                       the ONE entry needing computed, safely-escaped JSON content;
#                       folding it into ``"format"`` would risk JSON injection from an
#                       arbitrary ``project_name``.
# ---------------------------------------------------------------------------------
Kind = Literal["copy", "static", "format", "json_catalog"]

TEMPLATES: dict[str, tuple[Kind, str]] = {
    "AGENTS.md": ("copy", "templates/specs-AGENTS.md"),
    "constitution.md": ("format", _CONSTITUTION_STUB),
    "memory/AGENTS.md": ("copy", "scaffold/memory/AGENTS.md"),
    **{f"memory/{name}": ("copy", f"scaffold/memory/{name}") for name in MEMORY_TOPLEVEL_FILES},
    "memory/product/index.md": ("copy", "scaffold/memory/product/index.md"),
    "memory/product/catalog.json": ("json_catalog", ""),
    "releases/AGENTS.md": ("copy", "scaffold/releases/AGENTS.md"),
    "releases/_archive/releases_histo.jsonl": ("static", ""),
    "backlog/AGENTS.md": ("copy", "scaffold/backlog/AGENTS.md"),
    "backlog/BACKLOG.json": ("static", _BACKLOG_STUB),
    "backlog/_archive/backlog_histo.jsonl": ("static", ""),
    "bugs/AGENTS.md": ("copy", "scaffold/bugs/AGENTS.md"),
    "bugs/_archive/bugs_histo.jsonl": ("static", ""),
    "audits/AGENTS.md": ("copy", "scaffold/audits/AGENTS.md"),
    "audits/_archive/audits_histo.jsonl": ("static", ""),
    "ADRs/AGENTS.md": ("copy", "scaffold/ADRs/AGENTS.md"),
    "ADRs/decisions.jsonl": ("static", ""),
}


def is_canon_path(rel_posix: str) -> bool:
    """True iff *rel_posix* (POSIX-relative to ``specs/``) is a v6-canon-conformant
    file path — structural shape only, never sha-specific (see :func:`verdict_violations`
    for the verdict business rule layered on top of the same path shape)."""
    return any(entry.pattern.match(rel_posix) for entry in CANON)


def canon_violations(paths: Iterable[str]) -> list[str]:
    """Every path in *paths* that is NOT canon-conformant, order-preserving.

    *paths* are POSIX-relative to ``specs/`` — a filesystem walk's ``Path.relative_to(
    specs_dir).as_posix()`` or a git tree listing's own native paths, identically.
    """
    return [path for path in paths if not is_canon_path(path)]


@dataclass(frozen=True)
class Violation:
    """One :func:`check_tree` finding: a path and why it fails the canon."""

    path: str
    reason: str


def check_tree(specs_dir: Path) -> list[Violation]:
    """Doctor-facing sibling of :func:`scaffold` — the property this module exists to
    hold is ``scaffold(specs_dir); check_tree(specs_dir) == []``.

    Two passes: every FILE under *specs_dir* must be canon-conformant (mirrors
    :func:`canon_violations`, real filesystem walk instead of a supplied path list),
    and every ``required_at_birth`` entry with a concrete :attr:`CanonEntry.dest` must
    exist. An absent *specs_dir* yields the second pass's findings only (nothing to
    walk, everything required is trivially missing).
    """
    violations: list[Violation] = []
    if specs_dir.is_dir():
        paths = [
            p.relative_to(specs_dir).as_posix() for p in sorted(specs_dir.rglob("*")) if p.is_file()
        ]
        violations.extend(
            Violation(path, "not part of the v6 canon (specs/AGENTS.md)")
            for path in canon_violations(paths)
        )
    for entry in CANON:
        if not entry.required_at_birth or entry.dest is None:
            continue
        if not (specs_dir / entry.dest).is_file():
            violations.append(Violation(entry.dest, "required_at_birth entry is missing"))
    return violations


def default_public_dir() -> Path:
    """``dadaia_workspace/public/`` resolved relative to this installed module — the
    same module-relative idiom already used by ``features.spec_artifacts.memory``
    (retired by this task) and ``features.specs.doctor``'s CLI composition root."""
    return Path(__file__).resolve().parent.parent.parent / "public"


def _today() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


def _render(entry: CanonEntry, *, public_dir: Path, context: dict[str, str]) -> str:
    kind, template = TEMPLATES[entry.shape]
    if kind == "copy":
        text = (public_dir / template).read_text(encoding="utf-8")
    elif kind == "static":
        text = template
    elif kind == "format":
        text = template.format(**context)
    else:
        text = (
            json.dumps(
                {
                    "generated_at": f"{context['today']}T00:00:00Z",
                    # The catalog's ONE writer is `memory.py catalog generate`, which
                    # derives `context` from the tree's own directory name; a scaffold
                    # writing the project label instead was invalid the moment it was
                    # born (`memory.py check` regenerates and compares).
                    "context": context["tree_name"],
                    "features": [],
                },
                indent=2,
            )
            + "\n"
        )
    section_id = FIXED_SECTION_BY_PATH.get(entry.dest or "")
    if section_id is None:
        return text
    return render_fixed_section(text, section_id, read_fixed_fragment(public_dir, section_id))


def scaffold(
    specs_dir: Path,
    *,
    project_name: str = "Projeto",
    force: bool = False,
    public_dir: Path | None = None,
) -> list[Path]:
    """Write every ``required_at_birth`` CANON entry — scaffold is canon rendered.

    An existing target is left untouched unless *force*. Returns the paths actually
    (re)written, in :data:`CANON` order; a skipped (already-present, not forced) entry
    is omitted — the caller that also needs skip/error bookkeeping is
    ``features.specs.scaffolder.scaffold`` (the CLI-facing wrapper, which pre-checks
    existence to report ``ScaffoldResult.skipped`` without changing this fold).
    """
    resolved_public = public_dir if public_dir is not None else default_public_dir()
    context = {
        "today": _today(),
        "project_name": project_name,
        "tree_name": specs_dir.resolve().parent.name,
        "specs_pattern_version": str(CANONICAL_SPECS_VERSION),
    }
    created: list[Path] = []
    for entry in CANON:
        # Only "no destination" disqualifies an entry: a required_at_birth row always
        # has a renderer (``memory/product/catalog.json``'s is computed, not a template —
        # a prior guard skipped it for having no template string and silently dropped it
        # from every fresh scaffold: fresh-specs-scaffold-fails-specs-doctor's own class).
        if not entry.required_at_birth or entry.dest is None:
            continue
        target = specs_dir / entry.dest
        if target.exists() and not force:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            _render(entry, public_dir=resolved_public, context=context), encoding="utf-8"
        )
        created.append(target)
    return created


def scaffold_entry(specs_dir: Path, rel_path: str, /, **context: str) -> Path:
    """Render and write ONE canon-conformant, on-demand entry — the generic sibling of
    :func:`scaffold`'s birth-time fold (e.g. ``scaffold_entry(specs_dir,
    "releases/0.6.0/SPEC.md", release_id="0.6.0")``).

    File-level no-clobber: refuses (``FileExistsError``) when *rel_path* already
    exists. Raises ``ValueError`` when *rel_path* matches no :data:`CANON` entry, or
    matches one with no renderable template (a shape this module only ever checks,
    never scaffolds on demand, e.g. a verdict handoff).
    """
    entry = next((e for e in CANON if e.pattern.match(rel_path)), None)
    if entry is None:
        raise ValueError(f"{rel_path!r} is not a v6-canon-conformant path — nothing to scaffold.")
    if entry.shape not in TEMPLATES:
        raise ValueError(f"{rel_path!r} (area={entry.area}) has no scaffold template.")
    target = specs_dir / rel_path
    if target.exists():
        raise FileExistsError(f"{target} already exists — refusing to overwrite (no-clobber).")
    rendered = _render(
        entry,
        public_dir=default_public_dir(),
        context={"today": _today(), **context},
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    return target
