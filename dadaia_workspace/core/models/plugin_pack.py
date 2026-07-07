"""Plugin-pack domain models — the in-package pack descriptor and the install ledger.

Two pure, typed ``core`` value objects for the ``dadaia plugin`` subsystem (v0.1.60 FR1/FR2),
mirroring the ``HarnessProfile`` precedent:

* :class:`PluginPack` — a parsed ``pack.json`` descriptor (``name`` + ``agents``/``skills``/
  ``rules`` tuples + ``schema_version``). Its :meth:`PluginPack.from_dict` parse/validate is
  the only "logic" here and is **pure** (takes a mapping, never a path).
* :class:`InstalledPlugins` — the persisted install ledger record
  (``.dadaia/states/installed_plugins.json``: ``{"schema_version": "1", "plugins": [...]}``),
  the direct analog of ``HarnessProfile``.

**No I/O here (A-seam, v0.1.60).** This module mirrors the discipline of
``core/models/harness_profile.py`` — frozen dataclasses with zero filesystem or ``json``
coupling. Descriptor reading and ledger serialisation live in ``infrastructure`` (the
``dadaia plugin`` CLI reads staged/packaged ``pack.json`` bytes; the JSON ledger adapter is
``infrastructure/json_plugin_store.py``). Keeping ``json``/``pathlib`` out is a deliberate
ports-and-adapters precedent, not a lint catch (``core-no-os-primitives`` does not ban them).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

#: The current on-disk schema version of both ``pack.json`` and ``installed_plugins.json``.
CURRENT_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class PluginPack:
    """An immutable, parsed plugin-pack descriptor.

    Attributes:
        name: the pack identifier (e.g. ``"frontend-design"``).
        agents: the core-stub agent names this pack replaces with real bodies.
        skills: the skill slugs the pack ships (may be empty).
        rules: the rule slugs the pack ships (may be empty).
        schema_version: the on-disk descriptor schema version (``"1"`` today).
    """

    name: str
    agents: tuple[str, ...]
    skills: tuple[str, ...]
    rules: tuple[str, ...]
    schema_version: str

    @classmethod
    def of(
        cls,
        name: str,
        agents: tuple[str, ...],
        skills: tuple[str, ...] = (),
        rules: tuple[str, ...] = (),
    ) -> PluginPack:
        """Build a pack at :data:`CURRENT_SCHEMA_VERSION`."""
        return cls(
            name=name,
            agents=agents,
            skills=skills,
            rules=rules,
            schema_version=CURRENT_SCHEMA_VERSION,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> PluginPack:
        """Parse + validate a ``pack.json`` descriptor mapping. Pure — no I/O.

        Raises:
            ValueError: when the descriptor is malformed — a missing/empty ``name``,
                no declared ``agents``, or a non-string entry in any of the string-list
                fields. A pack with zero agents is meaningless (it replaces no stub), so it
                is rejected rather than silently accepted.
        """
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("plugin pack descriptor requires a non-empty 'name'")

        def _str_tuple(key: str) -> tuple[str, ...]:
            raw = data.get(key, [])
            if not isinstance(raw, list) or not all(isinstance(entry, str) for entry in raw):
                raise ValueError(f"plugin pack '{name}' field '{key}' must be a list of strings")
            return tuple(raw)

        agents = _str_tuple("agents")
        if not agents:
            raise ValueError(f"plugin pack '{name}' must declare at least one agent")

        version = data.get("schema_version")
        return cls(
            name=name,
            agents=agents,
            skills=_str_tuple("skills"),
            rules=_str_tuple("rules"),
            schema_version=str(version) if version is not None else CURRENT_SCHEMA_VERSION,
        )


@dataclass(frozen=True)
class InstalledPlugins:
    """An immutable record of the plugin packs enabled in a workspace.

    The direct analog of ``HarnessProfile`` — the shape the JSON adapter serialises to
    ``.dadaia/states/installed_plugins.json``. An absent file means "no packs installed"
    (every consumer treats ``None`` as the empty ledger).

    Attributes:
        schema_version: the on-disk schema version (``"1"`` today).
        plugins: the enabled pack names, insertion-ordered, deduplicated.
    """

    schema_version: str
    plugins: tuple[str, ...]

    @classmethod
    def of(cls, plugins: tuple[str, ...]) -> InstalledPlugins:
        """Build a ledger at :data:`CURRENT_SCHEMA_VERSION` for *plugins*."""
        return cls(schema_version=CURRENT_SCHEMA_VERSION, plugins=plugins)

    @classmethod
    def empty(cls) -> InstalledPlugins:
        """The empty ledger — the canonical starting point for a fresh workspace."""
        return cls(schema_version=CURRENT_SCHEMA_VERSION, plugins=())

    def with_added(self, name: str) -> InstalledPlugins:
        """Return a ledger with *name* enabled — idempotent (a re-install adds nothing)."""
        if name in self.plugins:
            return self
        return InstalledPlugins(schema_version=self.schema_version, plugins=(*self.plugins, name))

    def with_removed(self, name: str) -> InstalledPlugins:
        """Return a ledger with *name* disabled — the pure inverse of :meth:`with_added`.

        Idempotent: removing an absent name returns ``self`` (v0.1.63 FR2). Remaining
        entries keep their insertion order and the schema version is preserved.
        """
        if name not in self.plugins:
            return self
        return InstalledPlugins(
            schema_version=self.schema_version,
            plugins=tuple(entry for entry in self.plugins if entry != name),
        )
