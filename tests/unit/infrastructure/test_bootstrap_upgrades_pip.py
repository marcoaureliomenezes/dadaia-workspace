"""The venv the product creates must not ship an installer with known advisories.

`venv.create(with_pip=True)` leaves whatever pip the host interpreter bundles. On this
machine that is pip 24.0, which carries advisories for path traversal when extracting a
wheel, symlink escape when extracting a tar, and mishandling of concatenated archives —
all of which matter because a consumer workspace's venv goes on to install other packages
(bug `workspace-venv-ships-vulnerable-pip`).

The upgrade must NOT break the documented offline-first bootstrap: an air-gapped `init`
has to keep working, so a failure to reach an index is a silent no-op, never an error.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager


class _Recorder:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[list[str]] = []
        self._fail = fail

    def __call__(self, cmd: list[str], **kwargs: object) -> None:
        self.calls.append(cmd)
        if self._fail:
            raise OSError("no index reachable")


def test_the_bootstrap_upgrades_pip(tmp_path: Path) -> None:
    run = _Recorder()

    VenvPythonEnvironmentManager()._upgrade_pip(tmp_path / "pip", runner=run)

    assert run.calls, "no upgrade attempted"
    cmd = run.calls[0]
    assert "install" in cmd and "--upgrade" in cmd and "pip" in cmd, cmd


def test_an_unreachable_index_is_a_silent_no_op(tmp_path: Path) -> None:
    """Air-gapped init must keep working — the upgrade is best-effort, never a gate."""
    run = _Recorder(fail=True)

    VenvPythonEnvironmentManager()._upgrade_pip(tmp_path / "pip", runner=run)  # must not raise

    assert run.calls, "it should still have tried"
