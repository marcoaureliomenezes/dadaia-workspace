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

    def fake_run(cmd: list[str], check: bool = False, **_kwargs: object) -> None:
        rec.commands.append(list(cmd))

    monkeypatch.setattr(python_env_module.venv, "create", fake_venv_create)
    monkeypatch.setattr(python_env_module.subprocess, "run", fake_run)
    # Post-bootstrap provider verification runs a REAL venv python — no-op it here;
    # its own behavior is covered by the dedicated verification tests below.
    monkeypatch.setattr(
        VenvPythonEnvironmentManager, "_verify_venv_provider", lambda self, ws, expected=None: None
    )
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
    # Two installs: the provider spec, then the CI toolchain (pytest) the product
    # promises for `ci preflight` and the executed-test close gate.
    assert len(recorder.commands) == 2
    assert recorder.commands[1][-1] == "pytest"
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
    assert len(recorder.commands) == 2  # package installed + CI toolchain (pytest)


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

    def failing_then_ok(cmd: list[str], check: bool = False, **_kwargs: object) -> None:
        calls.append(list(cmd))
        if cmd[-1] == "dadaia-workspace==9.9.9":
            raise _subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(python_env_module.subprocess, "run", failing_then_ok)

    mgr.ensure_workspace_venv(str(tmp_path))

    assert calls[0][-1] == "dadaia-workspace==9.9.9"
    assert calls[1][-1] == str(repacked)
    assert calls[2][-1] == "pytest"  # CI toolchain rides along on the fallback path too


def test_bootstrap_error_names_escape_hatch_when_repack_also_unavailable(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess as _subprocess

    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_install_spec", lambda: "dadaia-workspace==9.9.9")
    monkeypatch.setattr(
        python_env_module, "repack_installed_wheel", lambda dest_dir, dist=None: None
    )

    def always_fail(cmd: list[str], check: bool = False, **_kwargs: object) -> None:
        raise _subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(python_env_module.subprocess, "run", always_fail)

    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError) as excinfo:
        mgr.ensure_workspace_venv(str(tmp_path))
    assert "DADAIA_BOOTSTRAP_PACKAGE" in str(excinfo.value)


# ── bug init-succeeds-after-provider-bootstrap-failure (Hermes live canary) ─────────
#
# init used to leak pip's raw "ERROR: Could not find a version..." into its output while
# the repack fallback quietly saved the bootstrap — indistinguishable, for a consumer,
# from a masked incomplete bootstrap. The index install is now output-captured, the
# fallback announces itself in ONE clean line, and the bootstrap VERIFIES the venv's
# provider independently (clean env, exact running version) before reporting success.


def test_index_install_is_output_captured_and_fallback_announces_itself(
    tmp_path: Path,
    recorder: _Recorder,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import subprocess as _subprocess

    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_install_spec", lambda: "dadaia-workspace==9.9.9")
    repacked = tmp_path / "repacked" / "dadaia_workspace-9.9.9-py3-none-any.whl"
    repacked.parent.mkdir(parents=True)
    repacked.write_bytes(b"fake-wheel")
    monkeypatch.setattr(
        python_env_module, "repack_installed_wheel", lambda dest_dir, dist=None: repacked
    )

    captured_kwargs: list[dict[str, object]] = []

    def failing_then_ok(cmd: list[str], check: bool = False, **kwargs: object) -> None:
        captured_kwargs.append(dict(kwargs))
        if cmd[-1] == "dadaia-workspace==9.9.9":
            raise _subprocess.CalledProcessError(1, cmd, output="", stderr="ERROR: no dist")

    monkeypatch.setattr(python_env_module.subprocess, "run", failing_then_ok)

    mgr.ensure_workspace_venv(str(tmp_path))

    # pip's own stream is captured — its raw ERROR never leaks to the operator.
    assert captured_kwargs and all(k.get("capture_output") for k in captured_kwargs)
    out = capsys.readouterr().out
    assert "re-packed" in out  # one clean, honest fallback line replaces the noise


def test_verification_failure_fails_the_bootstrap(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_install_spec", lambda: "dadaia-workspace==9.9.9")

    def broken_verify(
        self: VenvPythonEnvironmentManager, ws: str, expected: str | None = None
    ) -> None:
        raise python_env_module.WorkspaceVenvBootstrapError("venv provider verification failed")

    monkeypatch.setattr(VenvPythonEnvironmentManager, "_verify_venv_provider", broken_verify)

    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError):
        mgr.ensure_workspace_venv(str(tmp_path))


def test_verify_venv_provider_uses_clean_env_and_checks_exact_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verification must not be satisfiable through inherited PYTHONPATH."""
    mgr = VenvPythonEnvironmentManager()
    seen: dict[str, object] = {}

    class _Proc:
        returncode = 0
        stdout = "9.9.8\n"
        stderr = ""

    def fake_run(cmd: list[str], **kwargs: object) -> _Proc:
        seen["cmd"] = cmd
        seen["env"] = kwargs.get("env")
        return _Proc()

    monkeypatch.setattr(python_env_module.subprocess, "run", fake_run)
    monkeypatch.setenv("PYTHONPATH", "/somewhere/inherited")

    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError) as excinfo:
        mgr._verify_venv_provider(str(tmp_path), expected="9.9.9")

    assert "9.9.8" in str(excinfo.value) and "9.9.9" in str(excinfo.value)
    env = seen["env"]
    assert isinstance(env, dict) and "PYTHONPATH" not in env
