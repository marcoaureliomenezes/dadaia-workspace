"""Workspace filesystem-layout constants — the single authority (pure ``core`` leaf).

Bug class (transversal; the six-bug ``.dadaia/`` layout ledger): the
same invariant declared in multiple modules diverges. The root whitelist lived in
``hooks/root_whitelist.py`` AND ``features/spec_context/doctor.py`` and diverged the day
``DADAIA.md`` was added to one of them; the ``.dadaia/`` layout lived as bare name lists
in four modules, and six fixes edited their membership without ever changing their shape.
One fact, one place: every consumer DERIVES from this module (both ``hooks`` and
``features`` may import ``core``; the reverse edges are forbidden by import-linter), and a
``.dadaia/`` zone enters only as a :class:`Zone` record — a name without a class, a
creator and a TTL cannot be added.

Same regime as :mod:`dadaia_workspace.core.harness_registry`: stdlib-only, no I/O, no
internal imports — a pure constants leaf, pinned by contract tests
(``tests/contract/test_zone_registry.py``: the rendered table equals the registry, no
second name list exists anywhere in the package, every creator is a live module).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.specs_version import RELEASE_ID_FRAGMENT

__all__ = [
    "AUDIT_DIR_NAME_PATTERN",
    "AUDIT_DIR_NAME_RE",
    "CANON_ROOT_MEMBERS",
    "DADAIA_MD_HARNESS_TARGETS",
    "DADAIA_ROOT_FILES",
    "DADAIA_ZONES",
    "HARNESS_DIRS",
    "INSTANCE_EXCEPTIONS",
    "LAW_BASENAMES",
    "LAW_HARNESS_DIRS",
    "MEMORY_TOPLEVEL_FILES",
    "REPO_TREE_ARTIFACTS",
    "INSTALLED_GIT_HOOKS",
    "REPO_TREE_EXCLUDED",
    "REQUIRED_ROOT_DIRS",
    "ROOT_ALLOWED_DIRS",
    "ROOT_ALLOWED_FILES",
    "SCOPED_LAW_AREAS",
    "SHAPE_FRAGMENTS",
    "SPECS_CANON",
    "STATES_CANON",
    "CanonEntry",
    "Creator",
    "SpecsArea",
    "Zone",
    "ZoneClass",
    "additive_prefixes",
    "parse_exception_globs",
    "public_scripts_dir",
    "repo_excluded_display",
    "root_entries_display",
    "specs_canon_table_rows",
    "walked_zones",
    "zone_names",
    "zone_table_rows",
    "zones_created_by",
    "zones_with_canon",
    "zones_with_ttl",
]

#: SPEC-DOC-030 (DADAIA.md §6.8, v6 canon): every new ``specs/audits/`` directory must
#: be named ``<YYYYMMDD>-<slug>`` — the SAME shape ``features.specs.canon``'s own
#: audits ``CanonEntry`` pattern uses (bug
#: spec-doc-030-audit-dir-rule-contradicts-dadaia-6-8-canon: this constant used to
#: state an older, stale ``<YYYYMMDDTHHMMSSZ>-<session_id_8chars>`` shape that
#: contradicted the law). One fact, one place: ``core`` may not import ``features``, so
#: the fragment lives here and ``canon.py`` imports it — never a second, independently
#: hand-kept regex.
AUDIT_DIR_NAME_PATTERN: str = r"\d{8}-[a-z0-9][a-z0-9-]*"
AUDIT_DIR_NAME_RE: re.Pattern[str] = re.compile(f"^{AUDIT_DIR_NAME_PATTERN}$")

#: Directories the workspace root may contain (the Workspace Root Law).
ROOT_ALLOWED_DIRS: frozenset[str] = frozenset(
    {".agents", ".claude", ".codex", ".dadaia", ".git", ".kimi-code", "repos"}
)

#: Files the workspace root may contain. ``DADAIA.md`` is the workspace system prompt
#: (the single always-on law file); ``AGENTS.md`` its harness-discovery bridge;
#: ``CLAUDE.md`` the Claude Code import bridge; ``prompt.md`` the optional operator
#: long-prompt file; ``.env`` the one credential home (DADAIA.md §9); ``.gitignore`` the
#: defence-in-depth exclusion list (§5.3) — bug
#: doctor-root1-flags-env-that-dadaia-md-9-declares-canonical: the law named both, this
#: set named neither, and hook + doctor (both derived from here) contradicted the law.
ROOT_ALLOWED_FILES: frozenset[str] = frozenset(
    {"AGENTS.md", "CLAUDE.md", "DADAIA.md", "prompt.md", ".env", ".gitignore"}
)


class ZoneClass(StrEnum):
    """What a zone is for — the doctor's walk and the gate's ADDITIVE class derive from it."""

    PROJECTION = "projection"
    STATE = "state"
    PROTECTED = "protected"
    OPERATOR = "operator"
    OUTPUT = "output"
    EPHEMERAL = "ephemeral"
    MANAGED = "managed"


class Creator(StrEnum):
    """Who brings a zone into existence — the row's owner, tied to a live module by ratchet."""

    INIT = "init"
    INSTALL = "install"
    RUNTIME = "runtime"
    OPERATOR = "operator"


@dataclass(frozen=True)
class Zone:
    """One top-level ``.dadaia/`` directory."""

    name: str
    cls: ZoneClass
    creator: Creator
    #: Seconds a file may age by mtime before the doctor expires it; ``None`` = never.
    ttl_seconds: int | None
    #: Closed canon of entry-name globs; ``None`` = open, anything may live inside.
    canon: frozenset[str] | None
    #: One line, rendered into the projected ``.dadaia/AGENTS.md`` table.
    purpose: str


#: The closed canon of ``.dadaia/states/`` — anything else is slop.
STATES_CANON: frozenset[str] = frozenset(
    {
        "spec_contexts.json",
        "server_registry.json",
        "install_ledger.json",
        "agent_model_policy.json",
        "agent_model_policy.json.last-good.json",
        "privacy_denylist.json",
        "instance_exceptions.txt",
        "backlog_subject_aliases.txt",
        "harness_profile.json",
        "presence",
        "AGENTS.md",
    }
)

_ONE_DAY = 86_400

#: The reaper's hold window: a moved entry is deleted only after this elapses (Q3).
_SEVEN_DAYS: int = 7 * _ONE_DAY

#: The one record of what may live in ``.dadaia/``. Row order is the
#: rendered table order; every other list of zone names in the package is a view of this.
DADAIA_ZONES: tuple[Zone, ...] = (
    Zone(
        "agentic",
        ZoneClass.PROJECTION,
        Creator.INSTALL,
        None,
        None,
        "staged public assets + manifest.json",
    ),
    Zone("hooks", ZoneClass.PROJECTION, Creator.INSTALL, None, None, "projected hook entrypoints"),
    Zone("states", ZoneClass.STATE, Creator.INIT, None, STATES_CANON, "workspace database"),
    Zone(
        "sessions",
        ZoneClass.PROTECTED,
        Creator.RUNTIME,
        None,
        frozenset({"*.json"}),
        "session records; reaper = core.session_store",
    ),
    Zone(
        "handoff",
        ZoneClass.OUTPUT,
        Creator.RUNTIME,
        _ONE_DAY,
        None,
        "agent handoffs, ack-on-consume",
    ),
    Zone("tmp", ZoneClass.EPHEMERAL, Creator.RUNTIME, _ONE_DAY, None, "scratch + evidence"),
    Zone(
        "reaped",
        ZoneClass.EPHEMERAL,
        Creator.RUNTIME,
        _SEVEN_DAYS,
        None,
        "slop held by the reaper; deleted only by TTL expiry",
    ),
    Zone("mcps", ZoneClass.EPHEMERAL, Creator.RUNTIME, _ONE_DAY, None, "MCP working dirs"),
    Zone(
        ".cache",
        ZoneClass.EPHEMERAL,
        Creator.RUNTIME,
        _ONE_DAY,
        None,
        "redirected tool caches (DADAIA.md 5.3)",
    ),
    Zone(
        "dist",
        ZoneClass.STATE,
        Creator.RUNTIME,
        None,
        frozenset({"spec-contexts.json"}),
        "the one export artifact",
    ),
    Zone(
        "references",
        ZoneClass.OPERATOR,
        Creator.OPERATOR,
        None,
        None,
        "operator reference clones; never scanned",
    ),
    Zone(".venv", ZoneClass.MANAGED, Creator.INIT, None, None, "workspace venv; never scanned"),
)

#: Files (not zones) the ``.dadaia/`` top level may contain.
DADAIA_ROOT_FILES: frozenset[str] = frozenset({"AGENTS.md", ".gitignore"})

#: Workspace-relative path of the operator's exception globs: matches
#: at the root and inside the harness dirs; outside the manifest and outside these = slop.
INSTANCE_EXCEPTIONS: str = ".dadaia/states/instance_exceptions.txt"


def parse_exception_globs(text: str) -> tuple[str, ...]:
    """One glob per line; ``#`` lines and blanks dropped; a directory glob's trailing ``/``
    dropped (``fnmatch`` never matches it); deduplicated, first kept, order kept."""
    lines = (line.strip().rstrip("/") for line in text.splitlines())
    return tuple(dict.fromkeys(line for line in lines if line and not line.startswith("#")))


# Derived views — one per consumer, all pure; a consumer never spells the names itself.


def zone_names() -> frozenset[str]:
    """The doctor's allow set for the ``.dadaia/`` top level."""
    return frozenset(zone.name for zone in DADAIA_ZONES)


def zones_created_by(creator: Creator) -> tuple[Zone, ...]:
    """What ``init``/``install`` must create and the doctor reports ``missing`` for."""
    return tuple(zone for zone in DADAIA_ZONES if zone.creator is creator)


def zones_with_ttl() -> tuple[Zone, ...]:
    """The zones the doctor expires by mtime (``--fix --expired-only``'s whole scope)."""
    return tuple(zone for zone in DADAIA_ZONES if zone.ttl_seconds is not None)


def zones_with_canon() -> tuple[Zone, ...]:
    """The closed-canon zones: an entry outside ``canon`` is slop."""
    return tuple(zone for zone in DADAIA_ZONES if zone.canon is not None)


def walked_zones() -> tuple[Zone, ...]:
    """The zones the doctor scans — OPERATOR and MANAGED zones are never walked."""
    return tuple(
        zone for zone in DADAIA_ZONES if zone.cls not in (ZoneClass.OPERATOR, ZoneClass.MANAGED)
    )


def additive_prefixes() -> tuple[str, ...]:
    """The gate's ``.dadaia/`` ADDITIVE prefixes: the OUTPUT + EPHEMERAL zones."""
    return tuple(
        f".dadaia/{zone.name}/"
        for zone in DADAIA_ZONES
        if zone.cls in (ZoneClass.OUTPUT, ZoneClass.EPHEMERAL)
    )


def zone_table_rows() -> tuple[tuple[str, str, str, str, str], ...]:
    """``(name, purpose, class, ttl-or-never, creator)`` per row, for the rendered table."""
    return tuple(
        (
            zone.name,
            zone.purpose,
            zone.cls.value,
            "never" if zone.ttl_seconds is None else str(zone.ttl_seconds),
            zone.creator.value,
        )
        for zone in DADAIA_ZONES
    )


#: The git chokepoints (DADAIA.md 3.4) and the shipped script each is installed FROM:
#: ``(.git/hooks/<target>, public/scripts/<source>)``. One home for "which hooks exist
#: and what they are made of" — ``cli.commands.ci`` installs them, the workspace doctor
#: compares the installed copies to them (HOOKS-DRIFT-1).
INSTALLED_GIT_HOOKS: tuple[tuple[str, str], ...] = (
    ("pre-commit", "pre-commit-presence-gate.sh"),
    ("pre-push", "pre-push-ci-gate.sh"),
)


def public_scripts_dir() -> Path:
    """The shipped ``public/scripts/`` directory inside the installed package.

    Pure path arithmetic on this module's own location — no filesystem read, so the
    core-purity ratchet is untouched.
    """
    return Path(__file__).resolve().parents[1] / "public" / "scripts"


#: Basenames of the projected LAW files — human-only in an instantiated workspace.
LAW_BASENAMES: frozenset[str] = frozenset({"DADAIA.md", "AGENTS.md", "CLAUDE.md"})

#: Harness/projection directories that host a projected law file (relative to the
#: workspace root). The gate composes its guarded set FROM this; the installer projects
#: ``DADAIA.md`` into the subset in :data:`DADAIA_MD_HARNESS_TARGETS`.
LAW_HARNESS_DIRS: frozenset[str] = frozenset({".claude/rules", ".codex", ".kimi-code", ".agents"})

#: The harness directories themselves (the top segment of each of the above) — the one
#: home of "which root directories a harness owns", derived, never respelled.
HARNESS_DIRS: frozenset[str] = frozenset(path.split("/")[0] for path in LAW_HARNESS_DIRS)

#: Where the law is projected per harness whose root-import chain does not already
#: deliver it — Claude Code's does, so no entry here (bug FR31, see workspace-law rule).
DADAIA_MD_HARNESS_TARGETS: dict[str, str] = {
    "codex": ".codex/DADAIA.md",
    "kimi-code": ".kimi-code/DADAIA.md",
}

# ---------------------------------------------------------------------------------
# The repo working tree (DADAIA.md §5.3) and the ``specs/`` canon (§6.2) — the same
# registry regime as the root law and the zone table above. 0.4.7 FR5: these names
# lived in three homes (the law's hand-typed bullets, ``features/specs/canon.py``'s
# rows, ``infrastructure/privacy_check.py``'s literal) and the ledger counted seven
# bugs born of one home drifting from another.
# ---------------------------------------------------------------------------------

#: Tool artifacts a repo working tree may carry but that are never source: caches,
#: build output, coverage data. Bare names — the display form (trailing ``/`` for the
#: directories) is :func:`repo_excluded_display`.
REPO_TREE_ARTIFACTS: tuple[str, ...] = (
    # ``.venv`` is here for the RENDERED law line only (DADAIA.md §5.3 lists `.venv/`
    # and the rendering reads this tuple). It can never produce a finding: the repo-tree
    # walk consults ``_REPO_WALK_PRUNED`` first, which ends the walk at ``.venv``.
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".hypothesis",
    ".ruff_cache",
    "test-results",
    "playwright-report",
    "coverage",
    ".coverage",
)

#: Everything a repo working tree must NOT carry (DADAIA.md §5.3): the tool artifacts
#: above plus ``.dadaia`` — a nested workspace control directory, excluded for its own
#: reason (it corrupts context resolution for every tree-walking tool), which is why a
#: consumer walking artifacts only (the public-asset walk, which lives UNDER
#: ``.dadaia/``) reads :data:`REPO_TREE_ARTIFACTS` instead.
REPO_TREE_EXCLUDED: tuple[str, ...] = (".dadaia", *REPO_TREE_ARTIFACTS)

#: The one entry of :data:`REPO_TREE_ARTIFACTS` that is a file, not a directory — the
#: only fact the rendered law line needs beyond the names themselves.
_REPO_TREE_EXCLUDED_FILES: frozenset[str] = frozenset({".coverage"})

#: Top-level ``specs/memory/`` files (v6 canon). Named here, with every other canonical
#: name; ``features.specs.memory_canon`` re-exports it for its own consumers.
MEMORY_TOPLEVEL_FILES: tuple[str, ...] = ("ARCHITECTURE.md", "TECHSTACK.md", "QUALITY.md")

#: The root member a :class:`CanonEntry` lives under. Distinct from a filesystem "area"
#: only for the two bare root files (``AGENTS.md``, ``constitution.md``), each its own
#: singleton member — every other value names the directory area it governs. Deriving
#: :data:`CANON_ROOT_MEMBERS` as ``{e.area for e in SPECS_CANON}`` then needs zero
#: special casing — the whole reason this carries 8 values, not 6.
SpecsArea = Literal[
    "AGENTS.md", "constitution.md", "memory", "releases", "backlog", "bugs", "audits", "ADRs"
]

#: The variable segments a canon path shape may carry: the law's own notation on the
#: left, the regex fragment it compiles to on the right. A shape is written ONCE, in
#: the law's notation; :attr:`CanonEntry.pattern` derives the matcher and
#: :func:`specs_canon_table_rows` derives the rendered table from the same string —
#: never a hand-kept regex beside a hand-kept prose spelling of the same path.
_SHAPE_TOKENS: tuple[tuple[str, str], ...] = (
    ("<M.m.p>", RELEASE_ID_FRAGMENT),
    ("<40hex>", r"[0-9a-f]{40}"),
    ("<YYYYMMDD-slug>", AUDIT_DIR_NAME_PATTERN),
    ("<area>", r"[a-z][a-z0-9_-]*"),
    ("<slug>", r"[a-z][a-z0-9_-]*"),
    ("rc-N", r"rc-\d+"),
    ("**", r".+"),
)

#: The shape tokens as a lookup — a consumer needing one fragment (the verdict-sha
#: capture in ``features.specs.canon``) reads it here instead of respelling it.
SHAPE_FRAGMENTS: dict[str, str] = dict(_SHAPE_TOKENS)

_SHAPE_TOKEN_RE = re.compile("|".join(f"({re.escape(token)})" for token, _ in _SHAPE_TOKENS))


def _shape_regex(shape: str) -> str:
    """*shape* with every token replaced by its fragment and every literal part escaped."""
    fragments = dict(_SHAPE_TOKENS)
    return "".join(
        fragments[part] if part in fragments else re.escape(part)
        for part in _SHAPE_TOKEN_RE.split(shape)
        if part
    )


@dataclass(frozen=True)
class CanonEntry:
    """One row of the ``specs/`` canon: a path SHAPE, its root member, and whether a
    fresh tree must carry it at birth.

    :attr:`shape` is the law's notation (``releases/<M.m.p>/SPEC.md``). A shape with no
    variable token IS a concrete ``specs/``-relative destination (:attr:`dest`); a shape
    with one is matched, never scaffolded at birth. Rendering — which template produces
    the content — is the SCAFFOLDER's concern and lives in ``features.specs.canon``,
    keyed by :attr:`shape`: ``core`` holds the names, never the file contents.
    """

    shape: str
    area: SpecsArea
    required_at_birth: bool = False

    @property
    def dest(self) -> str | None:
        """The concrete ``specs/``-relative path, or ``None`` for a variable shape."""
        return None if _SHAPE_TOKEN_RE.search(self.shape) else self.shape

    @cached_property
    def pattern(self) -> re.Pattern[str]:
        """The anchored matcher derived from :attr:`shape` — never hand-written."""
        return re.compile(f"^{_shape_regex(self.shape)}$")


#: THE CANON TABLE — one row per canon-conformant path shape, in rendered-table order
#: (root, memory, releases, backlog, bugs, audits, ADRs; required-at-birth first within
#: an area).
SPECS_CANON: tuple[CanonEntry, ...] = (
    CanonEntry("AGENTS.md", "AGENTS.md", True),
    CanonEntry("constitution.md", "constitution.md", True),
    CanonEntry("memory/AGENTS.md", "memory", True),
    *(CanonEntry(f"memory/{name}", "memory", True) for name in MEMORY_TOPLEVEL_FILES),
    CanonEntry("memory/product/index.md", "memory", True),
    CanonEntry("memory/product/catalog.json", "memory", True),
    CanonEntry("memory/product/<area>/<slug>.md", "memory"),
    CanonEntry("releases/AGENTS.md", "releases", True),
    CanonEntry("releases/_ideas/AGENTS.md", "releases", True),
    CanonEntry("releases/_archive/releases_histo.jsonl", "releases", True),
    CanonEntry("releases/_ideas/<M.m.p>/SPEC.md", "releases"),
    CanonEntry("releases/_archive/<M.m.p>/**", "releases"),
    CanonEntry("releases/<M.m.p>/_RELEASE.json", "releases"),
    # Legacy state-file name (pre-0.4.6) — admitted ONLY as the rename-lane input:
    # SPEC-DOC-046 offers the doctor-fixable rename to _RELEASE.json (ADR 0007).
    CanonEntry("releases/<M.m.p>/RELEASE.json", "releases"),
    CanonEntry("releases/<M.m.p>/SPEC.md", "releases"),
    CanonEntry("releases/<M.m.p>/PLAN.md", "releases"),
    CanonEntry("releases/<M.m.p>/TASKS.md", "releases"),
    CanonEntry("releases/<M.m.p>/verdicts/<40hex>.handoff.json", "releases"),
    # An archived candidate's trio (ADR 0006): rc-N is ONLY an archive, opened on
    # demand by ``dadaia release rc-archive``, never required at birth.
    CanonEntry("releases/<M.m.p>/rc-N/SPEC.md", "releases"),
    CanonEntry("releases/<M.m.p>/rc-N/PLAN.md", "releases"),
    CanonEntry("releases/<M.m.p>/rc-N/TASKS.md", "releases"),
    CanonEntry("backlog/AGENTS.md", "backlog", True),
    CanonEntry("backlog/BACKLOG.json", "backlog", True),
    CanonEntry("backlog/_archive/backlog_histo.jsonl", "backlog", True),
    CanonEntry("bugs/AGENTS.md", "bugs", True),
    CanonEntry("bugs/BUGS.jsonl", "bugs"),
    CanonEntry("bugs/_archive/bugs_histo.jsonl", "bugs", True),
    CanonEntry("audits/AGENTS.md", "audits", True),
    CanonEntry("audits/_archive/audits_histo.jsonl", "audits", True),
    CanonEntry("audits/<YYYYMMDD-slug>/AUDIT.md", "audits"),
    CanonEntry("audits/<YYYYMMDD-slug>/FINDINGS.jsonl", "audits"),
    CanonEntry("ADRs/AGENTS.md", "ADRs", True),
    CanonEntry("ADRs/decisions.jsonl", "ADRs", True),
)

#: The v6 canon ROOT member names — every entry permitted directly under ``specs/``.
#: Derived from :data:`SPECS_CANON` itself (zero special-casing: :data:`SpecsArea`
#: already carries one value per root member, including the two bare root files).
CANON_ROOT_MEMBERS: frozenset[str] = frozenset(entry.area for entry in SPECS_CANON)

#: TREE-4's required directories, derived (not hand-kept): every area that pre-creates
#: its own ``_archive/<area>_histo.jsonl`` at birth also needs its directory to exist —
#: exactly {audits, backlog, bugs, releases} today, self-updating if a future area gains
#: a birth-time histo entry.
REQUIRED_ROOT_DIRS: tuple[str, ...] = tuple(
    sorted(
        {
            entry.area
            for entry in SPECS_CANON
            if entry.required_at_birth
            and entry.dest
            and entry.dest.startswith(f"{entry.area}/_archive/")
        }
    )
)

#: The areas whose scaffolded ``AGENTS.md`` a projection freezes (the doctor's TREE-5
#: scoped-law coverage), derived from the rows that declare one.
SCOPED_LAW_AREAS: tuple[str, ...] = tuple(
    entry.dest.removesuffix("/AGENTS.md")
    for entry in SPECS_CANON
    if entry.dest and entry.dest.endswith("/AGENTS.md")
)


# Derived views — the rendered law tables (DADAIA.md §5.1, §5.3, §6.2).


def root_entries_display() -> str:
    """§5.1's one line: every root directory (trailing ``/``) then every root file."""
    return " ".join(
        [*(f"{name}/" for name in sorted(ROOT_ALLOWED_DIRS)), *sorted(ROOT_ALLOWED_FILES)]
    )


def repo_excluded_display() -> str:
    """§5.3's one line: the excluded names in registry order, directories slashed."""
    return " ".join(
        name if name in _REPO_TREE_EXCLUDED_FILES else f"{name}/" for name in REPO_TREE_ARTIFACTS
    )


def specs_canon_table_rows() -> tuple[tuple[str, str], ...]:
    """``(parent, members)`` per rendered §6.2 row: one row per directory that holds two
    or more canon members (``""`` = the ``specs/`` root), members in table order.

    A directory holding exactly one member is path-compressed into its parent's cell
    (``verdicts/<40hex>.handoff.json``) instead of earning a row of its own — nothing is
    elided and nothing is spelled twice: the rows ARE :data:`SPECS_CANON` read one path
    segment at a time.
    """
    children: dict[str, list[str]] = {}
    for entry in SPECS_CANON:
        segments = entry.shape.split("/")
        for depth, segment in enumerate(segments):
            bucket = children.setdefault("/".join(segments[:depth]), [])
            if segment not in bucket:
                bucket.append(segment)

    def compress(node: str) -> tuple[str, str | None]:
        """The cell text for the member at *node*, and the row it opens (or ``None``)."""
        parts = [node.rsplit("/", 1)[-1]]
        while len(children.get(node, ())) == 1:
            node = f"{node}/{children[node][0]}"
            parts.append(node.rsplit("/", 1)[-1])
        return (
            "/".join(parts) + ("/" if node in children else ""),
            node if node in children else None,
        )

    rows: list[tuple[str, str]] = []

    def emit(parent: str) -> None:
        cells: list[str] = []
        opened: list[str] = []
        for segment in children[parent]:
            cell, row = compress(f"{parent}/{segment}" if parent else segment)
            cells.append(cell)
            if row is not None:
                opened.append(row)
        rows.append((parent, " ".join(cells)))
        for row in opened:
            emit(row)

    emit("")
    return tuple(rows)
