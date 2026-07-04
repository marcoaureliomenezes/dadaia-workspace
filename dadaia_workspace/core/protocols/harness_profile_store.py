"""HarnessProfileStore protocol — read/write the persisted harness profile.

The ``core.protocols`` port for ``.dadaia/states/harness_profile.json`` persistence,
mirroring the ``ContextStore`` precedent. The concrete adapter is
``infrastructure/json_harness_profile_store.py`` (JSON on disk); consumers depend on this
Protocol, never on the adapter directly (the ``features-no-infrastructure`` layering law).

Read semantics: ``read`` returns ``None`` when the profile file is absent — a pre-v0.1.58
workspace has no profile, and the convention is that an absent profile is treated as the
full all-four install set (back-compat) by every consumer (``public_assets`` install/doctor,
v0.1.58 W3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.models.harness_profile import HarnessProfile


class HarnessProfileStore(Protocol):
    def read(self, states_dir: Path) -> HarnessProfile | None:
        """Return the persisted profile under *states_dir*, or ``None`` when absent."""
        ...

    def write(self, states_dir: Path, profile: HarnessProfile) -> None:
        """Persist *profile* under *states_dir*, idempotently (no spurious rewrite)."""
        ...
