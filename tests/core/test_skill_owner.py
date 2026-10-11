"""skill-owner-loader#identity: one core loader gives each skill-script owner one module
identity, resolved from its absolute path, so no cwd file shadows it and no bytecode lands.

size: SMALL — in-process identity checks; four short subprocesses for the isolation cases.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import dadaia_workspace

_PKG = Path(dadaia_workspace.__file__).resolve().parent
_ROOT = _PKG.parent


def _run(code: str, cwd: Path, *flags: str, path: str = "") -> subprocess.CompletedProcess[str]:
    """A fresh interpreter: stdlib plus the given package parent on sys.path, cwd elsewhere."""
    prologue = f"import sys; sys.path[1:] = [p for p in sys.path if p.startswith(sys.base_prefix)]; sys.path.append({path!r})\n"
    return subprocess.run(
        [sys.executable, "-I", *flags, "-c", prologue + code],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_load_owner_returns_one_module_object_per_owner():
    from dadaia_workspace.core.skill_owner import load_owner

    assert load_owner("dd-bug-resolution", "_ledger") is load_owner("dd-bug-resolution", "_ledger")


def test_package_and_sibling_import_share_one_module_and_exception_class():
    from dadaia_workspace.core.skill_owner import load_owner

    owner = load_owner("dd-bug-resolution", "_ledger")
    import _ledger  # type: ignore[import-not-found]  # noqa: PLC0415  (the sibling spelling)

    assert owner is sys.modules["_ledger"]
    assert owner.LineError is _ledger.LineError


def test_loads_with_cwd_elsewhere_and_only_stdlib_on_sys_path(tmp_path):
    done = _run(
        "from dadaia_workspace.core.skill_owner import load_owner\n"
        "print(load_owner('dd-release-implementation', '_release_schema').__name__)",
        tmp_path,
        path=str(_ROOT),
    )
    assert (done.returncode, done.stdout.strip()) == (0, "_release_schema"), done.stderr


def test_a_ledger_py_planted_in_the_cwd_is_never_loaded(tmp_path):
    (tmp_path / "_ledger.py").write_text("PLANTED = True\n", encoding="utf-8")
    done = _run(
        "sys.path.insert(0, '')\n"
        "from dadaia_workspace.core.skill_owner import load_owner\n"
        "m = load_owner('dd-bug-resolution', '_ledger')\n"
        "print(m.__file__, hasattr(m, 'PLANTED'))",
        tmp_path,
        "-B",
        path=str(_ROOT),
    )
    kernel = _PKG / "public" / "skills" / "dd-bug-resolution" / "scripts" / "_ledger.py"
    assert (done.returncode, done.stdout.strip()) == (0, f"{kernel} False"), done.stderr


def test_loading_owners_writes_no_pycache_into_the_skills_tree(tmp_path):
    copy = tmp_path / "copy"
    shutil.copytree(_PKG, copy / "dadaia_workspace", ignore=shutil.ignore_patterns("__pycache__"))
    skills = copy / "dadaia_workspace" / "public" / "skills"
    done = _run(
        "from pathlib import Path\n"
        "from dadaia_workspace.core.skill_owner import load_owner\n"
        f"for p in sorted(Path({str(skills)!r}).glob('*/scripts/_*.py')):\n"
        "    if p.parent.parent.name in ('dd-bug-resolution', 'dd-release-implementation'):\n"
        "        load_owner(p.parent.parent.name, p.stem)\n",
        tmp_path,
        path=str(copy),
    )
    assert done.returncode == 0, done.stderr
    assert sorted(skills.rglob("__pycache__")) == []
