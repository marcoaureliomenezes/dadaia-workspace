"""The symlink refusal's fix, run verbatim in the host shell, clears the refusal.

The refusal's one fix is
runnable on every supported OS: POSIX sh, Windows cmd). Size: SMALL (CliRunner + one shell
call).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.specs import canon
from tests.helpers.oslib import link, read_text, run_line, write_text

_OUTSIDE = (  # a valid atom: the only error left is the refused symlink
    "---\nslug: QUALITY\ntitle: Quality\ntldr: Quality.\nsummary: Quality.\ntags:\n  - quality\n---\n"
    "# Quality\n\noperator text, no fixed block\n"
)


@pytest.mark.medium
def test_the_symlink_refusal_fix_runs_verbatim_and_the_upgrade_then_lands(
    tmp_path: Path,
) -> None:
    specs = tmp_path / "repo" / "specs"
    canon.scaffold(specs, project_name="p")
    outside = tmp_path / "outside.md"
    write_text(outside, _OUTSIDE)
    quality = specs / "memory" / "QUALITY.md"
    quality.unlink()
    if not link(str(outside), quality, is_dir=False):
        pytest.skip("this host cannot create symlinks")

    refused = CliRunner().invoke(app, ["specs", "upgrade", "--specs-dir", str(specs)])
    assert refused.exit_code == 1, refused.output
    (fix,) = [ln[5:] for ln in refused.output.splitlines() if ln.startswith("fix: ")]
    done = run_line(fix, cwd=tmp_path)
    again = CliRunner().invoke(app, ["specs", "upgrade", "--specs-dir", str(specs)])

    assert done.returncode == 0
    assert not quality.is_symlink()
    assert again.exit_code == 0, again.output
    assert read_text(outside) == _OUTSIDE
    assert read_text(quality) != _OUTSIDE
