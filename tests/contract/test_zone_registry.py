"""0.4.6 AC1 (FR2: the three ratchets born with the zone registry); 0.5.0 AC6.1
(the canonical sets widened to ledger vocabularies, phases, trio names, gitflow roles; every
``public/**/*.md`` law file scanned); size: SMALL.

``core.workspace_layout.DADAIA_ZONES`` is the one record of what may live in ``.dadaia/``.
Six ledger bugs (architect G, 2026-07-01..08-26) edited the membership of bare name lists
in ``doctor.py``, ``legacy_dadaia_dirs.py``, ``hygiene.py`` and ``workspace/service.py``
without ever changing their shape; each list disagreed with the next. These ratchets make
the recurrence unrepresentable:

1. the rendered ``.dadaia/AGENTS.md`` table IS the registry (documented == allowed);
2. no other literal in the package holds three or more names of ANY canonical set (zones,
   root entries, specs canon members, repo-tree exclusions), and no string literal names a
   retired zone — a second list cannot be born;
3. every ``Creator`` maps to a live module — retiring a feature without deleting its row
   fails the build (the ``test_core_file_io_purity`` "every authorized stem exists" shape).

Ratchet 2 carries a pending-demolition allowance: files outside T-046-24's write set that
still hold a second list, each keyed to the task that deletes it. The allowance moves
down only — an entry whose file no longer violates is stale and fails the test.
"""

from __future__ import annotations

import ast
import importlib
import json
import re
import typing
from pathlib import Path

import pytest

from dadaia_workspace.core.gitflow import Role
from dadaia_workspace.core.workspace_layout import (
    CANON_ROOT_MEMBERS,
    DADAIA_ZONES,
    ROOT_ALLOWED_DIRS,
    ROOT_ALLOWED_FILES,
    STATES_CANON,
    Creator,
    root_entries_display,
    specs_canon_table_rows,
    zone_names,
)
from dadaia_workspace.features.specs.doctor_common import RELEASE_ARTIFACTS
from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    render_registry_tables,
)
from tests.helpers.scan_population import assert_populated

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMAS = _REPO_ROOT / "dadaia_workspace" / "public" / "schemas"
_PACKAGE = _REPO_ROOT / "dadaia_workspace"

#: Zone names retired by 0.4.6 candidate 4 (SPEC FR1/FR9, architect C). A string literal
#: ``.dadaia/<retired>`` anywhere in the package is a path into a directory no record
#: sanctions.
_RETIRED_ZONES: frozenset[str] = frozenset(
    {"academy", "logs", "runs", "scripts", "dev-report", "runtime"}
)

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


#: A stdlib ledger script owns its subset (it cannot import core); the parity test
#: pins every subset to the one vocabulary.
_PARITY = "parity:tests/unit/skills/test_ledger_write_verbs_refuse_with_the_pair_intact.py"
_TEXT = "sa-text-restates-rules-the-code-contradicts"

#: Every closed set of canonical names the registry owns (0.4.7 FR5 widened ratchet 2
#: from the zone names to all four): a literal holding three or more names of ONE set,
#: outside ``core/workspace_layout.py``, is a second list of that set.
_CANONICAL_SETS: dict[str, frozenset[str]] = {
    "zone": zone_names(),
    "root": ROOT_ALLOWED_DIRS | ROOT_ALLOWED_FILES,
    "specs-canon": CANON_ROOT_MEMBERS,
    "phase": frozenset(
        json.loads((_SCHEMAS / "releases/release-state-v1.schema.json").read_text("utf-8"))[
            "properties"
        ]["phase"]["enum"]
    ),
    "ledger-disposition": frozenset(
        json.loads((_SCHEMAS / "histo/histo-record-v1.schema.json").read_text("utf-8"))[
            "properties"
        ]["disposition"]["enum"]
    ),
    "trio": frozenset(RELEASE_ARTIFACTS),
    "gitflow-role": frozenset(typing.get_args(Role)),
}

#: Each set's own defining module — the one place its names are spelled in bulk.
_SET_HOME: dict[str, str] = {
    "phase": "dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py",
    "ledger-disposition": "dadaia_workspace/public/schemas/histo/histo-record-v1.schema.json",
    "trio": "dadaia_workspace/features/specs/doctor_common.py",
    "gitflow-role": "dadaia_workspace/core/gitflow.py",
}

#: AC6.5 allowance for the widened sets (birth keys pinned at T-050-135): each second list,
#: keyed ``file`` -> ``parity:<test file>``, the test proving its set.
_SECOND_LIST_BIRTH = frozenset(  # its keys at T-050-135; the allowance only shrinks
    {
        "dadaia_workspace/public/skills/dd-audit-project/scripts/_audit_check.py",
        "dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_schema.py",
        "dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_check.py",
        "dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py",
    }
)
_SECOND_LIST_ALLOWANCE: dict[str, str] = {
    "dadaia_workspace/public/skills/dd-audit-project/scripts/_audit_check.py": _PARITY,
    "dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_schema.py": _PARITY,
    "dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_check.py": _PARITY,
    # the stdlib script cannot import the package: its TRIO is proven by the trio row
    "dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py": (
        "parity:tests/unit/features/specs/test_release_tree.py"
    ),
}


def _allowance_violations(
    hits: set[str], allowance: dict[str, str], *, birth: frozenset[str]
) -> list[str]:
    """Unlisted hits, stale keys, a value naming no test file, keys absent at birth."""
    problems = [f"unlisted: {hit}" for hit in sorted(hits - allowance.keys())]
    problems += [f"stale key (delete it): {key}" for key in sorted(allowance.keys() - hits)]
    problems += [
        f"{key} -> {value!r} names no test file"
        for key, value in sorted(allowance.items())
        if not value.startswith("parity:")
        or not (_REPO_ROOT / value.removeprefix("parity:")).is_file()
    ]
    return problems + [f"absent at birth: {key}" for key in sorted(allowance.keys() - birth)]


#: Literals whose names coincide with a canonical set by accident, not by restatement,
#: each with the evidence that it is not a canon list. An entry whose file no longer
#: holds such a literal is stale and fails the test.
_NOT_A_NAME_LIST: dict[str, str] = {}


def _second_list_hits(
    tree: ast.AST, names: frozenset[str], home: frozenset[str] = frozenset()
) -> list[str]:
    """``line:<detail>`` for every literal holding >= 3 names of one canonical set (sets
    in *home* are this file's own) or a retired-zone path."""
    retired_paths = {f".dadaia/{name}" for name in _RETIRED_ZONES}
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Set | ast.Tuple | ast.List):
            for label, canonical in _CANONICAL_SETS.items():
                if label in home:
                    continue
                found = [
                    elt.value
                    for elt in node.elts
                    if isinstance(elt, ast.Constant)
                    and isinstance(elt.value, str)
                    and elt.value.rstrip("/") in canonical
                ]
                if len(found) >= 3:
                    hits.append(f"{node.lineno}: literal holds {label} names {found}")
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.rstrip("/") in retired_paths
        ):
            hits.append(f"{node.lineno}: retired zone path {node.value!r}")
    return hits


def _restated_law_lines(text: str) -> list[str]:
    """``line:<detail>`` for every law line restating one canonical set instead of
    referring to some of its members: the WHOLE set for a set of four or fewer names,
    half or more of a larger one."""
    hits: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        tokens = set(re.findall(r"[A-Za-z0-9_.\-]+", line))
        for label, canonical in _CANONICAL_SETS.items():
            found = sorted(tokens & canonical)
            if (
                (len(found) == len(canonical))
                if len(canonical) <= 4
                else (len(found) * 2 >= len(canonical))
            ):
                hits.append(f"{number}: line restates the {label} set {found}")
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
    widened: set[str] = set()
    for path in _package_sources():
        rel = path.relative_to(_REPO_ROOT).as_posix()
        if rel.endswith("core/workspace_layout.py"):
            continue
        home = frozenset(label for label, module in _SET_HOME.items() if module == rel)
        hits = _second_list_hits(ast.parse(path.read_text("utf-8")), names, home)
        if hits and rel in _SECOND_LIST_ALLOWANCE:
            widened.add(rel)
            continue
        if hits and rel not in _NOT_A_NAME_LIST:
            violations[rel] = hits
        elif not hits and rel in _NOT_A_NAME_LIST:
            violations[rel] = ["stale _NOT_A_NAME_LIST entry: no canonical-name literal left"]

    assert not violations, (
        "a second .dadaia zone list was born outside core.workspace_layout — derive a view "
        f"from DADAIA_ZONES instead: {violations}"
    )
    problems = _allowance_violations(widened, _SECOND_LIST_ALLOWANCE, birth=_SECOND_LIST_BIRTH)
    assert problems == [], "\n".join(problems)


def test_a_planted_second_list_of_a_widened_set_trips() -> None:
    """RED fixture (AC6.1): a literal restating the gitflow roles or the trio is a second
    list outside its home module, and not inside it."""
    tree = ast.parse(
        "ROLES = ('principal', 'integration', 'work')\nT = ['SPEC.md', 'PLAN.md', 'TASKS.md']\n"
    )
    assert len(_second_list_hits(tree, zone_names())) == 2
    assert len(_second_list_hits(tree, zone_names(), frozenset({"gitflow-role", "trio"}))) == 0


def _restating_law_files() -> set[str]:
    """``path:set`` for every ``public/**/*.md`` (archives aside) holding a line that
    restates a canonical set."""
    public = _PACKAGE / "public"
    hits: set[str] = set()
    for path in sorted(public.rglob("*.md")):
        if "_archive" in path.parts:
            continue
        for hit in _restated_law_lines(path.read_text("utf-8")):
            label = hit.split("the ", 1)[1].split(" set ", 1)[0]
            hits.add(f"{path.relative_to(public).as_posix()}:{label}")
    return hits


def test_the_law_source_never_restates_a_canonical_set() -> None:
    """No law line spells out a canonical set: §5.1 (root), §5.3 (repo exclusions) and
    §6.2 (specs canon) carry placeholders ``public stage`` fills from the registry, and
    every other ``public/**/*.md`` restatement is gone (AC6.1's allowance drained)."""
    assert _restating_law_files() == set()


def test_a_planted_law_line_restating_a_small_set_trips() -> None:
    """RED fixture (AC6.1): the whole trio on one line is a restatement; two of it is not."""
    assert _restated_law_lines("- SPEC.md, PLAN.md and TASKS.md are the trio.\n")
    assert not _restated_law_lines("- SPEC.md and PLAN.md only.\n")


def test_staged_law_canon_tables_equal_the_registry(staged_data: Path) -> None:
    """The staged ``specs-AGENTS.md`` canon table IS ``specs_canon_table_rows()``, row for
    row; the staged law's root line and ``repo-AGENTS.md``'s exclusion line ARE the rendered
    registry lists — documented == allowed, wherever the rule now lives."""
    text = (staged_data / "AGENTS.md").read_text("utf-8")
    # The scoped templates are not staged (sa-staged-assets-without-consumers#44.2: no
    # reader of .dadaia/agentic/templates); they are rendered by the same one renderer.
    scoped = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "templates"
    specs_law = render_registry_tables((scoped / "specs-AGENTS.md").read_text("utf-8"))
    repo_law = render_registry_tables((scoped / "repo-AGENTS.md").read_text("utf-8"))
    canon_tables = [
        t for t in _markdown_tables(specs_law) if t and {"area", "members"} <= set(t[0])
    ]
    assert len(canon_tables) == 1, "exactly one rendered specs-canon table"
    rendered = [(_bare(row["area"]), row["members"].strip("`")) for row in canon_tables[0]]
    expected = [
        ("root" if parent == "" else parent, members)
        for parent, members in specs_canon_table_rows()
    ]
    assert rendered == expected

    assert f"- Root holds only: `{root_entries_display()}`" in text
    for placeholder in ("<!-- root -->", "<!-- specs-canon -->"):
        for rendered in (text, specs_law, repo_law):
            assert placeholder not in rendered, f"{placeholder} was left unrendered"


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
