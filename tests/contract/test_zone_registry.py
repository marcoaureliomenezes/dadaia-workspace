"""Intent: CONTRACT — 0.4.6 AC1 (FR2: the three ratchets born with the zone registry); size: SMALL.

``core.workspace_layout.DADAIA_ZONES`` is the one record of what may live in ``.dadaia/``.
Six ledger bugs (architect G, 2026-07-01..08-26) edited the membership of bare name lists
in ``doctor.py``, ``legacy_dadaia_dirs.py``, ``hygiene.py`` and ``workspace/service.py``
without ever changing their shape; each list disagreed with the next. These ratchets make
the recurrence unrepresentable:

1. the rendered ``.dadaia/AGENTS.md`` table IS the registry (documented == allowed);
2. no other literal in the package holds three or more zone names, and no string literal
   names a retired zone — a second list cannot be born;
3. every ``Creator`` maps to a live module — retiring a feature without deleting its row
   fails the build (the ``test_core_file_io_purity`` "every authorized stem exists" shape).

Ratchet 2 carries a pending-demolition allowance: files outside T-046-24's write set that
still hold a second list, each keyed to the task that deletes it. The allowance moves
down only — an entry whose file no longer violates is stale and fails the test.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from dadaia_workspace.core.workspace_layout import (
    DADAIA_ZONES,
    STATES_CANON,
    Creator,
    zone_names,
)
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.scan_population import assert_populated

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE = _REPO_ROOT / "dadaia_workspace"

#: Zone names retired by 0.4.6 candidate 4 (SPEC FR1/FR9, architect C). A string literal
#: ``.dadaia/<retired>`` anywhere in the package is a path into a directory no record
#: sanctions.
_RETIRED_ZONES: frozenset[str] = frozenset(
    {"reports", "academy", "logs", "runs", "scripts", "dev-report", "runtime"}
)

#: Files outside T-046-24's write set that still hold a second zone list or a retired-zone
#: path literal, keyed to the task whose write set deletes them. Each entry must still
#: violate: once its task lands, the entry is stale and must go (ratchet moves down only).
_PENDING_DEMOLITION: dict[str, str] = {
    "dadaia_workspace/features/export/service.py": "T-046-31",
}

#: The module that creates each ``Creator``'s zones. ``None`` = no single package module
#: (a runtime writer is any feature; the operator's hands are outside the package).
_CREATOR_HOME: dict[Creator, str | None] = {
    Creator.INIT: "dadaia_workspace.features.workspace.service",
    Creator.INSTALL: "dadaia_workspace.infrastructure.public_assets",
    Creator.RUNTIME: None,
    Creator.OPERATOR: None,
}


def _package_sources() -> list[Path]:
    files = sorted(p for p in _PACKAGE.rglob("*.py") if "__pycache__" not in p.parts)
    assert_populated(files, _PACKAGE / "core" / "workspace_layout.py")
    return files


def _second_list_hits(tree: ast.AST, names: frozenset[str]) -> list[str]:
    """``line:<detail>`` for every literal holding >= 3 zone names or a retired-zone path."""
    retired_paths = {f".dadaia/{name}" for name in _RETIRED_ZONES}
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Set | ast.Tuple | ast.List):
            found = [
                elt.value
                for elt in node.elts
                if isinstance(elt, ast.Constant)
                and isinstance(elt.value, str)
                and elt.value in names
            ]
            if len(found) >= 3:
                hits.append(f"{node.lineno}: literal holds zone names {found}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.rstrip("/") in retired_paths:
                hits.append(f"{node.lineno}: retired zone path {node.value!r}")
    return hits


def _markdown_tables(text: str) -> list[list[dict[str, str]]]:
    """Every pipe table in *text* as a list of header-keyed rows (cells stripped)."""
    tables: list[list[dict[str, str]]] = []
    header: list[str] | None = None
    for line in text.splitlines():
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            tables.append([])
        elif all(set(c) <= set("-: ") for c in cells):
            continue
        else:
            tables[-1].append(dict(zip(header, cells, strict=False)))
    return tables


def _bare(cell: str) -> str:
    return cell.strip("`").rstrip("/")


@pytest.fixture(scope="module")
def staged_data(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The bytes ``public stage`` writes — the same bytes ``install`` projects to
    ``.dadaia/AGENTS.md``; the source fragment carries only the placeholder."""
    workspace = tmp_path_factory.mktemp("stage")
    FileSystemPublicAssetManager().stage(workspace)
    return workspace / ".dadaia" / "agentic" / "data"


def test_dadaia_agents_table_equals_zone_registry(staged_data: Path) -> None:
    """The staged ``.dadaia/AGENTS.md`` table rows are the registry, row for row, and the
    ``states/AGENTS.md`` canon table is ``STATES_CANON`` — documented == allowed."""
    zone_tables = [
        t
        for t in _markdown_tables((staged_data / "dadaia-AGENTS.md").read_text("utf-8"))
        if t and {"class", "ttl", "creator"} <= set(t[0])
    ]
    assert len(zone_tables) == 1, "exactly one rendered zone table"
    name_col = next(k for k in zone_tables[0][0] if k in {"zone", "folder"})
    rendered = [
        (_bare(row[name_col]), row["class"], row["ttl"], row["creator"]) for row in zone_tables[0]
    ]
    expected = [
        (
            z.name,
            z.cls.value,
            "never" if z.ttl_seconds is None else str(z.ttl_seconds),
            z.creator.value,
        )
        for z in DADAIA_ZONES
    ]
    assert rendered == expected

    canon_tables = [
        {_bare(next(iter(row.values()))) for row in t}
        for t in _markdown_tables((staged_data / "states-AGENTS.md").read_text("utf-8"))
        if t
    ]
    assert STATES_CANON in canon_tables, "states-AGENTS.md carries the closed canon table"


def test_zone_registry_is_the_only_dadaia_name_list() -> None:
    """No set/tuple/list literal in the package holds three or more zone names and no string
    literal names ``.dadaia/<retired>`` — the registry rows (``Zone(...)`` calls, never a
    bare literal) are the only place a zone name is spelled in bulk."""
    names = zone_names()
    violations: dict[str, list[str]] = {}
    for path in _package_sources():
        hits = _second_list_hits(ast.parse(path.read_text("utf-8")), names)
        if hits:
            violations[path.relative_to(_REPO_ROOT).as_posix()] = hits

    unexpected = {p: h for p, h in violations.items() if p not in _PENDING_DEMOLITION}
    assert not unexpected, (
        "a second .dadaia zone list was born outside core.workspace_layout — derive a view "
        f"from DADAIA_ZONES instead: {unexpected}"
    )
    stale = sorted(p for p in _PENDING_DEMOLITION if p not in violations)
    assert not stale, f"pending-demolition entries no longer violate — delete them: {stale}"


def test_every_zone_creator_exists() -> None:
    """Each ``Creator`` used by a row maps to a live module (or, for runtime/operator, to an
    explicit ``None``); a row whose creator was retired fails the build."""
    assert set(_CREATOR_HOME) == set(Creator)
    used = {z.creator for z in DADAIA_ZONES}
    assert used <= set(_CREATOR_HOME)
    for creator, module in _CREATOR_HOME.items():
        if module is not None:
            assert creator in used, f"{creator} names a module but creates no zone"
            importlib.import_module(module)
