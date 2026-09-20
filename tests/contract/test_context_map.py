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
