"""The real ``dadaia doctor`` output: the printer, not a synthetic render."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from tests.core.test_cli_line__fix_line_contract import the_fix
from tests.fixtures.stores import own_venv_python, own_venv_workspace

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_the_real_doctor_prints_every_fix_as_one_whole_runnable_line(tmp_path: Path) -> None:
    """The printer, not a synthetic render: a workspace finding (an expired tmp entry), an
    error-class specs finding (FIXED-1 on a symlinked QUALITY.md) and a ledger finding
    (a malformed BACKLOG.json), through a `dadaia doctor` subprocess at a 61-char root with
    COLUMNS unset: exit 1, and every `fix:` line is one whole line in one of the two fix forms."""
    import site

    from dadaia_workspace.features.specs import canon

    ws = own_venv_workspace(tmp_path / ("w" * max(1, 61 - len(str(tmp_path)))))  # 61-char root
    expired = ws / ".dadaia" / "tmp" / "agent" / "20200101"
    expired.mkdir(parents=True)
    os.utime(expired, (0, 0))
    specs = ws / "repos" / "demo" / "specs"
    canon.scaffold(specs, project_name="demo")
    outside = tmp_path / "outside.md"
    outside.write_text("# Quality\n", encoding="utf-8")
    (specs / "memory" / "QUALITY.md").unlink()
    (specs / "memory" / "QUALITY.md").symlink_to(outside)
    (specs / "backlog" / "BACKLOG.json").write_text("{}\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "COLUMNS"}
    env["PYTHONPATH"] = os.pathsep.join([str(_REPO_ROOT), *site.getsitepackages()])
    argv = [str(own_venv_python(ws)), "-m", "dadaia_workspace", "doctor", "--specs-dir", str(specs)]
    run = subprocess.run(argv, cwd=ws, env=env, capture_output=True, text=True, timeout=120)

    assert run.returncode == 1, run.stdout + run.stderr
    lines = run.stdout.splitlines()
    assert {"WS-tmp-expired", "FIXED-1", "LEDGER-BACKLOG-SCHEMA"} <= {
        line.split(" ", 1)[0] for line in lines
    }, run.stdout
    fixes = [line for line in lines if line.startswith("fix: ")]
    assert fixes, run.stdout
    for fix in fixes:  # two shapes, no third
        if the_fix(fix).startswith("Operator action: "):  # it names the file
            assert re.search(r"\s(/|\w:[\\/])\S", fix), fix
    # Whole lines: a wrapped fix would leave a continuation line that is neither a finding
    # (`CODE verdict …`) nor a `fix:` line.
    assert [ln for ln in lines if ln and not re.match(r"(fix: |[A-Z][A-Za-z0-9-]+ )", ln)] == []
