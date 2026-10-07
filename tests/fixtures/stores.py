"""The real context registry in a tmp states dir — the store every non-CLI test uses."""

import shutil
import sys
from pathlib import Path

from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore


def context_store(states_dir: Path) -> JsonContextStore:
    """``JsonContextStore`` over *states_dir*; an absent registry created as ``init`` creates it."""
    states_dir.mkdir(parents=True, exist_ok=True)
    registry = states_dir / "spec_contexts.json"
    if not registry.exists():
        registry.write_text('{"contexts": []}', encoding="utf-8")
    return JsonContextStore(states_dir)


def own_venv_workspace(root: Path) -> Path:
    """A registry plus a venv whose `python` and `dadaia` are this environment's own: a
    process on that `python` is owned by *root* (no install)."""
    tools = root / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    tools.mkdir(parents=True)
    (root / ".dadaia" / "states").mkdir()
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": []}')
    fake_venv(root)
    cli = f"dadaia{PLATFORM.venv_exe_suffix}"
    shutil.copy2(Path(sys.executable).parent / cli, tools / cli)
    return root


def own_venv_python(root: Path) -> Path:
    return (
        root / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir / f"python{PLATFORM.venv_exe_suffix}"
    )


def fake_venv(root: Path) -> Path:
    """`root/.dadaia/.venv` with a `python` that runs: the interpreter copied (no symlink: Windows
    needs a privilege for one) under its real name, `python` plus `PLATFORM`'s exe suffix, in
    `PLATFORM`'s scripts dir, and a `pyvenv.cfg` naming its home. Returns that `python`."""
    python = own_venv_python(root)
    python.parent.mkdir(parents=True, exist_ok=True)
    real = Path(sys.executable).resolve()
    shutil.copy2(real, python)
    (root / ".dadaia" / ".venv" / "pyvenv.cfg").write_text(f"home = {real.parent}\n")
    return python
