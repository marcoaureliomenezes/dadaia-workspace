"""The real context registry in a tmp states dir — the store every non-CLI test uses."""

import sys
from pathlib import Path

from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore


def context_store(states_dir: Path) -> JsonContextStore:
    """``JsonContextStore`` over *states_dir*, created as ``init`` creates it."""
    states_dir.mkdir(parents=True, exist_ok=True)
    return JsonContextStore(states_dir)


def own_venv_workspace(root: Path) -> Path:
    """A registry plus a venv whose `python` is this interpreter and whose `dadaia` drains
    the pre-push pipe: a process on that `python` is owned by *root* (no install)."""
    tools = root / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    tools.mkdir(parents=True)
    (root / ".dadaia" / "states").mkdir()
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": []}')
    own_venv_python(root).symlink_to(Path(sys.executable).resolve())
    (root / ".dadaia" / ".venv" / "pyvenv.cfg").write_text(
        f"home = {Path(sys.executable).resolve().parent}\n"
    )
    (tools / f"dadaia{PLATFORM.venv_exe_suffix}").write_text("#!/bin/sh\ncat >/dev/null\n")
    (tools / f"dadaia{PLATFORM.venv_exe_suffix}").chmod(0o755)
    return root


def own_venv_python(root: Path) -> Path:
    return (
        root / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir / f"python{PLATFORM.venv_exe_suffix}"
    )
