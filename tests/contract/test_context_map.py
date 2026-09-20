"""Intent: CONTRACT — T-047-53/T-047-54 (SPEC 0.4.7 FR2, AC2.1); size: SMALL (contract).

The context balance of a dadaia-workspace, pinned from the library source:

1. every dd- skill that touches a governed area opens that area's scoped `AGENTS.md`
   as the FIRST numbered step of its procedure, naming the workspace-relative path;
2. `public/data/CONTEXT-MAP.md` carries one row per surface, the rows name surfaces
   that exist, every surface has a row, and the Measured column equals `wc -c`.

The scoped law reaches every harness by procedure rather than by loader luck, so the
step-1 table below is the contract, not a description.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import render_registry_tables
from tests.helpers.scan_population import assert_populated

pytestmark = pytest.mark.contract

_PKG_ROOT = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_PUBLIC = _PKG_ROOT / "public"
_SKILLS_DIR = _PUBLIC / "skills"
_CONTEXT_MAP = _PUBLIC / "data" / "CONTEXT-MAP.md"

# --------------------------------------------------------------------------- #
# The step-1 contract: skill -> the workspace-relative scoped law it opens first.
# --------------------------------------------------------------------------- #

STEP_ONE_LAW: dict[str, str] = {
    "dd-backlog-definition": "specs/backlog/AGENTS.md",
    "dd-bug-registration": "specs/bugs/AGENTS.md",
    "dd-bug-resolution": "specs/bugs/AGENTS.md",
    "dd-release-definition": "specs/releases/AGENTS.md",
    "dd-release-implementation": "specs/releases/AGENTS.md",
    "dd-audit-project": "specs/audits/AGENTS.md",
    "dd-handoff-emitter": ".dadaia/handoff/AGENTS.md",
    "dd-spec-navigator": "specs/AGENTS.md",
    "dd-code-review": "specs/memory/AGENTS.md",
    "dd-cli-library": ".dadaia/AGENTS.md",
}

# The installed path each scoped-law SOURCE under `public/` becomes in a workspace.
SCOPED_SOURCE_BY_INSTALLED_PATH: dict[str, Path] = {
    "specs/AGENTS.md": _PUBLIC / "templates" / "specs-AGENTS.md",
    "specs/backlog/AGENTS.md": _PUBLIC / "scaffold" / "backlog" / "AGENTS.md",
    "specs/bugs/AGENTS.md": _PUBLIC / "scaffold" / "bugs" / "AGENTS.md",
    "specs/releases/AGENTS.md": _PUBLIC / "scaffold" / "releases" / "AGENTS.md",
    "specs/audits/AGENTS.md": _PUBLIC / "scaffold" / "audits" / "AGENTS.md",
    "specs/memory/AGENTS.md": _PUBLIC / "scaffold" / "memory" / "AGENTS.md",
    "specs/ADRs/AGENTS.md": _PUBLIC / "scaffold" / "ADRs" / "AGENTS.md",
    ".dadaia/AGENTS.md": _PUBLIC / "data" / "dadaia-AGENTS.md",
    ".dadaia/handoff/AGENTS.md": _PUBLIC / "data" / "handoff-AGENTS.md",
    ".dadaia/tmp/AGENTS.md": _PUBLIC / "data" / "tmp-AGENTS.md",
    ".dadaia/states/AGENTS.md": _PUBLIC / "data" / "states-AGENTS.md",
    "repos/<slug>/AGENTS.md": _PUBLIC / "templates" / "repo-AGENTS.md",
    "tests/AGENTS.md": _PUBLIC / "templates" / "tests-AGENTS.md",
}

_FIRST_NUMBERED_STEP = re.compile(r"^1\. (?P<body>.+)$", re.MULTILINE)


def _first_numbered_step(skill: str) -> str:
    text = (_SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
    match = _FIRST_NUMBERED_STEP.search(text)
    assert match is not None, (
        f"{skill}/SKILL.md has no numbered procedure at all — step 1 must be "
        f"`1. Open `{STEP_ONE_LAW[skill]}` (the area's scoped law) and follow it.`"
    )
    return match.group("body")


@pytest.mark.parametrize("skill", sorted(STEP_ONE_LAW))
def test_skill_step_one_opens_its_scoped_law(skill: str) -> None:
    """FR2a — the first numbered step names the area's scoped law, root-relative."""
    expected = STEP_ONE_LAW[skill]
    step = _first_numbered_step(skill)
    assert expected in step, (
        f"{skill}/SKILL.md step 1 is {step!r}; it must open `{expected}` "
        "(the area's scoped law) before anything else."
    )


def test_every_step_one_path_is_an_installed_scoped_law() -> None:
    """FR2c — a step-1 path names a scoped law the library actually ships."""
    assert_populated(set(STEP_ONE_LAW), sentinel="dd-cli-library")
    missing = sorted(
        f"{skill} -> {path}"
        for skill, path in STEP_ONE_LAW.items()
        if not SCOPED_SOURCE_BY_INSTALLED_PATH.get(path, Path("/nonexistent")).exists()
    )
    assert missing == [], "step-1 paths with no library source:\n" + "\n".join(missing)


# --------------------------------------------------------------------------- #
# The surfaces: what CONTEXT-MAP.md must account for, and their ceilings.
# --------------------------------------------------------------------------- #

_ROOT_MAP_CEILING = 8192
_SCOPED_CEILING = 4096
_SKILL_CEILING = 6144
_UNBOUNDED = "—"


def installed_bytes(src: Path) -> int:
    """Bytes of *src* as a workspace actually receives it.

    `stage` renders every `<!-- … -->` registry placeholder before install, so the
    source size is not what an agent loads: `.dadaia/AGENTS.md` carries the zone table
    on top of its authored text. The ceiling and the CONTEXT-MAP Measured column are
    both this number.
    """
    return len(render_registry_tables(src.read_text(encoding="utf-8")).encode("utf-8"))


def _persona_sources() -> dict[str, Path]:
    return {p.stem: p for p in sorted((_PUBLIC / "agents").glob("*.md"))}


def _skill_sources() -> dict[str, Path]:
    return {p.parent.name: p for p in sorted(_SKILLS_DIR.glob("*/SKILL.md"))}


def surfaces() -> dict[str, tuple[Path, int | str]]:
    """Every context surface the library ships: key -> (source file, byte ceiling).

    The key is the surface as it appears in an installed workspace — the installed
    path for the map and the scoped law, the entity name for a skill or persona.
    """
    found: dict[str, tuple[Path, int | str]] = {
        "AGENTS.md": (_PUBLIC / "data" / "AGENTS.md", _ROOT_MAP_CEILING)
    }
    for installed, src in SCOPED_SOURCE_BY_INSTALLED_PATH.items():
        found[installed] = (src, _SCOPED_CEILING)
    for name, src in _skill_sources().items():
        found[name] = (src, _SKILL_CEILING)
    for name, src in _persona_sources().items():
        found[name] = (src, _UNBOUNDED)
    assert_populated(set(found), sentinel="specs/bugs/AGENTS.md")
    return found


# --------------------------------------------------------------------------- #
# (a) The ceilings — measured on the installed-shape SOURCES under `public/`.
# --------------------------------------------------------------------------- #


def test_ceilings_hold_on_every_context_surface() -> None:
    """AC1.1 — 8192 for the root map, 4096 for a scoped law, 6144 for a skill,
    measured on the INSTALLED (registry-rendered) form, not the authored source."""
    over = sorted(
        f"{key}: {installed_bytes(src)} B > {ceiling} B ({src.name})"
        for key, (src, ceiling) in surfaces().items()
        if isinstance(ceiling, int) and installed_bytes(src) > ceiling
    )
    assert over == [], "context surfaces over their byte ceiling:\n" + "\n".join(over)


def test_every_scoped_law_source_has_an_installed_path() -> None:
    """No scoped `AGENTS.md` ships without a declared installed path — otherwise the
    ceiling table and the map would silently miss it."""
    shipped: set[Path] = set()
    for sub in ("data", "scaffold", "templates"):
        base = _PUBLIC / sub
        shipped |= set(base.glob("**/AGENTS.md")) | set(base.glob("**/*-AGENTS.md"))
    shipped -= {_PUBLIC / "data" / "AGENTS.md"}
    shipped -= {_PUBLIC / "templates" / "tests-CLAUDE.md", _PUBLIC / "templates" / "repo-CLAUDE.md"}
    assert_populated(shipped, sentinel=_PUBLIC / "scaffold" / "bugs" / "AGENTS.md")
    unmapped = sorted(
        str(p.relative_to(_PUBLIC))
        for p in shipped
        if p not in set(SCOPED_SOURCE_BY_INSTALLED_PATH.values())
    )
    assert unmapped == [], (
        "scoped law source(s) with no installed path in SCOPED_SOURCE_BY_INSTALLED_PATH "
        "(add the row, then add it to CONTEXT-MAP.md §2):\n" + "\n".join(unmapped)
    )


# --------------------------------------------------------------------------- #
# (b)/(c) Citation: every scoped law is reachable, every step-1 path is real.
# --------------------------------------------------------------------------- #


def test_every_scoped_law_is_cited_by_the_map_or_a_skill_step_one() -> None:
    """FR2 — a scoped `AGENTS.md` nobody opens is law nobody reads."""
    cited = set(_map_surface_rows()) | set(STEP_ONE_LAW.values())
    orphans = sorted(set(SCOPED_SOURCE_BY_INSTALLED_PATH) - cited)
    assert orphans == [], (
        "scoped law cited neither by CONTEXT-MAP.md nor by a skill's step 1:\n" + "\n".join(orphans)
    )


# --------------------------------------------------------------------------- #
# (d)/(e) The map itself: one row per surface, Measured == `wc -c`.
# --------------------------------------------------------------------------- #

_SURFACE_TABLE_HEADER = "| Surface |"


def _map_lines() -> list[str]:
    return _CONTEXT_MAP.read_text(encoding="utf-8").split("\n")


def _map_surface_rows() -> dict[str, int]:
    """Surface key -> line index, for every row of every `| Surface |` table."""
    rows: dict[str, int] = {}
    in_table = False
    for index, line in enumerate(_map_lines()):
        if line.startswith(_SURFACE_TABLE_HEADER):
            in_table = True
            continue
        if in_table and not line.startswith("|"):
            in_table = False
            continue
        if not in_table or set(line) <= set("|-: "):
            continue
        key = line.split("|")[1].strip().strip("`")
        assert key not in rows, f"CONTEXT-MAP.md names the surface `{key}` twice"
        rows[key] = index
    assert_populated(set(rows), sentinel="AGENTS.md")
    return rows


def test_context_map_has_exactly_one_row_per_surface() -> None:
    """The map is the auditable balance: no surface missing, no row invented."""
    rows = set(_map_surface_rows())
    known = set(surfaces())
    assert sorted(rows - known) == [], "CONTEXT-MAP.md rows naming no existing surface"
    assert sorted(known - rows) == [], "context surfaces with no CONTEXT-MAP.md row"


def test_measured_column_matches_the_bytes_on_disk() -> None:
    """The Measured column is a recorded fact, not a claim.

    Re-record with `UPDATE_CONTEXT_MAP=1 pytest tests/contract/test_context_map.py`.
    """
    lines = _map_lines()
    rows = _map_surface_rows()
    known = surfaces()
    updating = os.environ.get("UPDATE_CONTEXT_MAP") == "1"
    drift: list[str] = []
    for key, index in rows.items():
        measured = installed_bytes(known[key][0])
        cells = lines[index].split("|")
        if updating:
            cells[-2] = f" {measured} "
            lines[index] = "|".join(cells)
            continue
        if cells[-2].strip() != str(measured):
            drift.append(f"{key}: map says {cells[-2].strip()!r}, disk says {measured}")
    if updating:
        _CONTEXT_MAP.write_text("\n".join(lines), encoding="utf-8")
        return
    assert drift == [], (
        "CONTEXT-MAP.md Measured column is stale — re-record with "
        "`UPDATE_CONTEXT_MAP=1 pytest tests/contract/test_context_map.py`:\n" + "\n".join(drift)
    )


def test_context_map_is_projected_nowhere() -> None:
    """A library document: no projection rule may install it into a runtime tree."""
    rule_sources = (_PKG_ROOT / "infrastructure" / "projection_rules.py").read_text(
        encoding="utf-8"
    ) + (_PKG_ROOT / "infrastructure" / "public_assets.py").read_text(encoding="utf-8")
    assert "CONTEXT-MAP" not in rule_sources, (
        "CONTEXT-MAP.md is a library document — it is staged with `data/` and installed "
        "nowhere; a projection rule naming it is the bug."
    )


def _norm_statement(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lstrip("-*#|> ")).rstrip(".").lower()


def test_no_statement_lives_in_two_shipped_homes() -> None:
    """AC1.2 (0.4.7 c6): a rule lives in one home — no normalised bullet statement of
    60+ chars appears in two shipped rule files or skills (the root map, every scoped
    AGENTS.md source, every skill Markdown, the fixed sections). A statement is a bullet;
    numbered procedure steps (two skills may open the same scoped law) and prose headers
    are not statements."""
    shipped = [
        *sorted(_PUBLIC.glob("skills/**/*.md")),
        *sorted(_PUBLIC.glob("scaffold/**/AGENTS.md")),
        *sorted(_PUBLIC.glob("templates/*-AGENTS.md")),
        *sorted(_PUBLIC.glob("data/*.md")),
        *sorted(_PUBLIC.glob("data/fixed/*.md")),
    ]
    homes: dict[str, set[str]] = {}
    for path in shipped:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.lstrip().startswith("- "):
                continue
            key = _norm_statement(line)
            if len(key) >= 60:
                homes.setdefault(key, set()).add(path.relative_to(_PUBLIC).as_posix())
    duplicated = {k: sorted(v) for k, v in homes.items() if len(v) > 1}
    assert duplicated == {}, "a statement lives in two homes:\n" + "\n".join(
        f"  {v} :: {k[:90]}" for k, v in duplicated.items()
    )
