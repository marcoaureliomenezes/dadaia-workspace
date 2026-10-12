"""The project gitflow value: roles fixed, names free."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.core.gitflow import DEFAULT, from_mapping


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


def test_the_history_rewrite_rule_covers_only_the_branches_that_advance_by_merge_or_pr() -> None:
    """A wt/* branch is rebased by its owner; the rule must not reach it,
    and both of its verbs (rewrite, force-push) take the same scope."""
    skill = (
        Path(__file__).resolve().parents[2]
        / "dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md"
    ).read_text("utf-8")
    rows = [ln.split("|")[1:5] for ln in skill.splitlines() if re.match(r"\| [a-z]+( `|\s+\|)", ln)]
    covered = {r[0].split()[0] for r in rows if "wt/" not in r[0]}
    assert covered == {"work", "integration", "principal"}
    rule = next(ln for ln in skill.splitlines() if "pushed history" in ln)
    verbs, scope = rule.split("force-pushing,", 1)
    assert "pushed history of," in verbs
    assert "work branch" in scope
    assert "advances only by PR" in scope
    assert not {"job", "backlog", "task", "plain"} & set(re.findall(r"\w+", scope))
