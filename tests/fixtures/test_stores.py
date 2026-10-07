"""`fake_venv` builds the venv layout of the platform it is told, and the `python` in it runs."""

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import Capabilities
from tests.fixtures.stores import fake_venv


@pytest.mark.parametrize(
    ("platform", "relative"),
    [("linux", "bin/python"), ("darwin", "bin/python"), ("win32", "Scripts/python.exe")],
)
def test_fake_venv_lays_python_out_as_the_platform_does(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str, relative: str
) -> None:
    monkeypatch.setattr("tests.fixtures.stores.PLATFORM", Capabilities.detect(platform))
    python = fake_venv(tmp_path)
    assert python == tmp_path / ".dadaia" / ".venv" / relative
    assert python.is_file()
    assert not python.is_symlink()
    assert (tmp_path / ".dadaia" / ".venv" / "pyvenv.cfg").read_text().startswith("home = ")


def test_fake_venv_python_runs_on_this_platform(tmp_path: Path) -> None:
    python = fake_venv(tmp_path)
    run = subprocess.run([str(python), "-c", "print(6 * 7)"], capture_output=True, text=True)
    assert run.stdout.strip() == "42"
