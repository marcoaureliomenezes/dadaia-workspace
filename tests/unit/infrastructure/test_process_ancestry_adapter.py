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
from typing import Any

import pytest

from dadaia_workspace.core.protocols.process_ancestry import (
    UNKNOWN,
    Ancestry,
    ProcessAncestry,
)
from dadaia_workspace.core.protocols.process_runner import ProcessResult
from dadaia_workspace.infrastructure.process_ancestry_adapter import (
    LinuxProcAncestry,
    PsProcessAncestry,
    WindowsToolhelpAncestry,
)

# --------------------------------------------------------------------------- #
# Fakes                                                                        #
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


def _linux_probe(ppids: dict[int, int], tmp_path: Path) -> LinuxProcAncestry:
    return LinuxProcAncestry(proc_root=_make_proc_tree(tmp_path, ppids))


def _ps_probe(ppids: dict[int, int], *, fail: bool = False) -> PsProcessAncestry:
    return PsProcessAncestry(_PsRunnerFake(ppids, fail=fail))


def _windows_probe(ppids: dict[int, int]) -> WindowsToolhelpAncestry:
    return WindowsToolhelpAncestry(snapshot=ppids)


# --------------------------------------------------------------------------- #
# Cross-adapter matrix: ancestor / grandparent / unrelated / self / missing /
# failure — identical semantics across the 3 real adapter implementations.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("adapter_kind", "case"),
    [
        (kind, case)
        for kind in ("linux", "ps", "windows")
        for case in ("direct-parent", "grandparent", "unrelated", "missing-link")
    ]
    + [("linux", "self")],
)
def test_ancestry_matrix_across_adapters(tmp_path: Path, adapter_kind: str, case: str) -> None:
    if case == "direct-parent":
        ppids, child, ancestor, expected = {100: 50, 50: 1}, 100, 50, Ancestry.ANCESTOR
    elif case == "grandparent":
        ppids, child, ancestor, expected = (
            {200: 100, 100: 50, 50: 1},
            200,
            50,
            Ancestry.ANCESTOR,
        )
    elif case == "unrelated":
        ppids, child, ancestor, expected = {200: 100, 100: 1}, 200, 999, Ancestry.NOT_ANCESTOR
    elif case == "self":
        ppids, child, ancestor, expected = {200: 1}, 200, 200, Ancestry.ANCESTOR
    else:  # missing-link
        ppids, child, ancestor, expected = {}, 100, 50, UNKNOWN

    if adapter_kind == "linux":
        probe: ProcessAncestry = _linux_probe(ppids, tmp_path)
    elif adapter_kind == "ps":
        probe = _ps_probe(ppids)
    else:
        probe = _windows_probe(ppids)

    assert probe.is_ancestor(ancestor, child) is expected


def test_ps_failure_and_linux_comm_with_parens_parse(tmp_path: Path) -> None:
    ps_probe = _ps_probe({300: 200}, fail=True)
    assert ps_probe.is_ancestor(200, 300) is UNKNOWN

    proc = tmp_path / "proc"
    (proc / "100").mkdir(parents=True)
    # comm containing spaces AND a close-paren — the robust rfind(")") parse must win.
    (proc / "100" / "stat").write_text("100 (weird ) name) S 50 0\n", encoding="utf-8")
    (proc / "50").mkdir(parents=True)
    (proc / "50" / "stat").write_text("50 (init) S 1 0\n", encoding="utf-8")
    linux_probe = LinuxProcAncestry(proc_root=proc)
    assert linux_probe.is_ancestor(50, 100) is Ancestry.ANCESTOR


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
def test_never_calls_os_kill(probe: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import os

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("ProcessAncestry must never call os.kill")

    monkeypatch.setattr(os, "kill", _boom)
    # Any verdict is fine; the point is os.kill is never invoked.
    result = probe.is_ancestor(1, 12345)
    assert isinstance(result, Ancestry)

    if isinstance(probe, LinuxProcAncestry):
        # A corrupt ppid cycle must not loop forever — hop budget → UNKNOWN.
        cyclic_proc = _make_proc_tree(tmp_path, {10: 11, 11: 10})
        cyclic_probe = LinuxProcAncestry(proc_root=cyclic_proc)
        assert cyclic_probe.is_ancestor(999, 10) is UNKNOWN


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
