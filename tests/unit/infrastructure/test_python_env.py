"""VenvPythonEnvironmentManager — venv bootstrap installs the package (VENV-1 coherence).

Bug init-venv-never-installs-dadaia-workspace: ``ensure_workspace_venv`` used to create a
bare venv and bail when the dir existed, so ``.dadaia/.venv/bin/dadaia`` never existed and
doctor VENV-1 was unfixable by its own remediation (re-running init).

The suite-wide conftest backstop no-ops ``ensure_workspace_venv`` (no real venvs in
tests), so the REAL method is captured at import time — before the autouse monkeypatch
fires — and exercised here with ``subprocess.run`` stubbed (child-venv creation is
subprocess-based — see bug init-venv-bootstrap-inherits-degraded-base-python below).
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

    def fake_run(cmd: list[str], check: bool = False, **_kwargs: object) -> None:
        rec.commands.append(list(cmd))
        if len(cmd) >= 3 and cmd[1] == "-m" and cmd[2] == "venv":
            rec.venv_created.append(cmd[-1])
            (Path(cmd[-1]) / PLATFORM.venv_scripts_dir).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(python_env_module.subprocess, "run", fake_run)
    # Interpreter resolution and the post-creation version post-condition are covered
    # by their own dedicated unit tests below; no-op them here so these generic
    # bootstrap-flow tests stay focused on the install/repair behavior they exercise.
    monkeypatch.setattr(
        VenvPythonEnvironmentManager,
        "_resolve_child_venv_interpreter",
        lambda self: "fake-interpreter",
    )
    monkeypatch.setattr(
        VenvPythonEnvironmentManager,
        "_assert_child_interpreter_version",
        lambda self, workspace_root: None,
    )
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
    # Three commands: the venv-creation subprocess, the provider spec install, then the
    # CI toolchain (pytest) the product promises for `ci preflight` and the executed-test
    # close gate.
    assert len(recorder.commands) == 3
    create_cmd = recorder.commands[0]
    assert create_cmd[0] == "fake-interpreter"
    assert create_cmd[1:3] == ["-m", "venv"]
    assert create_cmd[-1] == str(tmp_path / ".dadaia" / ".venv")
    assert recorder.commands[2][-1] == "pytest"
    cmd = recorder.commands[1]
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

    command = recorder.commands[1]
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
    """The Consumer-consumer scenario: installed 0.X.Y is not on the index → repack + install."""
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

    assert calls[0][1:3] == ["-m", "venv"]  # venv-creation subprocess call, first
    assert calls[1][-1] == "dadaia-workspace==9.9.9"
    assert calls[2][-1] == str(repacked)
    assert calls[3][-1] == "pytest"  # CI toolchain rides along on the fallback path too


def test_bootstrap_error_names_escape_hatch_when_repack_also_unavailable(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess as _subprocess

    # Pre-existing bare venv (doctor VENV-1 repair shape): isolates this test to the
    # install/repack-failure path under test, independent of venv-creation/interpreter
    # resolution (each covered by their own dedicated tests).
    (tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir).mkdir(parents=True)

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


# ── bug init-succeeds-after-provider-bootstrap-failure (Consumer live canary) ─────────
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


def test_venv_create_spawn_oserror_becomes_clean_bootstrap_error_not_raw_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug r3b-portability-import-venv-permission (Consumer R3-B, F-16/F-22 class).

    ``dadaia import`` restored a workspace onto a **noexec** filesystem: venv creation
    got far enough to write ``bin/python3.13`` and then died in ``ensurepip`` because
    that interpreter cannot be EXECUTED there. Exercised here at the level where the
    RESOLVED interpreter itself cannot even be spawned (``subprocess.run`` raising
    ``OSError`` directly) — a ~40-line raw Python traceback must never reach the
    operator; every such failure becomes one clean, actionable
    ``WorkspaceVenvBootstrapError`` line naming the path and the likely cause.
    """
    monkeypatch.setattr(
        VenvPythonEnvironmentManager, "ensure_workspace_venv", _REAL_ENSURE, raising=True
    )
    monkeypatch.setattr(
        VenvPythonEnvironmentManager,
        "_resolve_child_venv_interpreter",
        lambda self: "/nonexistent/python3.12",
    )

    def exploding_run(cmd: list[str], check: bool = False, **_kwargs: object) -> None:
        raise PermissionError(
            13, "Permission denied", f"{cmd[-1]}/bin/python{PLATFORM.venv_exe_suffix or '3.13'}"
        )

    monkeypatch.setattr(python_env_module.subprocess, "run", exploding_run)
    mgr = VenvPythonEnvironmentManager()

    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError) as excinfo:
        mgr.ensure_workspace_venv(str(tmp_path))

    message = str(excinfo.value)
    # Actionable: names the venv path AND the noexec/permission cause.
    assert str(tmp_path) in message
    assert "noexec" in message.lower()
    # It is a DadaiaError, so the CLI entrypoint renders it as one line, never a traceback.
    from dadaia_workspace.core.exceptions import DadaiaError

    assert isinstance(excinfo.value, DadaiaError)


def test_venv_create_subprocess_failure_becomes_clean_bootstrap_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The realistic shape of the noexec bug under subprocess-based creation: the
    RESOLVED interpreter spawns fine (it lives outside the noexec mount) but venv's
    internal ensurepip step fails EXECUTING the freshly-copied interpreter inside the
    noexec-mounted target dir — surfacing to us as ``CalledProcessError``, not
    ``OSError``. Must still become one clean, actionable line.
    """
    monkeypatch.setattr(
        VenvPythonEnvironmentManager, "ensure_workspace_venv", _REAL_ENSURE, raising=True
    )
    monkeypatch.setattr(
        VenvPythonEnvironmentManager,
        "_resolve_child_venv_interpreter",
        lambda self: "/usr/bin/python3.12",
    )

    def failing_creation(cmd: list[str], check: bool = False, **_kwargs: object) -> None:
        import subprocess as _subprocess

        raise _subprocess.CalledProcessError(
            1, cmd, output="", stderr="PermissionError: [Errno 13] Permission denied"
        )

    monkeypatch.setattr(python_env_module.subprocess, "run", failing_creation)
    mgr = VenvPythonEnvironmentManager()

    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError) as excinfo:
        mgr.ensure_workspace_venv(str(tmp_path))

    message = str(excinfo.value)
    assert str(tmp_path) in message
    assert "noexec" in message.lower()


def test_venv_create_success_path_is_unchanged(tmp_path: Path, recorder: _Recorder) -> None:
    """Guard against over-catching: a normal bootstrap still creates and installs."""
    mgr = VenvPythonEnvironmentManager()
    mgr.ensure_workspace_venv(str(tmp_path))
    assert recorder.venv_created == [str(tmp_path / ".dadaia" / ".venv")]


# ── bug init-venv-bootstrap-inherits-degraded-base-python ────────────────────────────
#
# Size: SMALL — pure-function unit tests plus instance-method tests with subprocess and
# ``sys``/PATH lookups stubbed. Intent: prove the child-venv interpreter resolution
# ACTUALLY checks each candidate's own reported version against Requires-Python, in the
# declared order, rather than trusting stdlib ``venv.create()``'s implicit (and, on a
# ``--copies`` venv, provably degraded — see repro below) base-executable resolution.
#
# Root cause: ``venv.create()`` resolves a NEW venv's base interpreter through
# ``sys._base_executable`` of the CALLING process. On a venv created with
# ``symlinks=False`` ("--copies"), CPython's getpath.c re-derives that value via a
# landmark search for the OS-level *unversioned* ``python3`` name inside the recorded
# ``home`` directory — NOT the version-pinned ``executable`` pyvenv.cfg itself records.
# Reproduced on this exact host class: a `.dadaia/.venv` built with `--copies` reports
# `sys._base_executable == "/usr/bin/python3"`, an OS symlink to Python 3.10, while the
# venv's own `pyvenv.cfg` `executable` field correctly names `/usr/bin/python3.12` (the
# interpreter that actually built it) — and the running interpreter is itself 3.12.13.


def test_version_satisfies_accepts_version_within_bounds() -> None:
    assert python_env_module._version_satisfies((3, 12, 3), ">=3.12,<4.0") is True


def test_version_satisfies_rejects_version_below_floor() -> None:
    assert python_env_module._version_satisfies((3, 10, 12), ">=3.12,<4.0") is False


def test_version_satisfies_rejects_version_at_or_above_ceiling() -> None:
    assert python_env_module._version_satisfies((4, 0, 0), ">=3.12,<4.0") is False


def test_version_satisfies_fails_open_on_empty_or_missing_spec() -> None:
    assert python_env_module._version_satisfies((3, 1, 0), "") is True
    assert python_env_module._version_satisfies((3, 1, 0), None) is True


def test_resolve_child_venv_interpreter_skips_degraded_base_and_uses_pyvenv_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """THE reproduction: ``sys._base_executable`` reports an interpreter whose version
    does NOT satisfy Requires-Python (the ``--copies`` degraded-base symptom on this
    exact host class), while the running venv's OWN ``pyvenv.cfg`` ``executable`` field
    names one that does. Resolution must skip the degraded candidate and select the
    compliant one — never hand the degraded resolution to venv creation implicitly.
    """
    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_running_requires_python", lambda: ">=3.12,<4.0")
    monkeypatch.setattr(
        python_env_module.sys, "_base_executable", "/usr/bin/python3", raising=False
    )
    monkeypatch.setattr(
        python_env_module, "_current_venv_pyvenv_executable", lambda: "/usr/bin/python3.12"
    )
    monkeypatch.setattr(python_env_module, "_path_candidates", lambda min_minor: [])

    versions = {
        "/usr/bin/python3": (3, 10, 12),  # the degraded OS-level unversioned python3
        "/usr/bin/python3.12": (3, 12, 13),  # the venv's own pyvenv.cfg-recorded truth
    }
    monkeypatch.setattr(python_env_module, "_interpreter_version", lambda exe: versions.get(exe))

    interpreter = mgr._resolve_child_venv_interpreter()

    assert interpreter == "/usr/bin/python3.12"


def test_resolve_child_venv_interpreter_falls_back_to_path_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Neither ``_base_executable`` nor the current ``pyvenv.cfg`` satisfy: PATH search
    for a version-pinned pythonX.Y is the last resolution strategy before giving up.
    """
    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_running_requires_python", lambda: ">=3.12,<4.0")
    monkeypatch.setattr(
        python_env_module.sys, "_base_executable", "/usr/bin/python3", raising=False
    )
    monkeypatch.setattr(python_env_module, "_current_venv_pyvenv_executable", lambda: None)
    monkeypatch.setattr(
        python_env_module, "_path_candidates", lambda min_minor: ["/usr/local/bin/python3.13"]
    )
    versions = {
        "/usr/bin/python3": (3, 10, 12),
        "/usr/local/bin/python3.13": (3, 13, 1),
    }
    monkeypatch.setattr(python_env_module, "_interpreter_version", lambda exe: versions.get(exe))

    assert mgr._resolve_child_venv_interpreter() == "/usr/local/bin/python3.13"


def test_resolve_child_venv_interpreter_raises_actionable_error_when_nothing_satisfies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_running_requires_python", lambda: ">=3.12,<4.0")
    monkeypatch.setattr(
        python_env_module.sys, "_base_executable", "/usr/bin/python3", raising=False
    )
    monkeypatch.setattr(python_env_module, "_current_venv_pyvenv_executable", lambda: None)
    monkeypatch.setattr(python_env_module, "_path_candidates", lambda min_minor: [])
    monkeypatch.setattr(python_env_module, "_interpreter_version", lambda exe: (3, 10, 12))

    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError) as excinfo:
        mgr._resolve_child_venv_interpreter()

    message = str(excinfo.value)
    assert "3.12" in message  # names the required version
    assert "/usr/bin/python3" in message  # names what was actually tried


def test_assert_child_interpreter_version_rejects_mismatched_child_before_pip_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The post-condition (fix direction point 3): a venv whose OWN python does not
    satisfy Requires-Python must be rejected with an ACTIONABLE 'interpreter mismatch'
    error naming both versions — BEFORE any pip install is attempted (never pip's bare,
    rootless 'requires a different Python' failure).
    """
    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_running_requires_python", lambda: ">=3.12,<4.0")
    monkeypatch.setattr(python_env_module, "_interpreter_version", lambda exe: (3, 10, 12))

    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError) as excinfo:
        mgr._assert_child_interpreter_version(str(tmp_path))

    message = str(excinfo.value)
    assert "3.10.12" in message
    assert ">=3.12,<4.0" in message
    assert "interpreter mismatch" in message.lower()


def test_assert_child_interpreter_version_accepts_compliant_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_running_requires_python", lambda: ">=3.12,<4.0")
    monkeypatch.setattr(python_env_module, "_interpreter_version", lambda exe: (3, 12, 13))

    mgr._assert_child_interpreter_version(str(tmp_path))  # must not raise


def test_assert_child_interpreter_version_fails_open_when_unintrospectable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cannot determine the child's version (e.g. subprocess stubbed out in a caller's
    own test double) → skip the gate; pip install remains the final authority.
    """
    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_running_requires_python", lambda: ">=3.12,<4.0")
    monkeypatch.setattr(python_env_module, "_interpreter_version", lambda exe: None)

    mgr._assert_child_interpreter_version(str(tmp_path))  # must not raise


def test_fresh_bootstrap_uses_resolved_interpreter_for_venv_creation(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wire-up: ``ensure_workspace_venv`` must use the RESOLVED interpreter (never an
    implicit ``venv.create()``) to spawn the child-venv creation.
    """
    monkeypatch.setattr(
        VenvPythonEnvironmentManager,
        "_resolve_child_venv_interpreter",
        lambda self: "/opt/python3.12",
    )
    mgr = VenvPythonEnvironmentManager()
    mgr.ensure_workspace_venv(str(tmp_path))

    create_cmd = recorder.commands[0]
    assert create_cmd[0] == "/opt/python3.12"
    assert create_cmd[1:3] == ["-m", "venv"]
    assert create_cmd[-1] == str(tmp_path / ".dadaia" / ".venv")
