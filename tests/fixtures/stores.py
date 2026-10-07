"""The real context registry in a tmp states dir — the store every non-CLI test uses."""

import json
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
    own_venv_python(root).symlink_to(Path(sys.executable).resolve())
    (root / ".dadaia" / ".venv" / "pyvenv.cfg").write_text(
        f"home = {Path(sys.executable).resolve().parent}\n"
    )
    cli = f"dadaia{PLATFORM.venv_exe_suffix}"
    shutil.copy2(Path(sys.executable).parent / cli, tools / cli)
    return root


def workspace_cli(root: Path, *listed: dict[str, object]) -> Path:
    """A POSIX `dadaia` stub in *root*'s venv (a text script: Windows runs none), standing for
    the reads the worktree script makes: `context list` prints *listed*, `reports validate` passes iff `schema_version`,
    `doctor --specs-dir S` prints where it ran and fails iff `S/RED-doctor` exists; any other verb drains its stdin
    (the pre-push pipe)."""
    cli = root / ".dadaia" / ".venv" / "bin" / "dadaia"
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text(_CLI.format(python=sys.executable, rows=json.dumps(list(listed))))
    cli.chmod(0o755)
    return root


_CLI = """#!{python}
import json, sys
args = sys.argv[1:]
if args[:2] == ["context", "list"]:
    print({rows!r})
elif args[:2] == ["reports", "validate"]:
    sys.exit(0 if "schema_version" in json.load(open(args[2])) else 1)
elif args[:1] == ["doctor"]:
    import os
    specs = args[args.index("--specs-dir") + 1]
    print("doctor --specs-dir " + specs, "fenced " + os.environ.get("DADAIA_FENCED_ROOTS", ""),
          "cwd " + os.getcwd(), sep="\\n")
    sys.exit(os.path.exists(os.path.join(specs, "RED-doctor")))
else:
    sys.stdin.read()
"""


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
