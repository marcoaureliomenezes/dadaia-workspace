"""Subprocess implementation of the certification process-control port."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from dadaia_workspace.core.protocols.certification_process import CertificationProcessResult


class _RunningProcess:
    def __init__(self, process: subprocess.Popen[str]) -> None:
        self._process = process

    def poll(self) -> int | None:
        return self._process.poll()

    def read_stderr(self) -> str:
        return self._process.stderr.read() if self._process.stderr else ""

    def terminate(self) -> None:
        self._process.terminate()

    def wait(self, timeout: float) -> int:
        try:
            return self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
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
            result = subprocess.run(
                list(argv),
                cwd=cwd,
                env=dict(env) if env is not None else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
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
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=dict(env),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return _RunningProcess(process)
