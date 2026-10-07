"""The real context registry in a tmp states dir — the store every non-CLI test uses."""

import shutil
import sys
import tempfile
from pathlib import Path

from pip._vendor.distlib.scripts import ScriptMaker

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
    fake_venv(root, cli=True)
    return root


def own_venv_python(root: Path) -> Path:
    return (
        root / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir / f"python{PLATFORM.venv_exe_suffix}"
    )


def fake_venv(root: Path, cli: bool | str = False) -> Path:
    """`root/.dadaia/.venv` with a `python` that runs: the interpreter copied (no symlink: Windows
    needs a privilege for one) under its real name, `python` plus `PLATFORM`'s exe suffix, in
    `PLATFORM`'s scripts dir, and a `pyvenv.cfg` naming its home. With *cli*, this environment's own `dadaia` console script is
    copied beside it: the installer's launcher (an `.exe` on Windows, never a shebang text file).
    With *cli* a source text, that script (its first line `#!python`) is wrapped as pip wraps a
    console script: a launcher `.exe` on Windows, an executable shebang script elsewhere.
    Returns that `python`."""
    python = own_venv_python(root)
    python.parent.mkdir(parents=True, exist_ok=True)
    real = Path(sys.executable).resolve()
    shutil.copy2(real, python)
    (root / ".dadaia" / ".venv" / "pyvenv.cfg").write_text(f"home = {real.parent}\n")
    name = f"dadaia{PLATFORM.venv_exe_suffix}"
    if isinstance(cli, str):
        with tempfile.TemporaryDirectory() as src:
            (Path(src) / "dadaia").write_text(cli)
            maker = ScriptMaker(src, str(python.parent), add_launchers=True)
            maker.clobber = True  # a re-placed stub replaces the older one
            maker.make(str(Path(src) / "dadaia"))
    elif cli:
        shutil.copy2(Path(sys.executable).parent / name, python.with_name(name))
    return python
