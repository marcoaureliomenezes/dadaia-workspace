"""Intent: CONTRACT — AC6.1 (T-050-11): the project gitflow value — roles fixed, names free."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.gitflow import DEFAULT, Gitflow, from_mapping


def test_default_is_main_develop_feature() -> None:
    assert Gitflow(principal="main", integration="develop", work_prefix="feature/") == DEFAULT


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


def test_role_of_custom_gitflow() -> None:
    flow = Gitflow(principal="trunk", integration="next", work_prefix="work/")
    assert flow.role_of("trunk") == "principal"
    assert flow.role_of("next") == "integration"
    assert flow.role_of("work/1.2.3") == "work"
    assert flow.role_of("main") is None
    assert flow.role_of("feature/1.2.3") is None


def test_from_mapping_reads_the_block_keys() -> None:
    flow = from_mapping({"principal": "trunk", "integration": "next", "work": "work/"})
    assert flow == Gitflow(principal="trunk", integration="next", work_prefix="work/")


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
        "main",
    ],
)
def test_from_mapping_refuses_invalid(mapping: object) -> None:
    with pytest.raises(ValueError):
        from_mapping(mapping)
