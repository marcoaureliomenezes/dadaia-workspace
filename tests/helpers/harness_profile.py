"""Register the full harness roster in a test workspace's profile.

0.4.7 T-047-72: `install(target="all")` and `doctor()` scope on
`.dadaia/states/harness_profile.json` — the roster of record — and a workspace with
no profile migrates to the harness directories physically present (an empty tmp
workspace ⇒ nothing). A test that asserts the full multi-harness projection therefore
registers the roster first, exactly as `dadaia harness add` does.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore


def register_all(workspace: Path) -> None:
    """Persist every registered harness into *workspace*'s profile."""
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    JsonHarnessProfileStore().write(states, HarnessProfile.of(L1_ENTRY_HARNESSES))
