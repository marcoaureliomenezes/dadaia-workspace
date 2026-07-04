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


def test_from_dict_parses_a_full_descriptor() -> None:
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


def test_from_dict_defaults_schema_version_when_absent() -> None:
    pack = PluginPack.from_dict({"name": "devops", "agents": ["devops-engineer"]})
    assert pack.schema_version == CURRENT_SCHEMA_VERSION
    assert pack.skills == ()
    assert pack.rules == ()


@pytest.mark.parametrize("bad_name", [None, "", "   ", 42])
def test_from_dict_rejects_missing_or_empty_name(bad_name: object) -> None:
    with pytest.raises(ValueError, match="non-empty 'name'"):
        PluginPack.from_dict({"name": bad_name, "agents": ["a"]})


def test_from_dict_rejects_zero_agents() -> None:
    """A pack with no agents replaces no stub — it is meaningless and must be rejected."""
    with pytest.raises(ValueError, match="at least one agent"):
        PluginPack.from_dict({"name": "empty", "agents": []})


def test_from_dict_rejects_non_string_list_entries() -> None:
    with pytest.raises(ValueError, match="'skills' must be a list of strings"):
        PluginPack.from_dict(
            {"name": "x", "agents": ["a"], "skills": ["ok", 7]},
        )


def test_from_dict_rejects_non_list_field() -> None:
    with pytest.raises(ValueError, match="'agents' must be a list of strings"):
        PluginPack.from_dict({"name": "x", "agents": "frontend-engineer"})


def test_of_builds_at_current_schema_version() -> None:
    pack = PluginPack.of("devops", agents=("devops-engineer",))
    assert pack.schema_version == CURRENT_SCHEMA_VERSION
    assert pack.agents == ("devops-engineer",)


def test_installed_plugins_empty_and_of() -> None:
    assert InstalledPlugins.empty() == InstalledPlugins(schema_version="1", plugins=())
    assert InstalledPlugins.of(("frontend-design",)) == InstalledPlugins(
        schema_version="1", plugins=("frontend-design",)
    )


def test_with_added_appends_new_pack() -> None:
    ledger = InstalledPlugins.empty().with_added("frontend-design")
    assert ledger.plugins == ("frontend-design",)
    ledger = ledger.with_added("devops")
    assert ledger.plugins == ("frontend-design", "devops")


def test_with_added_is_idempotent_no_duplicate() -> None:
    """A re-install adds nothing — the ledger idempotency the CLI relies on (AC-3)."""
    ledger = InstalledPlugins.of(("frontend-design",))
    again = ledger.with_added("frontend-design")
    assert again is ledger
    assert again.plugins == ("frontend-design",)
