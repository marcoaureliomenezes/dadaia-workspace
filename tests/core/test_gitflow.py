"""AC6.1 (T-050-11): the project gitflow value — roles fixed, names free."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.core.gitflow import DEFAULT, from_mapping


def test_the_default_names_live_only_in_default_and_work_is_cut_from_integration() -> None:
    """sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-6: only DEFAULT spells it.
    sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-5: the skill cuts work from integration."""
    pkg = Path(__file__).resolve().parents[2] / "dadaia_workspace"
    literal = re.compile(r'principal: main|"--principal", "main"|else "main"')
    assert [p.name for p in pkg.rglob("*.py") if literal.search(p.read_text("utf-8"))] == []
    skill = (pkg / "public/skills/dd-gitflow-default/SKILL.md").read_text("utf-8")
    work_row = next(r for r in skill.splitlines() if r.startswith("| work `"))
    assert work_row.split("|")[3].strip() == "integration"


def test_one_live_release_reader_and_no_verb_mints_a_version() -> None:
    """sa-live-work-branch-named-three-ways#B41-5: one reader of the live id, no tag+1.
    sa-live-work-branch-named-three-ways#B41-4: release-please owns the version; no module lists or bumps tags."""
    pkg = Path(__file__).resolve().parents[2] / "dadaia_workspace"
    src = {p.name: p.read_text("utf-8") for p in pkg.rglob("*.py") if "public" not in p.parts}
    assert [n for n, t in src.items() if "def resolve_live_release_id" in t] == ["gitflow.py"]
    assert [n for n, t in src.items() if re.search(r'"tag", "--sort|\]\) \+ 1\}', t)] == []
    assert "release-please owns the version" in (pkg.parent / "AGENTS.md").read_text("utf-8")


@pytest.mark.parametrize(
    ("branch", "role"),
    [
        ("main", "principal"),
        ("develop", "integration"),
        ("feature/0.5.0", "work"),
        ("feature/v0.5.0", None),
        ("feature/0.5", None),
        ("feature/0.5.0-rc", None),
        ("hotfix/1.0.0", None),
        ("trunk", None),
    ],
)
def test_role_of_default(branch: str, role: str | None) -> None:
    assert DEFAULT.role_of(branch) == role


def test_from_mapping_reads_the_block_keys_and_maps_their_roles() -> None:
    flow = from_mapping({"principal": "trunk", "integration": "next", "work": "work/"})
    roles = [flow.role_of(b) for b in ("trunk", "next", "work/1.2.3", "main", "feature/1.2.3")]
    assert roles == ["principal", "integration", "work", None, None]


@pytest.mark.parametrize(
    "mapping",
    [
        {"principal": "main", "integration": "main", "work": "feature/"},  # same name twice
        {"principal": "main", "integration": "develop", "work": ""},  # empty prefix
        {"principal": "main", "integration": "develop"},  # key missing
        {"principal": "ma in", "integration": "develop", "work": "feature/"},
        {"principal": "main", "integration": "dev..x", "work": "feature/"},
        {"principal": "main", "integration": "develop", "work": "/feature/"},
        {"principal": "a.lock", "integration": "develop", "work": "feature/"},
        {"principal": 7, "integration": "develop", "work": "feature/"},
        {"principal": "release", "integration": "develop", "work": "release/"},  # nests
        {"principal": "main", "integration": "rel", "work": "rel/v"},  # nests (C9)
        "main",
    ],
)
def test_from_mapping_refuses_invalid(mapping: object) -> None:
    with pytest.raises(ValueError):
        from_mapping(mapping)
