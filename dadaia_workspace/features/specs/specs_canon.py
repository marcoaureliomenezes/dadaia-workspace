"""The v6 specs/ canon predicate — ONE source for "is this path conformant" (v0.5.0
specs-canon closure, operator ruling 2026-08-28).

Pure, zero-I/O module: every function here takes plain data (POSIX-relative path
strings) and returns plain data — never touches a filesystem or spawns a subprocess.
Two consumers share this ONE predicate family rather than each carrying its own
member-set copy (the drift class this module closes):

* ``doctor_structural.StructuralValidator.check_tree8_canon_root`` — the doctor's
  full-tree conformance sweep (replaces its former inline ``_TREE8_CANON_ROOT`` root-only
  set + separate dotfile sweep with one call to :func:`canon_violations`).
* ``features.chokepoints.service.push_gate_decision`` — the pre-push specs-canon gate
  (SPEC v0.5.0, this task): every path a push would newly publish under ``specs/`` is
  checked against the SAME predicate, through the existing ``GitObjectReader`` port
  (``list_tree_paths``) — never a second, hand-kept member list.

The canon (operator, 2026-08-28) — the ONLY members permitted under ``specs/``:

    AGENTS.md constitution.md memory/ releases/ backlog/ bugs/ audits/ ADRs/

    releases/{AGENTS.md, _ideas/{AGENTS.md, <M.m.p>/SPEC.md},
              _archive/{releases_histo.jsonl, <M.m.p>/**},
              <M.m.p>/{RELEASE.json, SPEC.md, PLAN.md, TASKS.md,
                       verdicts/<40hex>.handoff.json}}
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

import re
from collections.abc import Iterable

__all__ = [
    "CANON_ROOT_MEMBERS",
    "canon_violations",
    "is_canon_path",
    "verdict_violations",
]

#: The v6 canon ROOT member names — every entry permitted directly under ``specs/``.
#: The doctor's TREE-8 root-membership tier is the one consumer (its former inline
#: ``_TREE8_CANON_ROOT`` copy); the nested canon shape is expressed entirely by
#: :data:`_CANON_FILE_PATTERNS`/:func:`is_canon_path` below — one source, not two.
CANON_ROOT_MEMBERS: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "constitution.md",
        "memory",
        "releases",
        "backlog",
        "bugs",
        "audits",
        "ADRs",
    }
)

_SEMVER = r"\d+\.\d+\.\d+"
_SHA40 = r"[0-9a-f]{40}"
_YYYYMMDD_SLUG = r"\d{8}-[a-z0-9][a-z0-9-]*"
_AREA = r"[a-z][a-z0-9_-]*"
_SLUG = r"[a-z][a-z0-9_-]*"

#: Every canon-conformant FILE path, POSIX-relative to ``specs/``. A directory is never
#: matched on its own — it is implied by whichever file pattern below places content
#: inside it (the same shape a git tree listing already has: no directory-only entries).
_CANON_FILE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        # -- root --------------------------------------------------------------------
        r"^AGENTS\.md$",
        r"^constitution\.md$",
        # -- memory/ -------------------------------------------------------------------
        r"^memory/AGENTS\.md$",
        r"^memory/ARCHITECTURE\.md$",
        r"^memory/QUALITY\.md$",
        r"^memory/TECHSTACK\.md$",
        r"^memory/product/index\.md$",
        r"^memory/product/catalog\.json$",
        rf"^memory/product/{_AREA}/{_SLUG}\.md$",
        # -- releases/ -----------------------------------------------------------------
        r"^releases/AGENTS\.md$",
        r"^releases/_ideas/AGENTS\.md$",
        rf"^releases/_ideas/{_SEMVER}/SPEC\.md$",
        r"^releases/_archive/releases_histo\.jsonl$",
        rf"^releases/_archive/{_SEMVER}/.+$",
        rf"^releases/{_SEMVER}/RELEASE\.json$",
        rf"^releases/{_SEMVER}/SPEC\.md$",
        rf"^releases/{_SEMVER}/PLAN\.md$",
        rf"^releases/{_SEMVER}/TASKS\.md$",
        rf"^releases/{_SEMVER}/verdicts/{_SHA40}\.handoff\.json$",
        # -- backlog/ ------------------------------------------------------------------
        r"^backlog/AGENTS\.md$",
        r"^backlog/BACKLOG\.json$",
        r"^backlog/_archive/backlog_histo\.jsonl$",
        r"^backlog/_archive/consumed_backlog_histo\.jsonl$",
        # -- bugs/ ---------------------------------------------------------------------
        r"^bugs/AGENTS\.md$",
        r"^bugs/BUGS\.jsonl$",
        r"^bugs/_archive/bugs_histo\.jsonl$",
        # -- audits/ -------------------------------------------------------------------
        r"^audits/AGENTS\.md$",
        r"^audits/_archive/audits_histo\.jsonl$",
        rf"^audits/{_YYYYMMDD_SLUG}/AUDIT\.md$",
        rf"^audits/{_YYYYMMDD_SLUG}/FINDINGS\.jsonl$",
        # -- ADRs/ ---------------------------------------------------------------------
        r"^ADRs/AGENTS\.md$",
        r"^ADRs/decisions\.jsonl$",
        r"^ADRs/_superseded/superseded\.jsonl$",
    )
)

#: The verdict-filename shape, isolated (matches the trailing component
#: ``releases/<M.m.p>/verdicts/<40hex>.handoff.json`` already admitted by
#: ``_CANON_FILE_PATTERNS`` above), used by :func:`verdict_violations` to pick the sha
#: out of an otherwise-canon-conformant verdict path.
_VERDICT_RE = re.compile(rf"^releases/{_SEMVER}/verdicts/({_SHA40})\.handoff\.json$")


def is_canon_path(rel_posix: str) -> bool:
    """True iff *rel_posix* (POSIX-relative to ``specs/``) is a v6-canon-conformant
    file path — structural shape only, never sha-specific (see :func:`verdict_violations`
    for the verdict business rule layered on top of the same path shape)."""
    return any(pattern.match(rel_posix) for pattern in _CANON_FILE_PATTERNS)


def canon_violations(paths: Iterable[str]) -> list[str]:
    """Every path in *paths* that is NOT canon-conformant, order-preserving.

    *paths* are POSIX-relative to ``specs/`` — a filesystem walk's ``Path.relative_to(
    specs_dir).as_posix()`` or a git tree listing's own native paths, identically.
    """
    return [path for path in paths if not is_canon_path(path)]


def verdict_violations(
    paths: Iterable[str], head_sha: str, parent_sha: str | None
) -> list[str]:
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
