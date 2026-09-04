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

__all__ = [
    "AUDIT_DIR_NAME_PATTERN",
    "AUDIT_DIR_NAME_RE",
    "DADAIA_ADDITIVE_PREFIXES",
    "DADAIA_ALLOWED_SUBDIRS",
    "DADAIA_MD_HARNESS_TARGETS",
    "DADAIA_ROOT_FILES",
    "DADAIA_ZONES",
    "INSTANCE_EXCEPTIONS",
    "LAW_BASENAMES",
    "LAW_HARNESS_DIRS",
    "ROOT_ALLOWED_DIRS",
    "ROOT_ALLOWED_FILES",
    "STATES_CANON",
    "Creator",
    "Zone",
    "ZoneClass",
    "additive_prefixes",
    "parse_exception_globs",
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
    {".agents", ".claude", ".codex", ".dadaia", ".kimi-code", "repos"}
)

#: Files the workspace root may contain. ``DADAIA.md`` is the workspace system prompt
#: (the single always-on law file); ``AGENTS.md`` its harness-discovery bridge;
#: ``CLAUDE.md`` the Claude Code import bridge; ``prompt.md`` the optional operator
#: long-prompt file.
ROOT_ALLOWED_FILES: frozenset[str] = frozenset({"AGENTS.md", "CLAUDE.md", "DADAIA.md", "prompt.md"})


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
    """One glob per line; ``#`` lines and blanks dropped; deduplicated, first kept, order kept."""
    lines = (line.strip() for line in text.splitlines())
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


#: Compatibility views, one line each, deleted with their last readers (the doctor's
#: top-level allow set, ``legacy_dadaia_dirs``, the public doctor's foreign scan).
DADAIA_ALLOWED_SUBDIRS: frozenset[str] = zone_names()
DADAIA_ADDITIVE_PREFIXES: tuple[str, ...] = additive_prefixes()

#: Basenames of the projected LAW files — human-only in an instantiated workspace.
LAW_BASENAMES: frozenset[str] = frozenset({"DADAIA.md", "AGENTS.md", "CLAUDE.md"})

#: Harness/projection directories that host a projected law file (relative to the
#: workspace root). The gate composes its guarded set FROM this; the installer projects
#: ``DADAIA.md`` into the subset in :data:`DADAIA_MD_HARNESS_TARGETS`.
LAW_HARNESS_DIRS: frozenset[str] = frozenset({".claude/rules", ".codex", ".kimi-code", ".agents"})

#: Where the law is projected per harness whose root-import chain does not already
#: deliver it — Claude Code's does, so no entry here (bug FR31, see workspace-law rule).
DADAIA_MD_HARNESS_TARGETS: dict[str, str] = {
    "codex": ".codex/DADAIA.md",
    "kimi-code": ".kimi-code/DADAIA.md",
}
