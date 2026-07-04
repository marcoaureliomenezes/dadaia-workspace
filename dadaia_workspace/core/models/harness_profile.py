"""HarnessProfile domain model — the persisted harness-selection profile.

A pure, typed ``core`` value object recording which Layer-1 entry harnesses a workspace
was scaffolded for (``dadaia init --harness <set>``). It is the in-memory shape the
``infrastructure`` JSON adapter serialises to ``.dadaia/states/harness_profile.json`` and
that ``public_assets`` install/doctor scope on.

**No I/O here (A1 seam, v0.1.58).** This module mirrors the *discipline* of
``core/models/spec_context.py`` — a frozen dataclass with zero filesystem or ``json``
coupling. Serialisation lives in ``infrastructure/json_harness_profile_store.py``; the
init-time write is inlined in ``features/workspace/service.py`` (like the existing
``_init_json_file`` bootstrap). The ``core-no-os-primitives`` contract does not ban
``json``/``pathlib``, so keeping them out is a deliberate ports-and-adapters precedent,
not a lint catch.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The current on-disk schema version of ``harness_profile.json``.
CURRENT_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class HarnessProfile:
    """An immutable record of the harness set a workspace was scaffolded for.

    Attributes:
        schema_version: the on-disk schema version (``"1"`` today).
        harnesses: the selected Layer-1 entry harnesses, in canonical
            :data:`dadaia_workspace.core.harness_registry.L1_ENTRY_HARNESSES` order.
    """

    schema_version: str
    harnesses: tuple[str, ...]

    @classmethod
    def of(cls, harnesses: tuple[str, ...]) -> HarnessProfile:
        """Build a profile at :data:`CURRENT_SCHEMA_VERSION` for *harnesses*."""
        return cls(schema_version=CURRENT_SCHEMA_VERSION, harnesses=harnesses)
