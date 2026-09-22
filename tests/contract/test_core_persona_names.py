"""Intent: CONTRACT — AC3.2 / T-047-56: the three personas carry their dd- names everywhere.

The rename is a single fact with two homes that cannot drift: the typed roster
(``CORE_AGENTS``, which every model template must cover exactly) and the authored
public surface (persona files, entity registry, behavior map, skill prose). A stale
name in either one is a sub-agent Claude Code cannot dispatch, or a grant the
derivation check cannot resolve — both silent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.core.agent_model_templates import CORE_AGENTS

pytestmark = pytest.mark.contract

_PACKAGE = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_PUBLIC = _PACKAGE / "public"

#: The pre-0.4.7 persona names. Matched only where they are NOT already prefixed.
_RETIRED = re.compile(
    r"(?<![\w-])(" + "|".join(name.removeprefix("dd-") for name in CORE_AGENTS) + r")\b"
)


def test_core_agents_roster_is_the_dd_named_trio() -> None:
    assert CORE_AGENTS == ("dd-product-engineer", "dd-software-engineer", "dd-code-reviewer")


def test_no_retired_persona_name_survives_under_public() -> None:
    offenders: list[str] = []
    for path in sorted(_PUBLIC.rglob("*")):
        if not path.is_file() or path.suffix in {".pyc", ".png"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if _RETIRED.search(line):
                offenders.append(f"{path.relative_to(_PUBLIC)}:{lineno}: {line.strip()[:100]}")
    assert not offenders, "retired persona name(s) under public/:\n" + "\n".join(offenders)


def test_every_persona_file_is_dd_named_and_declares_that_name() -> None:
    agents = sorted((_PUBLIC / "agents").glob("*.md"))
    assert [p.stem for p in agents] == sorted(CORE_AGENTS)
    for path in agents:
        assert f"\nname: {path.stem}\n" in path.read_text(encoding="utf-8")


def test_no_live_file_under_the_package_names_the_deleted_coordinator_persona() -> None:
    """Intent: CONTRACT — roster-keeps-a-coordinator-persona-while-the-main-thread-coordinates.

    ADR 0022 deletes dd-project-manager: the main thread coordinates, dd-product-engineer
    owns backlog, SPEC and product memory. A surviving citation routes work to a persona
    that no longer exists. The one exemption is the policy store's retired-name table,
    which must name it to migrate an operator's existing overlay on read.
    """
    migration_table = _PACKAGE / "infrastructure" / "json_agent_model_policy_store.py"
    offenders: list[str] = []
    for path in sorted(_PACKAGE.rglob("*")):
        if not path.is_file() or path.suffix in {".pyc", ".png"} or path == migration_table:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if "project-manager" in line:
                offenders.append(f"{path.relative_to(_PACKAGE)}:{lineno}: {line.strip()[:100]}")
    assert not offenders, "dd-project-manager cited under dadaia_workspace/:\n" + "\n".join(
        offenders
    )
