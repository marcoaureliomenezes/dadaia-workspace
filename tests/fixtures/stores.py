"""The real context registry in a tmp states dir — the store every non-CLI test uses."""

from pathlib import Path

from dadaia_workspace.infrastructure.json_context_store import JsonContextStore


def context_store(states_dir: Path) -> JsonContextStore:
    """``JsonContextStore`` over *states_dir*, created as ``init`` creates it."""
    states_dir.mkdir(parents=True, exist_ok=True)
    return JsonContextStore(states_dir)
