"""VenvPythonEnvironmentManager — the workspace venv bootstrap, over a faked subprocess.

bug init-venv-never-installs-dadaia-workspace (VENV-1 coherence);
bug init-venv-installs-index-version-not-running-distribution; bug
certify-cannot-install-installed-provider; bug init-succeeds-after-provider-bootstrap-failure;
bug init-venv-bootstrap-inherits-degraded-base-python; 0.4.8 AC1.6, AC2.1-AC2.3; v0.4.3 A9.1-A9.3.

The conftest backstop no-ops ``ensure_workspace_venv``; the real method is captured at
import time and restored by the ``recorder`` fixture.
"""

import base64
import hashlib
import subprocess
import zipfile
from importlib.metadata import Distribution
from pathlib import Path

import pytest

import dadaia_workspace.infrastructure.python_env as python_env_module
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.platform import PLATFORM, Capabilities
from dadaia_workspace.infrastructure.python_env import (
    VenvPythonEnvironmentManager,
    build_digest,
    repack_installed_wheel,
)
from tests.fixtures.provider_dist import install_fake_dist

_REAL_ENSURE = VenvPythonEnvironmentManager.ensure_workspace_venv


class _Recorder:
    def __init__(self) -> None:
        self.venv_created: list[str] = []
        self.commands: list[list[str]] = []
        self.installed: str | None = None  # the fake venv's reported "<version> <build>"


@pytest.fixture()
def recorder(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    """Fake ``subprocess.run`` plus the interpreter/verification probes, which have
    their own tests below."""
    rec = _Recorder()

    def fake_run(cmd: list[str], check: bool = False, **_kwargs: object) -> None:
        rec.commands.append(list(cmd))
        if cmd[1:3] == ["-m", "venv"]:
            rec.venv_created.append(cmd[-1])
            (Path(cmd[-1]) / PLATFORM.venv_scripts_dir).mkdir(parents=True, exist_ok=True)

    cls = VenvPythonEnvironmentManager
    monkeypatch.setattr(python_env_module.subprocess, "run", fake_run)
    monkeypatch.setattr(cls, "_resolve_child_venv_interpreter", lambda self: "fake-interpreter")
    monkeypatch.setattr(cls, "_assert_child_interpreter_version", lambda self, ws: None)
    monkeypatch.setattr(cls, "_verify_venv_provider", lambda self, ws, expected=None: None)
    monkeypatch.setattr(cls, "installed_build", lambda self, ws: rec.installed)
    monkeypatch.setattr(cls, "ensure_workspace_venv", _REAL_ENSURE)
    return rec


def _venv(ws: Path) -> str:
    return str(ws / ".dadaia" / ".venv")


def _python(ws: Path) -> str:
    return str(Path(_venv(ws)) / PLATFORM.venv_scripts_dir / f"python{PLATFORM.venv_exe_suffix}")


# The entry-script forms pip's distlib writes over the interpreter path.
_PLAIN = "#!{}3.12\n"
_SPACED = "#!/bin/sh\n'''exec' \"{}3.12\" \"$0\" \"$@\"\n' '''\n"  # a path with a space
_LONG = "#!/bin/sh\n'''exec' {}3.12 \"$0\" \"$@\"\n' '''\n"  # a shebang over 127 bytes
_LAUNCHER = 'MZ\x90\x00launcher\x00PK#!"{}"\r\n'  # Windows: launcher bytes, then the shebang


def _healthy(ws: Path, root: Path | None = None, form: str = _PLAIN) -> None:
    """The ``dadaia`` entrypoint in ``form``, naming ``root``'s venv python (``ws``'s by default)."""
    entry = Path(_venv(ws)) / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.parent.mkdir(parents=True)
    entry.write_bytes(form.format(_python(root or ws)).encode("utf-8"))


def _wheel_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run as a wheel install: no pyproject.toml beside the package."""
    site = tmp_path / "site-packages" / "dadaia_workspace"
    site.mkdir(parents=True)
    (site / "__init__.py").write_text("")
    monkeypatch.setattr(python_env_module.dadaia_workspace, "__file__", str(site / "__init__.py"))
    monkeypatch.setattr(python_env_module.metadata, "version", lambda name: "9.9.9")


def test_fresh_bootstrap_creates_venv_and_installs_package(
    tmp_path: Path, recorder: _Recorder
) -> None:
    """Resolved interpreter creates the venv, then the editable checkout; no dev tool."""
    mgr = VenvPythonEnvironmentManager()
    assert mgr.ensure_workspace_venv(str(tmp_path)) == _venv(tmp_path)

    create, install = recorder.commands
    assert create[:3] == ["fake-interpreter", "-m", "venv"] and create[-1] == _venv(tmp_path)
    assert install[:4] == [_python(tmp_path), "-m", "pip", "install"]
    assert "--editable" in install and (Path(install[-1]) / "pyproject.toml").is_file()
    assert not any("pytest" in argv for argv in recorder.commands)


def test_existing_bare_venv_is_repaired_not_skipped(tmp_path: Path, recorder: _Recorder) -> None:
    """The VENV-1 state: venv dir present, entrypoint missing -> install, no re-create."""
    (Path(_venv(tmp_path)) / PLATFORM.venv_scripts_dir).mkdir(parents=True)
    VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path))
    assert (recorder.venv_created, len(recorder.commands)) == ([], 1)


def test_healthy_venv_is_a_noop(tmp_path: Path, recorder: _Recorder) -> None:
    _healthy(tmp_path)
    VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path))
    assert recorder.commands == []


@pytest.mark.parametrize(
    ("installed", "running", "installs"),
    [
        ("0.4.7", "1.0.0", True),
        ("1.0.0", "1.0.0", False),
        ("1.0.0 another-build", "1.0.0", True),  # same label, other code
        ("1.0.0rc1", "1.0.0", True),
        ("0.9.9+e2e", "1.0.0", True),
        ("0.4.7", "0.5.0rc1", True),  # PEP 440: a pre-release outranks the prior final
        ("0.4.7.post1", "0.5.0.dev1", True),
    ],
)
def test_reinit_reinstalls_only_an_older_venv(
    tmp_path: Path,
    recorder: _Recorder,
    monkeypatch: pytest.MonkeyPatch,
    installed: str,
    running: str,
    installs: bool,
) -> None:
    """0.4.8 AC2.1/AC2.2, bugs upgrade-refuses-a-prerelease-label-as-a-downgrade and
    reinit-with-unchanged-version-label-mixes-venv-and-projection: PEP 440 order; any other
    build takes the one install path, only the running build itself is untouched."""
    install_fake_dist(monkeypatch, running)
    _healthy(tmp_path)
    recorder.installed = installed if " " in installed else f"{installed} {build_digest(None)}"
    VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path))
    assert [c[:4] for c in recorder.commands[:1]] == (
        [[_python(tmp_path), "-m", "pip", "install"]] if installs else []
    )


@pytest.mark.parametrize(
    ("ws_name", "origin", "form", "installs"),
    [
        ("ws", "", _PLAIN, False),
        ("ws", "", _SPACED, False),
        ("ws", "", _LONG, False),
        ("ws", "", _LAUNCHER, False),
        ("jo\u00e3o", "", _PLAIN, False),
        ("ws", "orig", _PLAIN, True),
        ("ws", "orig", _SPACED, True),
        ("ws", "deep", _PLAIN, True),
    ],
    ids=["own", "own-spaced", "own-long", "own-launcher", "own-non-ascii"]
    + ["copy", "copy-spaced", "copy-suffix-of-original"],
)
def test_reinit_reinstalls_a_venv_whose_entrypoint_names_another_root(
    tmp_path: Path,
    recorder: _Recorder,
    monkeypatch: pytest.MonkeyPatch,
    ws_name: str,
    origin: str,
    form: str,
    installs: bool,
) -> None:
    """Bug init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original: ``cp -a orig ws``
    keeps the build but the entry scripts name the original's python, so the copy is
    reinstalled by its OWN python — also when the original's path ends with the copy's."""
    install_fake_dist(monkeypatch, "1.0.0")
    ws = tmp_path / ws_name
    names = {
        "": ws,
        "orig": tmp_path / "orig",
        "deep": tmp_path / "deep" / ws.relative_to(tmp_path.anchor),
    }[origin]
    _healthy(ws, names, form)
    recorder.installed = f"1.0.0 {build_digest(None)}"
    VenvPythonEnvironmentManager().ensure_workspace_venv(str(ws))
    python = _python(ws)
    assert [c[:3] for c in recorder.commands] == ([[python, "-m", "pip"]] if installs else [])


@pytest.mark.parametrize(("installed", "running"), [("1.0.0+e2e", "1.0.0"), ("0.5.0rc1", "0.4.7")])
def test_reinit_refuses_a_newer_venv_before_any_write(
    tmp_path: Path,
    recorder: _Recorder,
    monkeypatch: pytest.MonkeyPatch,
    installed: str,
    running: str,
) -> None:
    """0.4.8 AC2.3: never downgrade; name the version."""
    install_fake_dist(monkeypatch, running)
    _healthy(tmp_path)
    recorder.installed = f"{installed} {build_digest(None)}"
    with pytest.raises(python_env_module.WorkspaceVenvNewerError) as exc:
        VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path))
    assert exc.value.installed == installed
    assert recorder.commands == []


@pytest.mark.parametrize("repacks", [True, False])
def test_install_spec_repacks_the_running_distribution_when_not_a_source_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repacks: bool
) -> None:
    """A wheel install bootstraps from ITSELF re-packed, never an index pin (which can
    resolve to other bytes); if it cannot re-pack it refuses naming the override."""
    _wheel_install(tmp_path, monkeypatch)
    wheel = tmp_path / "dadaia_workspace-9.9.9-py3-none-any.whl"
    monkeypatch.setattr(
        python_env_module,
        "repack_installed_wheel",
        lambda dest_dir, dist=None: wheel if repacks else None,
    )
    mgr = VenvPythonEnvironmentManager()
    if repacks:
        assert mgr._install_spec(str(tmp_path / "ws")) == str(wheel)
        return
    with pytest.raises(
        python_env_module.WorkspaceVenvBootstrapError, match="DADAIA_BOOTSTRAP_PACKAGE"
    ):
        mgr._install_spec(str(tmp_path / "ws"))


def test_local_candidate_wheel_overrides_index_pin_without_editable(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "dadaia_workspace-9.9.9-py3-none-any.whl"
    wheel.write_bytes(b"candidate")
    monkeypatch.setenv("DADAIA_BOOTSTRAP_PACKAGE", str(wheel))
    VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path / "workspace"))
    assert recorder.commands[1][-1] == str(wheel)
    assert "--editable" not in recorder.commands[1]


def test_bootstrap_installs_the_repacked_running_distribution(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One pip install of the re-packed wheel, no ``==`` pin ever attempted, and the
    wheel is scratch (0.4.8 AC1.6): gone after the install."""
    _wheel_install(tmp_path, monkeypatch)
    written: list[Path] = []

    def repack(dest_dir: Path, dist: object = None) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        written.append(dest_dir / "dadaia_workspace-9.9.9-py3-none-any.whl")
        written[0].write_bytes(b"fake-wheel")
        return written[0]

    monkeypatch.setattr(python_env_module, "repack_installed_wheel", repack)
    ws = tmp_path / "ws"
    VenvPythonEnvironmentManager().ensure_workspace_venv(str(ws))

    assert [c[-1] for c in recorder.commands[1:]] == [str(written[0])]
    assert not any("==" in token for call in recorder.commands for token in call)
    assert not written[0].exists() and not (ws / ".dadaia" / "tmp").exists()


def _installed_dist(root: Path, record: str) -> Path:
    site = root / "site"
    dist_info = site / "fakepkg-0.1.0.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text("Metadata-Version: 2.1\nName: fakepkg\nVersion: 0.1.0\n")
    (dist_info / "RECORD").write_text(record)
    return dist_info


def test_repack_installed_wheel_produces_a_valid_wheel(tmp_path: Path) -> None:
    """RECORD hashes are regenerated so pip's install-time verification passes."""
    dist_info = _installed_dist(
        tmp_path,
        "fakepkg/__init__.py,,\nfakepkg-0.1.0.dist-info/METADATA,,\n"
        "fakepkg-0.1.0.dist-info/WHEEL,,\nfakepkg-0.1.0.dist-info/RECORD,,\n",
    )
    (dist_info.parent / "fakepkg").mkdir()
    (dist_info.parent / "fakepkg" / "__init__.py").write_text("VALUE = 1\n")
    (dist_info / "WHEEL").write_text(
        "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    )

    wheel = repack_installed_wheel(tmp_path / "out", dist=Distribution.at(dist_info))

    assert wheel is not None and wheel.name == "fakepkg-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as zf:
        record = zf.read("fakepkg-0.1.0.dist-info/RECORD").decode()
        payload = zf.read("fakepkg/__init__.py")
        assert "fakepkg-0.1.0.dist-info/WHEEL" in zf.namelist()
    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
    assert f"fakepkg/__init__.py,sha256={digest},{len(payload)}" in record
    assert "fakepkg-0.1.0.dist-info/RECORD,," in record


def test_repack_returns_none_for_editable_install(tmp_path: Path) -> None:
    """An editable install has no packaged payload — repack declines, never lies."""
    dist_info = _installed_dist(
        tmp_path, "__editable__.fakepkg.pth,,\nfakepkg-0.1.0.dist-info/METADATA,,\n"
    )
    (dist_info.parent / "__editable__.fakepkg.pth").write_text("/src\n")
    assert repack_installed_wheel(tmp_path / "out", dist=Distribution.at(dist_info)) is None


def test_a_failed_reinstall_is_narrated_and_keeps_the_old_build(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bugs init-succeeds-after-provider-bootstrap-failure and
    reinit-with-unchanged-version-label-mixes-venv-and-projection: pip's raw stream never
    reaches the operator, and a failed reinstall of a same-label build is ONE pip
    transaction (``--force-reinstall``), so pip's rollback leaves the old ``dadaia`` in
    place — never a venv without it. The fake models pip: ``uninstall`` removes the build."""
    _healthy(tmp_path)
    recorder.installed = "0.0.1 old-build"
    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_install_spec", lambda workspace_root: "/tmp/w.whl")
    entry = Path(_venv(tmp_path)) / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    seen: list[list[str]] = []

    def failing_pip(cmd: list[str], check: bool = False, **kwargs: object) -> None:
        seen.append(list(cmd))
        assert kwargs.get("capture_output")
        if "uninstall" in cmd:
            entry.unlink()
        elif cmd[-1] == "/tmp/w.whl":
            raise subprocess.CalledProcessError(1, cmd, output="", stderr="ERROR: no dist")

    monkeypatch.setattr(python_env_module.subprocess, "run", failing_pip)
    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError, match="ERROR: no dist"):
        mgr.ensure_workspace_venv(str(tmp_path))
    assert entry.exists() and "--force-reinstall" in seen[-1]


def test_verification_failure_fails_the_bootstrap(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(self: VenvPythonEnvironmentManager, ws: str, expected: str | None = None) -> None:
        raise python_env_module.WorkspaceVenvBootstrapError("venv provider verification failed")

    monkeypatch.setattr(VenvPythonEnvironmentManager, "_verify_venv_provider", broken)
    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError):
        VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path))


def test_verify_venv_provider_uses_clean_env_and_checks_exact_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Never satisfiable through an inherited PYTHONPATH; names both versions."""
    envs: list[object] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        envs.append(kwargs.get("env"))
        return subprocess.CompletedProcess(cmd, 0, stdout="9.9.8\n", stderr="")

    monkeypatch.setattr(python_env_module.subprocess, "run", fake_run)
    monkeypatch.setenv("PYTHONPATH", "/somewhere/inherited")
    with pytest.raises(
        python_env_module.WorkspaceVenvBootstrapError, match="9.9.8.*9.9.9|9.9.9.*9.9.8"
    ):
        VenvPythonEnvironmentManager()._verify_venv_provider(str(tmp_path), expected="9.9.9")
    assert isinstance(envs[0], dict) and "PYTHONPATH" not in envs[0]


@pytest.mark.parametrize(
    ("error", "named", "not_named"),
    [
        pytest.param(PermissionError(13, "Permission denied"), "noexec", None, id="spawn-oserror"),
        pytest.param(
            subprocess.CalledProcessError(
                1, "venv", output="", stderr="PermissionError: [Errno 13]"
            ),
            "noexec",
            None,
            id="ensurepip-cannot-exec",
        ),
        pytest.param(
            subprocess.CalledProcessError(
                1, "venv", output="ensurepip is not available.", stderr=""
            ),
            "ensurepip",
            "noexec",
            id="AC1.6-base-python-without-ensurepip",
        ),
    ],
)
def test_venv_creation_failure_is_one_clean_actionable_error(
    tmp_path: Path,
    recorder: _Recorder,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    named: str,
    not_named: str | None,
) -> None:
    """Bug r3b-portability-import-venv-permission; 0.4.8 AC1.6: a DadaiaError naming the
    venv path and the likely cause, never a raw traceback nor a wrong cause."""

    def failing(cmd: list[str], check: bool = False, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(python_env_module.subprocess, "run", failing)
    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError) as excinfo:
        VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path))
    message = str(excinfo.value).lower()
    assert isinstance(excinfo.value, DadaiaError)
    assert str(tmp_path).lower() in message and named in message
    assert not_named is None or not_named not in message


@pytest.mark.parametrize(
    ("version", "spec", "ok"),
    [
        ((3, 12, 3), ">=3.12,<4.0", True),
        ((3, 10, 12), ">=3.12,<4.0", False),
        ((4, 0, 0), ">=3.12,<4.0", False),
        ((3, 1, 0), "", True),
        ((3, 1, 0), None, True),
    ],
)
def test_version_satisfies_requires_python(
    version: tuple[int, int, int], spec: str | None, ok: bool
) -> None:
    """Bug init-venv-bootstrap-inherits-degraded-base-python: an empty spec fails open."""
    assert python_env_module._version_satisfies(version, spec) is ok


@pytest.mark.parametrize(
    ("host", "path", "ok"),
    [
        ("win32", "\\tools\\python.exe", False),
        ("win32", "C:\\tools\\python.exe", True),
        ("linux", "/usr/bin/python3.12", True),
        ("linux", "python3.12", False),
    ],
)
def test_is_fully_qualified_per_host_flavor(
    monkeypatch: pytest.MonkeyPatch, host: str, path: str, ok: bool
) -> None:
    """CWE-426 (v0.4.3 T-043-23): a Windows drive-relative path passes ``isabs`` yet is
    not fully qualified."""
    monkeypatch.setattr(python_env_module, "PLATFORM", Capabilities.detect(host))
    assert python_env_module._is_fully_qualified(path) is ok


@pytest.mark.parametrize(
    ("which", "expected"),
    [("python3.12", []), ("/usr/bin/python3.13", ["/usr/bin/python3.13"])],
)
def test_path_candidates_keep_only_absolute_which_results(
    monkeypatch: pytest.MonkeyPatch, which: str, expected: list[str]
) -> None:
    """v0.4.3 A9.1."""
    monkeypatch.setattr(
        python_env_module.shutil, "which", lambda name: which if which.endswith(name) else None
    )
    assert python_env_module._path_candidates(12) == expected


@pytest.mark.parametrize(
    ("value", "expected"), [("python3", None), ("/usr/bin/python3.12", "/usr/bin/python3.12")]
)
def test_pyvenv_executable_keeps_only_an_absolute_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str, expected: str | None
) -> None:
    """v0.4.3 A9.1: a hand-edited relative ``pyvenv.cfg`` value is never returned."""
    (tmp_path / "pyvenv.cfg").write_text(f"executable = {value}\n", encoding="utf-8")
    monkeypatch.setattr(python_env_module.sys, "prefix", str(tmp_path))
    assert python_env_module._current_venv_pyvenv_executable() == expected


_V310, _V312 = (3, 10, 12), (3, 12, 13)


@pytest.mark.parametrize(
    ("host", "pyvenv", "on_path", "versions", "expected"),
    [
        pytest.param(
            "linux",
            "/usr/bin/python3.12",
            [],
            {"/usr/bin/python3": _V310, "/usr/bin/python3.12": _V312},
            "/usr/bin/python3.12",
            id="degraded-base-skipped-for-pyvenv-executable",
        ),
        pytest.param(
            "linux",
            None,
            ["/usr/local/bin/python3.13"],
            {"/usr/bin/python3": _V310, "/usr/local/bin/python3.13": (3, 13, 1)},
            "/usr/local/bin/python3.13",
            id="falls-back-to-path-search",
        ),
        pytest.param("linux", None, [], {"/usr/bin/python3": _V310}, None, id="nothing-satisfies"),
        pytest.param("linux", "python3", [], {"python3": _V312}, None, id="relative-never-probed"),
        pytest.param(
            "win32",
            "\\tools\\python.exe",
            [],
            {"\\tools\\python.exe": _V312},
            None,
            id="drive-relative-never-probed",
        ),
    ],
)
def test_child_venv_interpreter_is_the_first_candidate_satisfying_requires_python(
    monkeypatch: pytest.MonkeyPatch,
    host: str,
    pyvenv: str | None,
    on_path: list[str],
    versions: dict[str, tuple[int, int, int]],
    expected: str | None,
) -> None:
    """Bug init-venv-bootstrap-inherits-degraded-base-python; v0.4.3 A9.1 (CWE-426):
    base executable, then pyvenv.cfg, then PATH; a relative candidate is never spawned;
    nothing satisfying raises naming the requirement and what was tried."""
    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(python_env_module, "PLATFORM", Capabilities.detect(host))
    monkeypatch.setattr(mgr, "_running_requires_python", lambda: ">=3.12,<4.0")
    base = "/usr/bin/python3" if host == "linux" else ""
    monkeypatch.setattr(python_env_module.sys, "_base_executable", base, raising=False)
    monkeypatch.setattr(python_env_module, "_current_venv_pyvenv_executable", lambda: pyvenv)
    monkeypatch.setattr(python_env_module, "_path_candidates", lambda min_minor: on_path)
    probed: list[str] = []

    def version_of(exe: str) -> tuple[int, int, int] | None:
        probed.append(exe)
        return versions.get(exe)

    monkeypatch.setattr(python_env_module, "_interpreter_version", version_of)
    if expected is not None:
        assert mgr._resolve_child_venv_interpreter() == expected
        return
    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError, match="3.12"):
        mgr._resolve_child_venv_interpreter()
    assert pyvenv not in probed


@pytest.mark.parametrize(("version", "raises"), [(_V310, True), (_V312, False), (None, False)])
def test_child_venv_version_postcondition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    version: tuple[int, int, int] | None,
    raises: bool,
) -> None:
    """A mismatched child is refused naming both versions before any pip install; an
    unintrospectable one fails open (pip stays the final authority)."""
    mgr = VenvPythonEnvironmentManager()
    monkeypatch.setattr(mgr, "_running_requires_python", lambda: ">=3.12,<4.0")
    monkeypatch.setattr(python_env_module, "_interpreter_version", lambda exe: version)
    if not raises:
        mgr._assert_child_interpreter_version(str(tmp_path))
        return
    with pytest.raises(python_env_module.WorkspaceVenvBootstrapError) as excinfo:
        mgr._assert_child_interpreter_version(str(tmp_path))
    message = str(excinfo.value)
    assert "3.10.12" in message and ">=3.12,<4.0" in message
    assert "interpreter mismatch" in message.lower()


def test_interpreter_version_probe_passes_a_bounded_timeout_and_devnull_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A9.2: the probe subprocess must be bounded (``timeout=``) and never inherit the
    caller's stdin (``stdin=subprocess.DEVNULL``) — an interactive or hanging candidate
    must not wedge the bootstrap."""
    seen: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> "subprocess.CompletedProcess[str]":
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="3 12 3\n", stderr="")

    monkeypatch.setattr(python_env_module.subprocess, "run", fake_run)

    result = python_env_module._interpreter_version("/usr/bin/python3.12")

    assert result == (3, 12, 3)
    assert seen.get("stdin") is python_env_module.subprocess.DEVNULL
    timeout = seen.get("timeout")
    assert isinstance(timeout, int | float) and 0 < timeout <= 30


def test_interpreter_version_probe_degrades_to_none_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A9.2: a candidate that would otherwise hang (``subprocess.run`` raising
    ``TimeoutExpired`` once the bound is enforced) degrades to ``None`` and is skipped —
    never propagates and never hangs the caller."""

    def hanging_run(cmd: list[str], **kwargs: object) -> "subprocess.CompletedProcess[str]":
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 5))

    monkeypatch.setattr(python_env_module.subprocess, "run", hanging_run)

    assert python_env_module._interpreter_version("/usr/bin/python-that-hangs") is None
