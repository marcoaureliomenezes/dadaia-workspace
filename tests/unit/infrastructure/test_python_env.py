"""VenvPythonEnvironmentManager — venv bootstrap installs the package (VENV-1 coherence).

Bug init-venv-never-installs-dadaia-workspace: ``ensure_workspace_venv`` used to create a
bare venv and bail when the dir existed, so ``.dadaia/.venv/bin/dadaia`` never existed and
doctor VENV-1 was unfixable by its own remediation (re-running init).

The suite-wide conftest backstop no-ops ``ensure_workspace_venv`` (no real venvs in
tests), so the REAL method is captured at import time — before the autouse monkeypatch
fires — and exercised here with ``venv.create``/``subprocess.run`` stubbed.
"""

from pathlib import Path

import pytest

import dadaia_workspace.infrastructure.python_env as python_env_module
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

# Captured at collection/import time — the conftest autouse monkeypatch only applies
# while a test runs, so this is the unpatched production method.
_REAL_ENSURE = VenvPythonEnvironmentManager.ensure_workspace_venv


class _Recorder:
    def __init__(self) -> None:
        self.venv_created: list[str] = []
        self.commands: list[list[str]] = []


@pytest.fixture()
def recorder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _Recorder:
    rec = _Recorder()

    def fake_venv_create(path: str, with_pip: bool = False) -> None:
        rec.venv_created.append(path)
        (Path(path) / PLATFORM.venv_scripts_dir).mkdir(parents=True, exist_ok=True)

    def fake_run(cmd: list[str], check: bool = False) -> None:
        rec.commands.append(list(cmd))

    monkeypatch.setattr(python_env_module.venv, "create", fake_venv_create)
    monkeypatch.setattr(python_env_module.subprocess, "run", fake_run)
    # Undo the suite-wide no-op backstop for these tests only.
    monkeypatch.setattr(
        VenvPythonEnvironmentManager, "ensure_workspace_venv", _REAL_ENSURE, raising=True
    )
    return rec


def _entrypoint(ws: Path) -> Path:
    return (
        ws / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    )


def test_fresh_bootstrap_creates_venv_and_installs_package(
    tmp_path: Path, recorder: _Recorder
) -> None:
    mgr = VenvPythonEnvironmentManager()
    result = mgr.ensure_workspace_venv(str(tmp_path))

    assert result == str(tmp_path / ".dadaia" / ".venv")
    assert recorder.venv_created == [str(tmp_path / ".dadaia" / ".venv")]
    assert len(recorder.commands) == 1
    cmd = recorder.commands[0]
    assert cmd[0] == mgr.pip_executable(str(tmp_path))
    assert cmd[1] == "install"
    # Running from the source checkout in this repo → editable install of that checkout.
    assert "--editable" in cmd
    assert (Path(cmd[-1]) / "pyproject.toml").is_file()


def test_existing_bare_venv_is_repaired_not_skipped(tmp_path: Path, recorder: _Recorder) -> None:
    """The exact state doctor VENV-1 flags: venv dir present, entrypoint missing."""
    (tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir).mkdir(parents=True)

    VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path))

    assert recorder.venv_created == []  # no re-create
    assert len(recorder.commands) == 1  # but the package IS installed


def test_healthy_venv_is_a_noop(tmp_path: Path, recorder: _Recorder) -> None:
    entry = _entrypoint(tmp_path)
    entry.parent.mkdir(parents=True)
    entry.write_text("#!stub")

    VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path))

    assert recorder.venv_created == []
    assert recorder.commands == []


def test_install_spec_pins_version_when_not_a_source_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wheel-installed distribution (no pyproject.toml next to the package) → pinned pin."""
    site = tmp_path / "site-packages" / "dadaia_workspace"
    site.mkdir(parents=True)
    (site / "__init__.py").write_text("")
    monkeypatch.setattr(python_env_module.dadaia_workspace, "__file__", str(site / "__init__.py"))
    monkeypatch.setattr(python_env_module.metadata, "version", lambda name: "9.9.9")

    spec = VenvPythonEnvironmentManager()._install_spec()

    assert spec == "dadaia-workspace==9.9.9"


def test_local_candidate_wheel_overrides_index_pin_without_editable(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "dadaia_workspace-9.9.9-py3-none-any.whl"
    wheel.write_bytes(b"candidate")
    monkeypatch.setenv("DADAIA_BOOTSTRAP_PACKAGE", str(wheel))

    VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path / "workspace"))

    command = recorder.commands[0]
    assert command[-1] == str(wheel)
    assert "--editable" not in command


# ── repack-installed-wheel fallback (bug certify-cannot-install-installed-provider) ──
#
# A consumer whose installed provider version is NOT resolvable from the index (an
# unpublished candidate wheel under validation, a yanked release, or an offline host)
# must still bootstrap disposable venvs (init/certify/reconcile) from a REPRODUCIBLE
# source: the running installed distribution itself, re-packed as a wheel.


def _make_installed_dist(root: Path) -> Path:
    """Materialize a minimal REAL installed distribution layout (site-packages style)."""
    site = root / "site"
    (site / "fakepkg").mkdir(parents=True)
    (site / "fakepkg" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    dist_info = site / "fakepkg-0.1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: fakepkg\nVersion: 0.1.0\n", encoding="utf-8"
    )
    (dist_info / "WHEEL").write_text(
        "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        encoding="utf-8",
    )
    (dist_info / "RECORD").write_text(
        "fakepkg/__init__.py,,\n"
        "fakepkg-0.1.0.dist-info/METADATA,,\n"
        "fakepkg-0.1.0.dist-info/WHEEL,,\n"
        "fakepkg-0.1.0.dist-info/RECORD,,\n",
        encoding="utf-8",
    )
    return dist_info


def test_repack_installed_wheel_produces_a_valid_wheel(tmp_path: Path) -> None:
    import base64
    import hashlib
    import zipfile
    from importlib.metadata import Distribution

    from dadaia_workspace.infrastructure.python_env import repack_installed_wheel

    dist_info = _make_installed_dist(tmp_path)
    wheel = repack_installed_wheel(tmp_path / "out", dist=Distribution.at(dist_info))

    assert wheel is not None
    assert wheel.name == "fakepkg-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())
        assert "fakepkg/__init__.py" in names
        assert "fakepkg-0.1.0.dist-info/METADATA" in names
        assert "fakepkg-0.1.0.dist-info/WHEEL" in names
        record = zf.read("fakepkg-0.1.0.dist-info/RECORD").decode()
        # RECORD hashes are REGENERATED so pip's install-time verification passes.
        payload = zf.read("fakepkg/__init__.py")
        digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
        assert f"fakepkg/__init__.py,sha256={digest},{len(payload)}" in record
        assert "fakepkg-0.1.0.dist-info/RECORD,," in record


def test_repack_returns_none_for_editable_install(tmp_path: Path) -> None:
    """An editable/source install has no packaged payload — repack must decline, not lie."""
    from importlib.metadata import Distribution

    from dadaia_workspace.infrastructure.python_env import repack_installed_wheel

    dist_info = tmp_path / "site" / "fakepkg-0.1.0.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: fakepkg\nVersion: 0.1.0\n", encoding="utf-8"
    )
    (dist_info / "RECORD").write_text(
        "__editable__.fakepkg.pth,,\nfakepkg-0.1.0.dist-info/METADATA,,\n", encoding="utf-8"
    )
    (tmp_path / "site" / "__editable__.fakepkg.pth").write_text("/src\n", encoding="utf-8")

    assert repack_installed_wheel(tmp_path / "out", dist=Distribution.at(dist_info)) is None


def test_bootstrap_falls_back_to_repacked_wheel_when_index_cannot_resolve(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Hermes-consumer scenario: installed 0.X.Y is not on the index → repack + install."""
    import subprocess as _subprocess

    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_install_spec", lambda: "dadaia-workspace==9.9.9")
    repacked = tmp_path / "repacked" / "dadaia_workspace-9.9.9-py3-none-any.whl"
    repacked.parent.mkdir(parents=True)
    repacked.write_bytes(b"fake-wheel")
    monkeypatch.setattr(
        python_env_module, "repack_installed_wheel", lambda dest_dir, dist=None: repacked
    )

    calls: list[list[str]] = []

    def failing_then_ok(cmd: list[str], check: bool = False) -> None:
        calls.append(list(cmd))
        if cmd[-1] == "dadaia-workspace==9.9.9":
            raise _subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(python_env_module.subprocess, "run", failing_then_ok)

    mgr.ensure_workspace_venv(str(tmp_path))

    assert calls[0][-1] == "dadaia-workspace==9.9.9"
    assert calls[1][-1] == str(repacked)


def test_bootstrap_error_names_escape_hatch_when_repack_also_unavailable(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess as _subprocess

    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_install_spec", lambda: "dadaia-workspace==9.9.9")
    monkeypatch.setattr(
        python_env_module, "repack_installed_wheel", lambda dest_dir, dist=None: None
    )

    def always_fail(cmd: list[str], check: bool = False) -> None:
        raise _subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(python_env_module.subprocess, "run", always_fail)

    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError) as excinfo:
        mgr.ensure_workspace_venv(str(tmp_path))
    assert "DADAIA_BOOTSTRAP_PACKAGE" in str(excinfo.value)
