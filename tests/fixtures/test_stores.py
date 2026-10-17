"""`fake_venv` builds the venv layout of the platform it is told, and the `python` in it runs."""

import sys
from pathlib import Path

import pytest
import typer

from dadaia_workspace.core.platform import PLATFORM, Capabilities
from tests.fixtures.stores import fake_venv
from tests.helpers.oslib import run as os_run


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
    ran = os_run([str(python), "-c", "print(6 * 7)"])
    assert ran.stdout.strip() == "42"


def test_fake_venv_cli_is_the_installers_launcher_and_starts_without_a_shell(
    tmp_path: Path,
) -> None:
    fake_venv(tmp_path, cli=True)
    cli = (
        tmp_path / ".dadaia/.venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    )
    ran = os_run([str(cli), "--help"])
    assert ran.returncode == 0
    assert "Usage" in ran.stdout


def test_fake_venv_cli_source_is_started_as_a_launcher(tmp_path: Path) -> None:
    fake_venv(tmp_path, cli="#!python\nimport sys\nprint('hi', *sys.argv[1:])\n")
    cli = (
        tmp_path / ".dadaia/.venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    )
    ran = os_run([str(cli), "a"])
    assert ran.stdout.strip() == "hi a"


@pytest.mark.parametrize("name", ["ws", "a workspace"])
def test_fake_venv_cli_entrypoint_is_bound_to_the_venv_python_at_any_path(
    tmp_path: Path, name: str
) -> None:
    root = tmp_path / name
    root.mkdir()
    python = fake_venv(root, cli="#!python\nimport sys\nprint(sys.executable)\n")
    cli = python.with_name(f"dadaia{PLATFORM.venv_exe_suffix}")
    ran = os_run([str(cli)])
    assert ran.stdout.strip() == str(python)


def test_fake_venv_pth_puts_the_running_packages_on_the_venv_python(tmp_path: Path) -> None:
    python = fake_venv(tmp_path, pth=True)
    code = "import typer; print(typer.__file__)"
    ran = os_run([str(python), "-c", code])
    assert Path(ran.stdout.strip()) == Path(typer.__file__)
    bare = os_run([str(fake_venv(tmp_path / "bare")), "-c", code])
    assert bare.returncode != 0


def test_fake_venv_copies_the_base_interpreter_not_the_running_venvs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decoy = tmp_path / "decoy-python"
    decoy.write_bytes(b"not the base interpreter")
    monkeypatch.setattr("sys.executable", str(decoy))
    root = tmp_path / "ws"
    python = fake_venv(root)
    base = Path(sys._base_executable).resolve()
    assert python.read_bytes() == base.read_bytes()
    cfg = (root / ".dadaia" / ".venv" / "pyvenv.cfg").read_text()
    assert cfg == f"home = {base.parent}\n"
