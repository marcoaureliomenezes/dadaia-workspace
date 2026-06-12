"""T-014-06 — ``ProcessAncestry`` port + three adapters.

Contract red lines:

* No adapter ever calls ``os.kill`` (no destructive probe).
* Indeterminate ancestry resolves to the explicit ``Ancestry.UNKNOWN`` sentinel.

Each adapter is exercised with a synthetic source (a fake ``/proc`` tree, a
ProcessRunner fake, a mocked Toolhelp32 snapshot dict) — never a real process tree.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.process_ancestry import (
    UNKNOWN,
    Ancestry,
)
from dadaia_workspace.core.protocols.process_runner import ProcessResult
from dadaia_workspace.infrastructure.process_ancestry_adapter import (
    LinuxProcAncestry,
    PsProcessAncestry,
    WindowsToolhelpAncestry,
)

# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


def _make_proc_tree(tmp_path: Path, ppids: dict[int, int]) -> Path:
    """Write a synthetic ``/proc/<pid>/stat`` tree with the given pid→ppid links."""
    proc = tmp_path / "proc"
    for pid, ppid in ppids.items():
        d = proc / str(pid)
        d.mkdir(parents=True)
        # field layout: pid (comm) state ppid ...  — comm includes parens/spaces.
        (d / "stat").write_text(f"{pid} (my proc) S {ppid} 0 0\n", encoding="utf-8")
    return proc


class _PsRunnerFake:
    """ProcessRunner fake answering ``ps -o ppid= -p <pid>`` from a pid→ppid map."""

    def __init__(self, ppids: dict[int, int], *, fail: bool = False) -> None:
        self._ppids = ppids
        self._fail = fail
        self.calls: list[Sequence[str]] = []

    def run(self, argv, *, cwd=None, timeout=None):  # type: ignore[no-untyped-def]
        self.calls.append(list(argv))
        if self._fail:
            return ProcessResult(returncode=1, stdout="", stderr="ps failed")
        pid = int(argv[-1])
        if pid not in self._ppids:
            return ProcessResult(returncode=1, stdout="", stderr="")
        return ProcessResult(returncode=0, stdout=f"  {self._ppids[pid]}\n", stderr="")


# --------------------------------------------------------------------------- #
# Linux adapter
# --------------------------------------------------------------------------- #


def test_linux_direct_parent_is_ancestor(tmp_path: Path) -> None:
    proc = _make_proc_tree(tmp_path, {100: 50, 50: 1})
    probe = LinuxProcAncestry(proc_root=proc)
    assert probe.is_ancestor(50, 100) is Ancestry.ANCESTOR


def test_linux_grandparent_is_ancestor(tmp_path: Path) -> None:
    proc = _make_proc_tree(tmp_path, {200: 100, 100: 50, 50: 1})
    probe = LinuxProcAncestry(proc_root=proc)
    assert probe.is_ancestor(50, 200) is Ancestry.ANCESTOR


def test_linux_unrelated_is_not_ancestor(tmp_path: Path) -> None:
    proc = _make_proc_tree(tmp_path, {200: 100, 100: 1})
    probe = LinuxProcAncestry(proc_root=proc)
    assert probe.is_ancestor(999, 200) is Ancestry.NOT_ANCESTOR


def test_linux_self_is_ancestor(tmp_path: Path) -> None:
    proc = _make_proc_tree(tmp_path, {200: 1})
    probe = LinuxProcAncestry(proc_root=proc)
    assert probe.is_ancestor(200, 200) is Ancestry.ANCESTOR


def test_linux_missing_pid_is_unknown(tmp_path: Path) -> None:
    proc = _make_proc_tree(tmp_path, {})  # empty tree
    probe = LinuxProcAncestry(proc_root=proc)
    assert probe.is_ancestor(50, 100) is UNKNOWN


def test_linux_comm_with_parens_parses(tmp_path: Path) -> None:
    proc = tmp_path / "proc"
    (proc / "100").mkdir(parents=True)
    # comm containing spaces AND a close-paren — the robust rfind(")") parse must win.
    (proc / "100" / "stat").write_text("100 (weird ) name) S 50 0\n", encoding="utf-8")
    (proc / "50").mkdir(parents=True)
    (proc / "50" / "stat").write_text("50 (init) S 1 0\n", encoding="utf-8")
    probe = LinuxProcAncestry(proc_root=proc)
    assert probe.is_ancestor(50, 100) is Ancestry.ANCESTOR


# --------------------------------------------------------------------------- #
# macOS / ps adapter
# --------------------------------------------------------------------------- #


def test_ps_grandparent_is_ancestor() -> None:
    runner = _PsRunnerFake({300: 200, 200: 100, 100: 1})
    probe = PsProcessAncestry(runner)
    assert probe.is_ancestor(100, 300) is Ancestry.ANCESTOR


def test_ps_unrelated_is_not_ancestor() -> None:
    runner = _PsRunnerFake({300: 200, 200: 1})
    probe = PsProcessAncestry(runner)
    assert probe.is_ancestor(999, 300) is Ancestry.NOT_ANCESTOR


def test_ps_runner_failure_is_unknown() -> None:
    runner = _PsRunnerFake({300: 200}, fail=True)
    probe = PsProcessAncestry(runner)
    assert probe.is_ancestor(200, 300) is UNKNOWN


def test_ps_uses_injected_runner_not_subprocess() -> None:
    runner = _PsRunnerFake({300: 1})
    probe = PsProcessAncestry(runner)
    probe.is_ancestor(1, 300)
    assert runner.calls and runner.calls[0][:3] == ["ps", "-o", "ppid="]


# --------------------------------------------------------------------------- #
# Windows adapter (mocked Toolhelp32 snapshot)
# --------------------------------------------------------------------------- #


def test_windows_grandparent_is_ancestor() -> None:
    probe = WindowsToolhelpAncestry(snapshot={400: 300, 300: 200, 200: 0})
    assert probe.is_ancestor(200, 400) is Ancestry.ANCESTOR


def test_windows_unrelated_is_not_ancestor() -> None:
    probe = WindowsToolhelpAncestry(snapshot={400: 300, 300: 0})
    assert probe.is_ancestor(999, 400) is Ancestry.NOT_ANCESTOR


def test_windows_missing_link_is_unknown() -> None:
    probe = WindowsToolhelpAncestry(snapshot={400: 300})  # 300 has no ppid entry
    assert probe.is_ancestor(200, 400) is UNKNOWN


# --------------------------------------------------------------------------- #
# Contract: non-destructive (never os.kill) + indeterminate chains
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "probe",
    [
        LinuxProcAncestry(),
        PsProcessAncestry(_PsRunnerFake({})),
        WindowsToolhelpAncestry(snapshot={}),
    ],
)
def test_never_calls_os_kill(probe, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    def _boom(*_a, **_k):  # noqa: ANN002, ANN003
        raise AssertionError("ProcessAncestry must never call os.kill")

    monkeypatch.setattr(os, "kill", _boom)
    # Any verdict is fine; the point is os.kill is never invoked.
    result = probe.is_ancestor(1, 12345)
    assert isinstance(result, Ancestry)


def test_cyclic_chain_terminates_unknown(tmp_path: Path) -> None:
    # A corrupt ppid cycle must not loop forever — hop budget → UNKNOWN.
    proc = _make_proc_tree(tmp_path, {10: 11, 11: 10})
    probe = LinuxProcAncestry(proc_root=proc)
    assert probe.is_ancestor(999, 10) is UNKNOWN


# --------------------------------------------------------------------------- #
# Composition-root selection respects the PLATFORM seam (no in-adapter branch)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("platform_str", "expected"),
    [
        ("linux", LinuxProcAncestry),
        ("darwin", PsProcessAncestry),
        ("win32", WindowsToolhelpAncestry),
    ],
)
def test_container_selects_adapter_by_platform_seam(
    platform_str: str, expected: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace import container
    from dadaia_workspace.core import platform as platform_mod

    monkeypatch.setattr(platform_mod, "PLATFORM", platform_mod.Capabilities.detect(platform_str))
    probe = container.build_process_ancestry()
    assert isinstance(probe, expected)
