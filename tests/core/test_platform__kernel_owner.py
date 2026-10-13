"""``core.platform`` decides through the kernel's ``_platform``, loaded by path."""

import os
import subprocess
import sys
from pathlib import Path

import dadaia_workspace
from dadaia_workspace.core.platform import PLATFORM

_OWNER = (
    Path(dadaia_workspace.__file__).parent / "public/skills/dd-bug-resolution/scripts/_platform.py"
)


def test_a_planted_platform_module_in_the_cwd_never_stands_in_for_the_owner(tmp_path: Path) -> None:
    (tmp_path / "_platform.py").write_text("raise SystemExit('the cwd shadow was imported')\n")
    code = (
        "import sys\nimport dadaia_workspace.core.platform as p\n"
        "print(sys.modules['_platform'].__file__, p.PLATFORM.venv_scripts_dir)\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(dadaia_workspace.__file__).parents[1])},
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == [str(_OWNER), PLATFORM.venv_scripts_dir]
