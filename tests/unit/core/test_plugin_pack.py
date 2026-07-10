"""Unit tests for the plugin-pack core models (v0.1.60 FR2, AC-2).

``PluginPack`` (parsed ``pack.json`` descriptor) + ``InstalledPlugins`` (the persisted ledger
record) are pure ``core`` value objects with NO I/O — the discipline mirror of
``HarnessProfile``. These tests pin the parse/validate contract of ``PluginPack.from_dict``
(a malformed descriptor is rejected, never silently accepted) and the idempotent-add
semantics of the ledger record the ``dadaia plugin`` CLI depends on.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.plugin_pack import (
    CURRENT_SCHEMA_VERSION,
    InstalledPlugins,
    PluginPack,
)


def test_from_dict_parses_full_defaults_and_of_builder() -> None:
    pack = PluginPack.from_dict(
        {
            "schema_version": "1",
            "name": "frontend-design",
            "agents": ["frontend-engineer", "design-specialist"],
            "skills": ["browser-frontend-implementation"],
            "rules": [],
        }
    )
    assert pack == PluginPack(
        name="frontend-design",
        agents=("frontend-engineer", "design-specialist"),
        skills=("browser-frontend-implementation",),
        rules=(),
        schema_version="1",
    )

    defaulted = PluginPack.from_dict({"name": "devops", "agents": ["devops-engineer"]})
    assert defaulted.schema_version == CURRENT_SCHEMA_VERSION
    assert defaulted.skills == ()
    assert defaulted.rules == ()

    built = PluginPack.of("devops", agents=("devops-engineer",))
    assert built.schema_version == CURRENT_SCHEMA_VERSION
    assert built.agents == ("devops-engineer",)


@pytest.mark.parametrize(
    ("name", "payload", "match"),
    [
        ("missing_name", {"name": None, "agents": ["a"]}, "non-empty 'name'"),
        ("empty_name", {"name": "", "agents": ["a"]}, "non-empty 'name'"),
        ("whitespace_name", {"name": "   ", "agents": ["a"]}, "non-empty 'name'"),
        ("numeric_name", {"name": 42, "agents": ["a"]}, "non-empty 'name'"),
        (
            # A pack with no agents replaces no stub — it is meaningless and must be
            # rejected.
            "zero_agents",
            {"name": "empty", "agents": []},
            "at least one agent",
        ),
        (
            "non_string_list_entry",
            {"name": "x", "agents": ["a"], "skills": ["ok", 7]},
            "'skills' must be a list of strings",
        ),
        (
            "non_list_field",
            {"name": "x", "agents": "frontend-engineer"},
            "'agents' must be a list of strings",
        ),
    ],
)
def test_from_dict_rejects_malformed_descriptor(
    name: str, payload: dict[str, object], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        PluginPack.from_dict(payload)


def test_installed_plugins_ledger_semantics() -> None:
    assert InstalledPlugins.empty() == InstalledPlugins(schema_version="1", plugins=())
    assert InstalledPlugins.of(("frontend-design",)) == InstalledPlugins(
        schema_version="1", plugins=("frontend-design",)
    )

    # with_added appends in order.
    ledger = InstalledPlugins.empty().with_added("frontend-design")
    assert ledger.plugins == ("frontend-design",)
    ledger = ledger.with_added("devops")
    assert ledger.plugins == ("frontend-design", "devops")

    # with_added is idempotent — a re-install adds nothing (AC-3), returning self.
    idem_ledger = InstalledPlugins.of(("frontend-design",))
    again = idem_ledger.with_added("frontend-design")
    assert again is idem_ledger
    assert again.plugins == ("frontend-design",)

    # with_removed (v0.1.63 FR2) is the pure inverse of with_added, order-preserving.
    two_pack = InstalledPlugins.of(("frontend-design", "devops"))
    assert two_pack.with_removed("frontend-design").plugins == ("devops",)
    assert two_pack.with_removed("devops").plugins == ("frontend-design",)

    # Removing an absent name is a no-op returning self (mirrors with_added).
    single = InstalledPlugins.of(("frontend-design",))
    unchanged = single.with_removed("devops")
    assert unchanged is single

    # Removal keeps remaining insertion order and the ledger schema version.
    three_pack = InstalledPlugins(schema_version="1", plugins=("a", "b", "c"))
    removed = three_pack.with_removed("b")
    assert removed.plugins == ("a", "c")
    assert removed.schema_version == "1"
