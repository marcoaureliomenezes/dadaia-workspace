"""A repair that did not happen must not be reported as success.

Bug ``r24-public-install-does-not-repair-kimi-shim-mode`` (validator R24 / R-21). Doctor
correctly diagnosed ``[drift] kimi-code:hooks/dadaia-kimi-pre-gate.sh (not executable)``
and prescribed ``dadaia public install --target kimi-code``. That command exited 0 and,
on the validator's filesystem, left the file at 0644 — doctor reported the same drift
immediately afterwards. The operator was told the fix ran, and it had not.

On an ordinary filesystem the installer's ``chmod(0o755)`` does repair the bit, and that
is asserted below so the working path stays covered. The defect is the OTHER path: the
chmod sat inside a bare ``contextlib.suppress(OSError)``, so when the mode could not be
restored the failure was erased — no line in the output, no non-zero exit, nothing. The
installer's report and the filesystem disagreed, and the report won.

This is the third failure of this exact shape in this codebase (a broad suppression
around a guard, making the guard look applied while it does nothing). The fix is not to
stop suppressing — an installer must not crash on one mode bit — it is to *verify the
outcome* and say so when the repair did not take.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.unit

_SHIM = "dadaia-kimi-pre-gate.sh"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "kimihome"
    home.mkdir()
    monkeypatch.setenv("KIMI_CODE_HOME", str(home))
    root = tmp_path / "ws"
    root.mkdir()
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(root)
    return root


def _home(workspace: Path) -> Path:
    from dadaia_workspace.infrastructure.runtime_config import kimi_code_home

    return kimi_code_home()


def _install(workspace: Path) -> list[str]:
    return FileSystemPublicAssetManager().install(workspace, target="kimi-code")


def _is_executable(path: Path) -> bool:
    return bool(path.stat().st_mode & stat.S_IXUSR)


def test_install_restores_a_shim_stripped_of_its_execute_bit(workspace: Path) -> None:
    _install(workspace)
    shim = _home(workspace) / "hooks" / _SHIM
    shim.chmod(0o644)

    _install(workspace)

    assert _is_executable(shim), "this is the prescribed remedy; it has to actually repair"


def test_a_chmod_that_cannot_be_applied_is_reported_not_swallowed(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The half that was invisible: the remedy runs, fails, and says nothing."""
    _install(workspace)
    shim = _home(workspace) / "hooks" / _SHIM
    shim.chmod(0o644)

    real_chmod = Path.chmod

    def refuse(self: Path, mode: int, **kwargs: object) -> None:
        if self.name == _SHIM:
            raise PermissionError(13, "Operation not permitted")
        real_chmod(self, mode, **kwargs)

    monkeypatch.setattr(Path, "chmod", refuse)

    report = "\n".join(_install(workspace))

    assert not _is_executable(shim)
    assert _SHIM in report and "not executable" in report, (
        "an installer that cannot restore the bit must say so; exiting 0 in silence is "
        "what sent the operator back to a doctor still reporting the same drift"
    )
