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
Its RENDERING half (:func:`scaffold`, :func:`scaffold_entry`, :func:`release_new`) does
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

    releases/{AGENTS.md, _ideas/{AGENTS.md, <M.m.p>/SPEC.md},
              _archive/{releases_histo.jsonl, <M.m.p>/**},
              <M.m.p>/{RELEASE.json, SPEC.md, PLAN.md, TASKS.md,
                       verdicts/<40hex>.handoff.json,
                       <alpha|rc>-N/{SPEC.md, PLAN.md, TASKS.md}}}
    backlog/{AGENTS.md, BACKLOG.json,
             _archive/{backlog_histo.jsonl, consumed_backlog_histo.jsonl}}
    bugs/{AGENTS.md, BUGS.jsonl, _archive/bugs_histo.jsonl}
    audits/{AGENTS.md, _archive/audits_histo.jsonl,
            <YYYYMMDD-slug>/{AUDIT.md, FINDINGS.jsonl}}
    ADRs/{AGENTS.md, decisions.jsonl, _superseded/superseded.jsonl}
    memory/{AGENTS.md, ARCHITECTURE.md, QUALITY.md, TECHSTACK.md,
            product/index.md, product/catalog.json, product/<area>/<slug>.md}

Nothing else — no ``.gitkeep``, no dotfiles, no ``remote-bugs/``, no ``reviews/``, no
``.md`` ADRs. Every path checked is POSIX-relative to ``specs/`` (e.g.
``"releases/0.5.0/SPEC.md"``, never an absolute filesystem path or a
backslash-separated one) — the same shape both a filesystem walk (``Path.as_posix()``)
and a git tree listing (``git ls-tree``'s own native output) already produce.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.specs_version import (
    CANONICAL_SPECS_VERSION,
    RELEASE_ID_FRAGMENT,
    is_release_semver,
)
from dadaia_workspace.core.workspace_layout import AUDIT_DIR_NAME_PATTERN
from dadaia_workspace.features.specs.memory_canon import MEMORY_TOPLEVEL_FILES

__all__ = [
    "CANON",
    "CANON_ROOT_MEMBERS",
    "REQUIRED_ROOT_DIRS",
    "CanonEntry",
    "Violation",
    "canon_violations",
    "check_tree",
    "is_canon_path",
    "release_new",
    "scaffold",
    "scaffold_entry",
    "verdict_violations",
]

_SEMVER = RELEASE_ID_FRAGMENT
_SHA40 = r"[0-9a-f]{40}"
#: One fact, one place (core.workspace_layout, SPEC-DOC-030's own single home) — never
#: a second, independently hand-kept copy of the audit-dir date-slug shape.
_YYYYMMDD_SLUG = AUDIT_DIR_NAME_PATTERN
#: A release segment name (ADR-1/ADR-5, mirrors ``scaffolder._SEGMENT_RE``): an
#: ``alpha-N``/``rc-N`` sub-phase directory under a release, e.g.
#: ``releases/0.6.0/alpha-1/``.
_SEGMENT = r"(?:alpha|rc)-\d+"
_AREA = r"[a-z][a-z0-9_-]*"
_SLUG = r"[a-z][a-z0-9_-]*"

#: The root member a :class:`CanonEntry` lives under. Distinct from a filesystem "area"
#: only for the two bare root files (``AGENTS.md``, ``constitution.md``), each its own
#: singleton member — every other value names the directory area it governs. Deriving
#: :data:`CANON_ROOT_MEMBERS` as ``{e.area for e in CANON}`` then needs zero special
#: casing (see below) — the whole reason this field carries 8 values, not 6.
Area = Literal[
    "AGENTS.md", "constitution.md", "memory", "releases", "backlog", "bugs", "audits", "ADRs"
]

#: How a required-at-birth (or on-demand, via :func:`scaffold_entry`) entry's content is
#: produced:
#:
#: * ``"copy"``       — read ``public_dir / template`` verbatim, write byte-identical.
#: * ``"static"``      — ``template`` IS the literal content (never ``.format()``-ed —
#:                        several static templates hold literal JSON braces).
#: * ``"format"``      — ``template.format(**context)``; used only where every brace in
#:                        the template is a deliberate placeholder (constitution.md, the
#:                        release SPEC.md stub).
#: * ``"json_catalog"`` — one dedicated renderer (``json.dumps``, correctly escaped) —
#:                        the ONE entry needing computed, safely-escaped JSON content;
#:                        folding it into ``"format"`` would risk JSON injection from an
#:                        arbitrary ``project_name``.
Kind = Literal["copy", "static", "format", "json_catalog"]


@dataclass(frozen=True)
class CanonEntry:
    """One row of the canon table: a path SHAPE plus (optionally) how to render it.

    ``dest`` is the concrete ``specs/``-relative path for an entry with no variable
    path segment (every ``required_at_birth`` entry today has none) — :func:`scaffold`
    folds over these directly, with no regex-to-literal-path reverse engineering.
    ``dest`` is ``None`` for a variable-shaped entry (a release id, a sha, a slug); such
    an entry is never ``required_at_birth`` and is rendered, if at all, through
    :func:`scaffold_entry` instead.
    """

    pattern: re.Pattern[str]
    kind: Kind
    required_at_birth: bool
    template: str | None
    area: Area
    dest: str | None = None


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

_RELEASE_SPEC_STUB = """\
# SPEC — Release: {release_id}

**Status:** Draft
**Release ID:** {release_id}
**Owner:** product-engineer
**Opened:** {today}

---

## 1. Problem and context

(Describe the problem this release solves.)

---

## 2. Objective

(State the release objective in one sentence.)

---

## 3. Scope

(List the scope clusters / acceptance criteria.)

---

## 4. Out of scope

(Explicitly list what this release does NOT cover.)

---

## 5. Dependencies and risks

(Upstream blockers, sequencing constraints, risk table.)
"""

_BACKLOG_STUB = '{"schema": "backlog-v1", "active": []}\n'


def _copy(rel: str) -> str:
    """A ``"copy"`` entry's ``template`` — a ``public_dir``-relative source path."""
    return rel


# ---------------------------------------------------------------------------------
# THE CANON TABLE — one row per canon-conformant path shape. Order mirrors the
# root-member order in the module docstring (root, memory, releases, backlog, bugs,
# audits, ADRs); within an area, required-at-birth rows come first.
# ---------------------------------------------------------------------------------
CANON: tuple[CanonEntry, ...] = (
    # -- root --------------------------------------------------------------------
    CanonEntry(
        re.compile(r"^AGENTS\.md$"),
        "copy",
        True,
        _copy("templates/specs-AGENTS.md"),
        "AGENTS.md",
        "AGENTS.md",
    ),
    CanonEntry(
        re.compile(r"^constitution\.md$"),
        "format",
        True,
        _CONSTITUTION_STUB,
        "constitution.md",
        "constitution.md",
    ),
    # -- memory/ -------------------------------------------------------------------
    CanonEntry(
        re.compile(r"^memory/AGENTS\.md$"),
        "copy",
        True,
        _copy("scaffold/memory/AGENTS.md"),
        "memory",
        "memory/AGENTS.md",
    ),
    # The top-level memory trio — folded over the ONE memory-canon table (F011):
    # never a second, hand-kept row per file.
    *(
        CanonEntry(
            re.compile(rf"^memory/{re.escape(name)}$"),
            "copy",
            True,
            _copy(f"scaffold/memory/{name}"),
            "memory",
            f"memory/{name}",
        )
        for name in MEMORY_TOPLEVEL_FILES
    ),
    CanonEntry(
        re.compile(r"^memory/product/index\.md$"),
        "copy",
        True,
        _copy("scaffold/memory/product/index.md"),
        "memory",
        "memory/product/index.md",
    ),
    CanonEntry(
        re.compile(r"^memory/product/catalog\.json$"),
        "json_catalog",
        True,
        None,
        "memory",
        "memory/product/catalog.json",
    ),
    CanonEntry(
        re.compile(rf"^memory/product/{_AREA}/{_SLUG}\.md$"),
        "copy",
        False,
        None,
        "memory",
    ),
    # -- releases/ -----------------------------------------------------------------
    CanonEntry(
        re.compile(r"^releases/AGENTS\.md$"),
        "copy",
        True,
        _copy("scaffold/releases/AGENTS.md"),
        "releases",
        "releases/AGENTS.md",
    ),
    CanonEntry(
        re.compile(r"^releases/_ideas/AGENTS\.md$"),
        "copy",
        True,
        _copy("scaffold/releases/_ideas/AGENTS.md"),
        "releases",
        "releases/_ideas/AGENTS.md",
    ),
    CanonEntry(
        re.compile(r"^releases/_archive/releases_histo\.jsonl$"),
        "static",
        True,
        "",
        "releases",
        "releases/_archive/releases_histo.jsonl",
    ),
    CanonEntry(
        re.compile(rf"^releases/_ideas/{_SEMVER}/SPEC\.md$"), "format", False, None, "releases"
    ),
    CanonEntry(re.compile(rf"^releases/_archive/{_SEMVER}/.+$"), "static", False, None, "releases"),
    CanonEntry(
        re.compile(rf"^releases/{_SEMVER}/RELEASE\.json$"), "static", False, None, "releases"
    ),
    CanonEntry(
        re.compile(rf"^releases/(?P<release_id>{_SEMVER})/SPEC\.md$"),
        "format",
        False,
        _RELEASE_SPEC_STUB,
        "releases",
    ),
    CanonEntry(re.compile(rf"^releases/{_SEMVER}/PLAN\.md$"), "static", False, None, "releases"),
    CanonEntry(re.compile(rf"^releases/{_SEMVER}/TASKS\.md$"), "static", False, None, "releases"),
    CanonEntry(
        re.compile(rf"^releases/{_SEMVER}/verdicts/{_SHA40}\.handoff\.json$"),
        "static",
        False,
        None,
        "releases",
    ),
    # A segmented release's SPEC/PLAN/TASKS live one directory deeper
    # (``releases/<M.m.p>/<alpha|rc>-N/{SPEC,PLAN,TASKS}.md`` —
    # ``scaffolder.scaffold_release_segment``, ``dd-release-implement`` §2/§4). Never
    # required_at_birth: a segment is opened on demand, well after the release itself.
    CanonEntry(
        re.compile(rf"^releases/{_SEMVER}/{_SEGMENT}/SPEC\.md$"), "static", False, None, "releases"
    ),
    CanonEntry(
        re.compile(rf"^releases/{_SEMVER}/{_SEGMENT}/PLAN\.md$"), "static", False, None, "releases"
    ),
    CanonEntry(
        re.compile(rf"^releases/{_SEMVER}/{_SEGMENT}/TASKS\.md$"), "static", False, None, "releases"
    ),
    # -- backlog/ ------------------------------------------------------------------
    CanonEntry(
        re.compile(r"^backlog/AGENTS\.md$"),
        "copy",
        True,
        _copy("scaffold/backlog/AGENTS.md"),
        "backlog",
        "backlog/AGENTS.md",
    ),
    CanonEntry(
        re.compile(r"^backlog/BACKLOG\.json$"),
        "static",
        True,
        _BACKLOG_STUB,
        "backlog",
        "backlog/BACKLOG.json",
    ),
    CanonEntry(
        re.compile(r"^backlog/_archive/backlog_histo\.jsonl$"),
        "static",
        True,
        "",
        "backlog",
        "backlog/_archive/backlog_histo.jsonl",
    ),
    CanonEntry(
        re.compile(r"^backlog/_archive/consumed_backlog_histo\.jsonl$"),
        "static",
        False,
        None,
        "backlog",
    ),
    # -- bugs/ ---------------------------------------------------------------------
    CanonEntry(
        re.compile(r"^bugs/AGENTS\.md$"),
        "copy",
        True,
        _copy("scaffold/bugs/AGENTS.md"),
        "bugs",
        "bugs/AGENTS.md",
    ),
    CanonEntry(re.compile(r"^bugs/BUGS\.jsonl$"), "static", False, None, "bugs"),
    CanonEntry(
        re.compile(r"^bugs/_archive/bugs_histo\.jsonl$"),
        "static",
        True,
        "",
        "bugs",
        "bugs/_archive/bugs_histo.jsonl",
    ),
    # -- audits/ -------------------------------------------------------------------
    CanonEntry(
        re.compile(r"^audits/AGENTS\.md$"),
        "copy",
        True,
        _copy("scaffold/audits/AGENTS.md"),
        "audits",
        "audits/AGENTS.md",
    ),
    CanonEntry(
        re.compile(r"^audits/_archive/audits_histo\.jsonl$"),
        "static",
        True,
        "",
        "audits",
        "audits/_archive/audits_histo.jsonl",
    ),
    CanonEntry(
        re.compile(rf"^audits/{_YYYYMMDD_SLUG}/AUDIT\.md$"), "static", False, None, "audits"
    ),
    CanonEntry(
        re.compile(rf"^audits/{_YYYYMMDD_SLUG}/FINDINGS\.jsonl$"), "static", False, None, "audits"
    ),
    # -- ADRs/ ---------------------------------------------------------------------
    CanonEntry(
        re.compile(r"^ADRs/AGENTS\.md$"),
        "copy",
        True,
        _copy("scaffold/ADRs/AGENTS.md"),
        "ADRs",
        "ADRs/AGENTS.md",
    ),
    CanonEntry(
        re.compile(r"^ADRs/decisions\.jsonl$"), "static", True, "", "ADRs", "ADRs/decisions.jsonl"
    ),
    CanonEntry(
        re.compile(r"^ADRs/_superseded/superseded\.jsonl$"),
        "static",
        True,
        "",
        "ADRs",
        "ADRs/_superseded/superseded.jsonl",
    ),
)

#: The v6 canon ROOT member names — every entry permitted directly under ``specs/``.
#: Derived from :data:`CANON` itself (zero special-casing: :data:`Area` already carries
#: one value per root member, including the two bare root files) — the doctor's TREE-8
#: root-membership tier is the one consumer of this frozenset.
CANON_ROOT_MEMBERS: frozenset[str] = frozenset(entry.area for entry in CANON)

#: TREE-4's required directories, derived (not hand-kept): every area that pre-creates
#: its own ``_archive/<area>_histo.jsonl`` at birth also needs its directory to exist —
#: exactly {audits, backlog, bugs, releases} today, self-updating if a future area gains
#: a birth-time histo entry.
REQUIRED_ROOT_DIRS: tuple[str, ...] = tuple(
    sorted(
        {
            entry.area
            for entry in CANON
            if entry.required_at_birth
            and entry.dest
            and entry.dest.startswith(f"{entry.area}/_archive/")
        }
    )
)

#: The verdict-filename shape, isolated (matches the trailing component
#: ``releases/<M.m.p>/verdicts/<40hex>.handoff.json`` already admitted by the CANON
#: table above), used by :func:`verdict_violations` to pick the sha out of an
#: otherwise-canon-conformant verdict path.
_VERDICT_RE = re.compile(rf"^releases/{_SEMVER}/verdicts/({_SHA40})\.handoff\.json$")

#: The legacy release-id slug form new releases may still mint (pre-canon-v6 repos);
#: bare SemVer (:func:`~dadaia_workspace.core.specs_version.is_release_semver`) is the
#: preferred, canon-conformant form. A slug-named release directory does not match any
#: CANON entry above (the doctor's TREE-8/SPEC-DOC-027 checks already treat it as
#: non-canon for a live release dir) — :func:`release_new` supports it anyway, honestly
#: outside the canon-driven render path, for backward compatibility.
_LEGACY_RELEASE_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")


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


def verdict_violations(paths: Iterable[str], head_sha: str, parent_sha: str | None) -> list[str]:
    """The verdict business rule (operator, 2026-08-28): ``verdicts/`` may hold at most
    ONE file whose 40-hex name equals *head_sha* or *head_sha*'s first parent
    (*parent_sha*).

    Every verdict-shaped path in *paths* whose sha is NEITHER *head_sha* nor
    *parent_sha* is a violation (stale — SPEC-DOC-044). When more than one verdict
    file's sha DOES match (an unusual double-verdict state), every match past the
    first is ALSO a violation — "at most one", not "any number matching". Paths that
    are not verdict-shaped at all (already covered by :func:`canon_violations`) are
    ignored here, never double-reported.
    """
    allowed = {sha for sha in (head_sha, parent_sha) if sha}
    matches: list[str] = []
    violations: list[str] = []
    for path in paths:
        match = _VERDICT_RE.match(path)
        if match is None:
            continue
        sha = match.group(1)
        if sha in allowed:
            matches.append(path)
        else:
            violations.append(path)
    violations.extend(sorted(matches[1:]))
    return violations


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
            Violation(path, "not part of the v6 canon (DADAIA.md §6)")
            for path in canon_violations(paths)
        )
    for entry in CANON:
        if not entry.required_at_birth or entry.dest is None:
            continue
        if not (specs_dir / entry.dest).is_file():
            violations.append(Violation(entry.dest, "required_at_birth entry is missing"))
    return violations


def _default_public_dir() -> Path:
    """``dadaia_workspace/public/`` resolved relative to this installed module — the
    same module-relative idiom already used by ``features.spec_artifacts.memory``
    (retired by this task) and ``features.specs.doctor``'s CLI composition root."""
    return Path(__file__).resolve().parent.parent.parent / "public"


def _today() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


def _render(entry: CanonEntry, *, public_dir: Path, context: dict[str, str]) -> str:
    if entry.kind == "copy":
        assert entry.template is not None
        return (public_dir / entry.template).read_text(encoding="utf-8")
    if entry.kind == "static":
        assert entry.template is not None
        return entry.template
    if entry.kind == "format":
        assert entry.template is not None
        return entry.template.format(**context)
    if entry.kind == "json_catalog":
        return (
            json.dumps(
                {
                    "generated_at": f"{context['today']}T00:00:00Z",
                    "context": context["project_name"],
                    "features": [],
                },
                indent=2,
            )
            + "\n"
        )
    raise AssertionError(f"unknown CanonEntry.kind: {entry.kind!r}")  # pragma: no cover


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
    resolved_public = public_dir if public_dir is not None else _default_public_dir()
    context = {
        "today": _today(),
        "project_name": project_name,
        "specs_pattern_version": str(CANONICAL_SPECS_VERSION),
    }
    created: list[Path] = []
    for entry in CANON:
        # NOTE: entry.template is None is a VALID, required state for kind=="json_catalog"
        # (memory/product/catalog.json) — its content is computed by _render, not read
        # from a template. Do not skip on entry.template is None here; a prior version of
        # this guard did, silently dropping the one required_at_birth json_catalog entry
        # from every fresh scaffold (fresh-specs-scaffold-fails-specs-doctor's own class
        # of bug, reproduced structurally). Only "no destination" disqualifies an entry.
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
    if entry.template is None:
        raise ValueError(f"{rel_path!r} (area={entry.area}) has no scaffold template.")
    target = specs_dir / rel_path
    if target.exists():
        raise FileExistsError(f"{target} already exists — refusing to overwrite (no-clobber).")
    rendered = _render(
        entry,
        public_dir=_default_public_dir(),
        context={"today": _today(), **context},
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    return target


#: Every artifact ``release_new`` refuses to mint over (CWE-73/CWE-59 hardening,
#: carried over from the retired ``features.spec_artifacts.new_artifacts``): a release
#: directory a caller can already write RELEASE.json/PLAN.md/TASKS.md into ahead of
#: ``release new`` (e.g. `dadaia release new` racing a segment scaffold) must never
#: have any of its four canonical artifacts silently overwritten.
_RELEASE_ARTIFACT_NAMES: tuple[str, ...] = ("SPEC.md", "PLAN.md", "TASKS.md", "RELEASE.json")


def release_new(specs_dir: Path, release_id: str) -> Path:
    """Create ``specs/releases/<release_id>/SPEC.md`` with a canonical stub — the
    ``dadaia release new`` implementation (moved here from the retired
    ``features.spec_artifacts.new_artifacts``, v0.5.1 K4).

    *release_id* must be the SemVer canon (``is_release_semver`` — preferred, matches
    the ``specs doctor`` SPEC-DOC-027 naming canon) OR the legacy slug
    (``^[a-z][a-z0-9-]+$``, backward compatibility for a pre-canon-v6 repo).

    No-clobber, three layers deep:

    1. Directory-level (unchanged, regression contract
       ``test_existing_dir_raises_file_exists_error``): refuses whenever
       ``releases/<release_id>/`` already exists at all, even if none of its four
       canonical artifacts do yet — a release directory is a single unit, not a bag
       of independently-clobberable files.
    2. Per-artifact (defense in depth): even were the directory check ever bypassed,
       refuses whenever any of SPEC.md/PLAN.md/TASKS.md/RELEASE.json already exists
       under it.
    3. Symlink refusal (CWE-59): refuses when ``releases/<release_id>`` (or
       ``releases/`` itself) already exists as a symlink — minting through a symlink
       could write the release stub outside *specs_dir* entirely.

    A bare-SemVer *release_id* renders through :func:`scaffold_entry`, over the SAME
    ``releases/<M.m.p>/SPEC.md`` CANON entry every other on-demand entry renders
    through — one render path, not two (M5, 2026-08-29 six-axis review). A legacy slug
    is not canon-shaped (no CANON entry matches it — TREE-8/SPEC-DOC-027 already treat
    a live slug-named release dir as non-canon), so it falls back to rendering the same
    stub template directly.
    """
    if not (is_release_semver(release_id) or _LEGACY_RELEASE_SLUG_RE.match(release_id)):
        raise ValueError(
            f"Invalid release ID {release_id!r}. "
            "Must be bare SemVer ^\\d+\\.\\d+\\.\\d+$ (e.g. 0.1.23 — preferred, matches "
            "the specs-doctor naming canon; a `v`-prefixed id is the retired archive axis "
            "and is refused at minting, AS-13) or the legacy slug ^[a-z][a-z0-9-]+$ "
            "(lowercase letters, digits, and hyphens; must start with a letter)."
        )

    releases_root = specs_dir / "releases"
    release_dir = releases_root / release_id
    if releases_root.is_symlink() or release_dir.is_symlink():
        raise FileExistsError(
            f"{release_dir} resolves through a symlink — refusing to mint a release "
            "through one (it could write outside the specs/ tree)."
        )
    for name in _RELEASE_ARTIFACT_NAMES:
        artifact = release_dir / name
        if artifact.exists() or artifact.is_symlink():
            raise FileExistsError(
                f"{artifact} already exists — refusing to overwrite a minted release artifact."
            )

    if is_release_semver(release_id):
        return scaffold_entry(specs_dir, f"releases/{release_id}/SPEC.md", release_id=release_id)

    # Legacy slug: no CANON entry matches it, so it is rendered directly from the same
    # stub template scaffold_entry would otherwise use.
    release_dir.mkdir(parents=True, exist_ok=True)
    spec_path = release_dir / "SPEC.md"
    spec_path.write_text(
        _RELEASE_SPEC_STUB.format(release_id=release_id, today=_today()), encoding="utf-8"
    )
    return spec_path
