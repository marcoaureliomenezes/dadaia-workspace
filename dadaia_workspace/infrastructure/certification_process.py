"""Subprocess-backed certification process control (one adapter, no port)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from subprocess import Popen, TimeoutExpired
from typing import NamedTuple

from dadaia_workspace.core import platform


class CertificationProcessResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str


class _RunningProcess:
    def __init__(self, process: Popen[str]) -> None:
        self._process = process

    def poll(self) -> int | None:
        return self._process.poll()

    def terminate(self) -> None:
        self._process.terminate()

    def wait(self, timeout: float) -> int:
        try:
            return self._process.wait(timeout=timeout)
        except TimeoutExpired as exc:
            raise TimeoutError(f"process did not exit within {timeout}s") from exc

    def kill(self) -> None:
        self._process.kill()


class SubprocessCertificationProcess:
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CertificationProcessResult:
        try:
            result = platform.run(argv, cwd=cwd, env=env, timeout=timeout)
        except TimeoutExpired as exc:
            raise TimeoutError(f"process did not exit within {timeout}s") from exc
        return CertificationProcessResult(
            result.returncode, result.stdout or "", result.stderr or ""
        )

    def start(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
    ) -> _RunningProcess:
        return _RunningProcess(platform.popen(argv, cwd=cwd, env=env))
