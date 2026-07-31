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


# ── the same defect, two more places (found by sweeping the class, not by a report) ──
#
# `r24-public-install-does-not-repair-kimi-shim-mode` was fixed for the Kimi shims because
# that is where the validator happened to look. Sweeping for the shape afterwards found it
# alive in two more install paths, and both matter more than the one that was reported:
#
#   * `.dadaia/hooks/*.sh` — the Codex hook wrappers. These ARE the PreToolUse gate
#     (root-whitelist, venv-guard, SDD path-class). A wrapper that is not executable means
#     the gate silently stops firing, and `codex_doctor` already knows how to report
#     "codex hook wrapper not executable" — so doctor diagnoses it while install claims
#     success, which is the r24 loop exactly.
#   * `.dadaia/scripts/*.sh` — the git chokepoints, including the pre-push security-verdict
#     gate. Here the chmod was not suppressed at all, so one unwritable file aborted the
#     whole install with a traceback instead of reporting the file.
#
# Fixing an instance is how the class survives. This is the class.


def _executables(workspace: Path) -> list[Path]:
    """Every file dadaia installs that something must EXECUTE.

    The hook wrappers carry no extension (``codex-pre-gate``, not ``codex-pre-gate.sh``),
    which an earlier version of this helper globbed for and therefore missed entirely —
    the tests passed while covering only the scripts directory. Listing the directory is
    the honest way to ask "everything here must be executable".
    """
    hooks = [p for p in sorted((workspace / ".dadaia" / "hooks").iterdir()) if p.is_file()]
    scripts = sorted((workspace / ".dadaia" / "scripts").glob("*.sh"))
    return hooks + scripts


def test_install_writes_every_managed_script_executable(workspace: Path) -> None:
    FileSystemPublicAssetManager().install(workspace, target="codex")

    written = _executables(workspace)
    assert written, "no managed executables were installed at all"
    not_executable = [p.name for p in written if not _is_executable(p)]
    assert not not_executable, (
        f"these gate scripts were installed without an execute bit: {not_executable}"
    )


def test_a_gate_script_stripped_of_its_bit_is_repaired_by_install(workspace: Path) -> None:
    manager = FileSystemPublicAssetManager()
    manager.install(workspace, target="codex")
    stripped = _executables(workspace)[0]
    stripped.chmod(0o644)

    manager.install(workspace, target="codex")

    assert _is_executable(stripped), (
        f"{stripped.name} stayed non-executable after the prescribed install; a hook "
        "wrapper that cannot execute is a gate that silently stops firing"
    )


def test_a_gate_script_whose_bit_cannot_be_set_is_reported(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = FileSystemPublicAssetManager()
    manager.install(workspace, target="codex")
    target = _executables(workspace)[0]
    target.chmod(0o644)

    real_chmod = Path.chmod

    def refuse(self: Path, mode: int, **kwargs: object) -> None:
        if self.name == target.name:
            raise PermissionError(13, "Operation not permitted")
        real_chmod(self, mode, **kwargs)

    monkeypatch.setattr(Path, "chmod", refuse)

    report = "\n".join(manager.install(workspace, target="codex"))

    assert target.name in report and "not executable" in report, (
        "install must say it could not make a gate script executable rather than exiting "
        "0 in silence or dying with a traceback"
    )


# ── the doctor half of the same class ───────────────────────────────────────────
#
# Found by sweeping every corruption the doctor is supposed to catch and asking, for each,
# whether the prescribed `dadaia public install` actually repairs it. Five of six were
# detected and repaired. The sixth was repaired but NEVER DETECTED:
# `.dadaia/scripts/pre-push-ci-gate.sh` stripped of its execute bit read `[ok]`.
#
# That file is the pre-push security-verdict gate and the CI preflight. Without its execute
# bit git cannot run it, so the push gate silently stops enforcing — and `public doctor`,
# the command whose entire job is to tell the operator their workspace is sound, says
# everything is fine. The `dadaia:scripts/*` lines compare CONTENT only; the sibling
# surface, the Codex hook wrappers, has had an exec-bit check in `codex_doctor` all along.
# One instance checked, the sibling left out — the same shape a third time.


def test_doctor_reports_a_chokepoint_that_lost_its_execute_bit(workspace: Path) -> None:
    manager = FileSystemPublicAssetManager()
    manager.install(workspace, target="all")
    gate = workspace / ".dadaia" / "scripts" / "pre-push-ci-gate.sh"
    assert gate.is_file(), "the pre-push gate script was not installed at all"
    gate.chmod(0o644)

    bad = [line for line in manager.doctor(workspace) if not line.startswith("[ok]")]

    assert any("pre-push-ci-gate.sh" in line and "not executable" in line for line in bad), (
        "doctor reported the workspace sound while the pre-push security-verdict gate "
        f"could not be executed by git:\n{bad}"
    )


def test_doctor_is_green_again_after_the_prescribed_install(workspace: Path) -> None:
    """The other half of a useful diagnosis: the remedy it prescribes has to work."""
    manager = FileSystemPublicAssetManager()
    manager.install(workspace, target="all")
    gate = workspace / ".dadaia" / "scripts" / "pre-push-ci-gate.sh"
    gate.chmod(0o644)

    manager.install(workspace, target="all")

    remaining = [line for line in manager.doctor(workspace) if "pre-push-ci-gate" in line]
    assert remaining and all(line.startswith("[ok]") for line in remaining), remaining
