"""Workspace filesystem-layout constants: the one home of every root, ``.dadaia/`` zone and
``specs/`` canon name. ``core`` leaf — stdlib only; its one read is the operator's
``.dadaiaignore`` (:func:`operator_globs`); every consumer derives from it.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.harness_registry import HARNESS_PROJECTION_DIRS
from dadaia_workspace.core.release_state import RELEASE_ID_RE

__all__ = [
    "render_registry_tables",
    "AUDIT_DIR_NAME_PATTERN",
    "AUDIT_DIR_NAME_RE",
    "CANON_ROOT_MEMBERS",
    "DADAIA_ROOT_FILES",
    "DADAIA_ZONES",
    "HARNESS_DIRS",
    "DADAIAIGNORE",
    "MEMORY_TOPLEVEL_FILES",
    "REPO_LAW",
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
    "dadaiaignore_seed",
    "operator_globs",
    "parse_dadaiaignore",
    "public_scripts_dir",
    "repo_excluded_display",
    "root_entries_display",
    "specs_canon_table_rows",
    "walked_zones",
    "zone_names",
    "zone_table_rows",
    "provisioned_zones",
    "zones_with_canon",
    "zones_with_ttl",
]

#: The main repo's scoped law, beside ``specs/``: ``templates/<name>`` -> ``<repo>/<dest>``.
REPO_LAW: tuple[tuple[str, str], ...] = (
    ("repo-AGENTS.md", "AGENTS.md"),
    ("tests-AGENTS.md", "tests/AGENTS.md"),
)

#: Every ``specs/audits/`` directory is named ``<YYYYMMDD>-<slug>``.
AUDIT_DIR_NAME_PATTERN: str = r"\d{8}-[a-z0-9][a-z0-9-]*"
AUDIT_DIR_NAME_RE: re.Pattern[str] = re.compile(f"^{AUDIT_DIR_NAME_PATTERN}$")


#: The operator's file of legitimate workspace paths, at the root (ADRs 0092, 0145).
DADAIAIGNORE: str = ".dadaiaignore"

#: Files the workspace root may contain: the root map, the operator prompt, the git ignore,
#: the operator's own globs — credentials live outside the workspace (ADR 0146).
ROOT_ALLOWED_FILES: frozenset[str] = frozenset(
    {"AGENTS.md", "prompt.md", ".gitignore", DADAIAIGNORE}
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
        "backlog_subject_aliases.txt",
        "harness_profile.json",
        "AGENTS.md",
    }
)

_ONE_DAY = 86_400
_SEVEN_DAYS: int = 7 * _ONE_DAY  # the reaper's hold window

#: The one record of what may live in ``.dadaia/``, in rendered-table order.
DADAIA_ZONES: tuple[Zone, ...] = (
    Zone("agentic", ZoneClass.PROJECTION, Creator.INSTALL, None, None, "staged public assets + manifest.json"),
    Zone("hooks", ZoneClass.PROJECTION, Creator.INSTALL, None, None, "projected hook entrypoints"),
    Zone("states", ZoneClass.STATE, Creator.INIT, None, STATES_CANON, "workspace database"),
    Zone("sessions", ZoneClass.PROTECTED, Creator.RUNTIME, None, frozenset({"*.json"}), "session records; reaper = core.session_store"),
    Zone("handoff", ZoneClass.OUTPUT, Creator.RUNTIME, _ONE_DAY, None, "agent handoffs, ack-on-consume"),
    Zone("tmp", ZoneClass.EPHEMERAL, Creator.RUNTIME, _ONE_DAY, None, "scratch + evidence"),
    Zone("reaped", ZoneClass.EPHEMERAL, Creator.RUNTIME, _SEVEN_DAYS, None, "slop held by the reaper; deleted only by TTL expiry"),
    Zone("mcps", ZoneClass.EPHEMERAL, Creator.RUNTIME, _ONE_DAY, None, "MCP working dirs"),
    Zone("dist", ZoneClass.STATE, Creator.RUNTIME, None, frozenset({"spec-contexts.json"}), "the one export artifact"),
    Zone("references", ZoneClass.OPERATOR, Creator.OPERATOR, None, None, "operator reference clones; never scanned"),
    Zone(".venv", ZoneClass.MANAGED, Creator.INIT, None, None, "workspace venv; never scanned"),
)  # fmt: skip

#: Files (not zones) the ``.dadaia/`` top level may contain.
DADAIA_ROOT_FILES: frozenset[str] = frozenset({"AGENTS.md", ".gitignore"})

#: Absolute tool caches in tmp, exported by the harness env.
TOOL_CACHE_ENV: dict[str, str] = {"MYPY_CACHE_DIR": "mypy-cache", "RUFF_CACHE_DIR": "ruff-cache"}
MARKER_DIR: Path = Path(".dadaia") / "tmp" / "hooks"


def parse_dadaiaignore(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(patterns, invalid lines) of a ``.dadaiaignore`` (ADR 0093): one root-relative pattern
    per line, ``#`` comments, ``*`` within one segment, a trailing ``/`` for a directory
    (dropped); ``!``, ``**``, an absolute path or ``..`` is invalid. Deduplicated, order kept."""
    kept: dict[str, None] = {}
    invalid: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pattern = line.rstrip("/")
        if line.startswith(("!", "/")) or "**" in line or ".." in pattern.split("/"):
            invalid.append(line)
        else:
            kept[pattern] = None
    return tuple(kept), tuple(invalid)


def operator_globs(workspace: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The one reader of ``<workspace>/.dadaiaignore``, for the gate and the doctor; absent
    or unreadable is no pattern."""
    try:
        text = (workspace / DADAIAIGNORE).read_text(encoding="utf-8")
    except OSError:
        return (), ()
    return parse_dadaiaignore(text)


def dadaiaignore_seed(workspace: Path) -> str:
    """What a new ``.dadaiaignore`` starts with — ``init`` and ``doctor --fix`` alike: the
    legacy ``states/instance_exceptions.txt`` 1:1 (then held as slop), else the template."""
    try:
        return (workspace / ".dadaia" / "states" / "instance_exceptions.txt").read_text("utf-8")
    except OSError:
        return (
            "# Operator-only: one root-relative pattern per line, * within one segment, a\n"
            "# trailing / for a directory; no ! and no ** (ADR 0093).\n"
        )


def _matches(sub: str, pattern: str) -> bool:
    """*pattern* matches the root-relative *sub* segment by segment (``*`` never crosses ``/``)."""
    parts, globs = sub.split("/"), pattern.split("/")
    return len(parts) == len(globs) and all(map(fnmatch.fnmatch, parts, globs))


def verdict(rel: str, is_dir: bool, globs: tuple[str, ...]) -> Literal["canon", "operator", "slop"]:
    """The one answer to "may this entry exist", for the gate and the doctor: a judged level
    (root, ``.dadaia/<zone>``, a closed zone's entry) outside its allow set is ``operator`` iff
    an exception glob matches its name or path, else ``slop``; below an open level, ``canon``."""
    parts = rel.strip("/").split("/")
    for depth, name in enumerate(parts):
        directory = is_dir or depth < len(parts) - 1
        if depth == 0:
            allowed = ROOT_ALLOWED_DIRS if directory else ROOT_ALLOWED_FILES
        elif depth == 1 and parts[0] == ".dadaia":
            allowed = zone_names() if directory else DADAIA_ROOT_FILES
        elif depth == 2 and parts[0] == ".dadaia":
            zone = next((z for z in DADAIA_ZONES if z.name == parts[1]), None)
            if zone is None or zone.canon is None:
                return "canon"
            allowed = zone.canon
        else:
            return "canon"
        if any(fnmatch.fnmatch(name, a) for a in allowed):
            continue
        excepted = any(_matches("/".join(parts[: depth + 1]), g) for g in globs)
        return "operator" if excepted else "slop"
    return "canon"


def zone_names() -> frozenset[str]:
    """The doctor's allow set for the ``.dadaia/`` top level."""
    return frozenset(zone.name for zone in DADAIA_ZONES)


def provisioned_zones() -> tuple[Zone, ...]:
    """The zones ``init`` creates and the doctor reports ``missing`` — one predicate."""
    return tuple(zone for zone in walked_zones() if zone.creator in (Creator.INIT, Creator.INSTALL))


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


def tool_cache_env(workspace_root: Path) -> dict[str, str]:
    return {var: str(workspace_root / ".dadaia" / "tmp" / d) for var, d in TOOL_CACHE_ENV.items()}


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


#: The git chokepoints: ``(.git/hooks/<target>, public/scripts/<source>)``.
INSTALLED_GIT_HOOKS: tuple[tuple[str, str], ...] = (("pre-push", "pre-push-ci-gate.sh"),)


def public_scripts_dir() -> Path:
    """The shipped ``public/scripts/`` directory (path arithmetic, no filesystem read)."""
    return Path(__file__).resolve().parents[1] / "public" / "scripts"


#: Every projection directory at the workspace root: ``.agents`` plus each harness's own.
HARNESS_DIRS: frozenset[str] = frozenset(
    {".agents", *(d for dirs in HARNESS_PROJECTION_DIRS.values() for d in dirs)}
)

ROOT_ALLOWED_DIRS: frozenset[str] = frozenset(
    {".dadaia", ".git", "repos", "worktrees"} | HARNESS_DIRS
)

#: Tool artifacts a repo working tree may carry but that are never source.
REPO_TREE_ARTIFACTS: tuple[str, ...] = (
    ".venv",  # rendered law line only: the repo-tree walk prunes ``.venv`` first
    ".pytest_cache",
    ".mypy_cache",
    ".hypothesis",
    ".ruff_cache",
    "test-results",
    "playwright-report",
    "coverage",
    ".coverage",
)

#: Everything a repo working tree must NOT carry: the artifacts plus a nested ``.dadaia``.
REPO_TREE_EXCLUDED: tuple[str, ...] = (".dadaia", *REPO_TREE_ARTIFACTS)

_REPO_TREE_EXCLUDED_FILES: frozenset[str] = frozenset({".coverage"})

MEMORY_TOPLEVEL_FILES: tuple[str, ...] = ("ARCHITECTURE.md", "QUALITY.md")

#: The root member a :class:`CanonEntry` lives under (each bare root file is its own).
SpecsArea = Literal[
    "AGENTS.md", "constitution.md", "memory", "releases", "backlog", "bugs", "audits", "ADRs"
]

#: A canon shape's variable tokens (the law's notation) and the regex each compiles to.
_SHAPE_TOKENS: tuple[tuple[str, str], ...] = (
    ("<M.m.p>", RELEASE_ID_RE.pattern[1:-1]),
    ("<40hex>", r"[0-9a-f]{40}"),
    ("<YYYYMMDD-slug>", AUDIT_DIR_NAME_PATTERN),
    ("<area>", r"[a-z][a-z0-9_-]*"),
    ("<slug>", r"[a-z][a-z0-9_-]*"),
    ("**", r".+"),
)

SHAPE_FRAGMENTS: dict[str, str] = dict(_SHAPE_TOKENS)

_SHAPE_TOKEN_RE = re.compile("|".join(f"({re.escape(token)})" for token, _ in _SHAPE_TOKENS))


def _shape_regex(shape: str) -> str:
    parts = _SHAPE_TOKEN_RE.split(shape)
    return "".join(SHAPE_FRAGMENTS.get(part) or re.escape(part) for part in parts if part)


@dataclass(frozen=True)
class CanonEntry:
    """One ``specs/`` canon row: a path shape in the law's notation, its root member, and
    whether a fresh tree must carry it at birth."""

    shape: str
    area: SpecsArea
    required_at_birth: bool = False

    @property
    def dest(self) -> str | None:
        """The concrete ``specs/``-relative path, or ``None`` for a variable shape."""
        return None if _SHAPE_TOKEN_RE.search(self.shape) else self.shape

    @cached_property
    def pattern(self) -> re.Pattern[str]:
        return re.compile(f"^{_shape_regex(self.shape)}$")


#: The canon table, in rendered order (required-at-birth first within an area).
SPECS_CANON: tuple[CanonEntry, ...] = (
    CanonEntry("AGENTS.md", "AGENTS.md", True),
    CanonEntry("constitution.md", "constitution.md", True),
    CanonEntry("memory/AGENTS.md", "memory", True),
    *(CanonEntry(f"memory/{name}", "memory", True) for name in MEMORY_TOPLEVEL_FILES),
    CanonEntry("memory/product/index.md", "memory", True),
    CanonEntry("memory/product/catalog.json", "memory"),  # written by memory.py only
    CanonEntry("memory/product/<area>/<slug>.md", "memory"),
    CanonEntry("releases/AGENTS.md", "releases", True),
    CanonEntry("releases/_archive/releases_histo.jsonl", "releases", True),
    CanonEntry("releases/_archive/<M.m.p>/**", "releases"),
    CanonEntry("releases/<M.m.p>/_RELEASE.json", "releases"),
    CanonEntry("releases/<M.m.p>/SPEC.md", "releases"),
    CanonEntry("releases/<M.m.p>/PLAN.md", "releases"),
    CanonEntry("releases/<M.m.p>/TASKS.md", "releases"),
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

#: Every entry permitted directly under ``specs/``.
CANON_ROOT_MEMBERS: frozenset[str] = frozenset(entry.area for entry in SPECS_CANON)

#: TREE-4's required directories: every area whose ``_archive/`` histo is born with the tree.
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

#: The areas carrying a scaffolded ``AGENTS.md`` (TREE-5 scoped-law coverage).
SCOPED_LAW_AREAS: tuple[str, ...] = tuple(
    entry.dest.removesuffix("/AGENTS.md")
    for entry in SPECS_CANON
    if entry.dest and entry.dest.endswith("/AGENTS.md")
)


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
    """``(parent, members)`` per directory holding two or more canon members (``""`` = the
    root); a single-member directory is path-compressed into its parent's cell."""
    children: dict[str, list[str]] = {}
    for entry in SPECS_CANON:
        segments = entry.shape.split("/")
        for depth, segment in enumerate(segments):
            bucket = children.setdefault("/".join(segments[:depth]), [])
            if segment not in bucket:
                bucket.append(segment)

    def compress(node: str) -> tuple[str, str | None]:
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


def _zone_table() -> str:
    rows = ["| Zone | Purpose | Class | TTL | Creator |", "|---|---|---|---|---|"]
    rows += [
        f"| `{name}/` | {purpose} | {cls} | {ttl} | {creator} |"
        for name, purpose, cls, ttl, creator in zone_table_rows()
    ]
    return "\n".join(rows)


def _states_canon_table() -> str:
    return "\n".join(["| Entry |", "|---|", *(f"| `{entry}` |" for entry in sorted(STATES_CANON))])


def _specs_canon_table() -> str:
    rows = ["| Area | Members |", "|---|---|"]
    rows += [
        f"| {'root' if parent == '' else f'`{parent}/`'} | `{members}` |"
        for parent, members in specs_canon_table_rows()
    ]
    return "\n".join(rows)


#: Law-fragment placeholder -> the registry view that fills it.
_PLACEHOLDERS: dict[str, Callable[[], str]] = {
    "<!-- zones -->": _zone_table,
    "<!-- canon -->": _states_canon_table,
    "<!-- root -->": root_entries_display,
    "<!-- repo-excluded -->": repo_excluded_display,
    "<!-- specs-canon -->": _specs_canon_table,
}


def render_registry_tables(text: str) -> str:
    """Fill every registry placeholder in a law fragment from ``core.workspace_layout``."""
    for placeholder, render in _PLACEHOLDERS.items():
        text = text.replace(placeholder, render())
    return text
