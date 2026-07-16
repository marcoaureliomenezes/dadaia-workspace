"""Process-control ports used by disposable workspace certification."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple, Protocol


class CertificationProcessResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str


class RunningCertificationProcess(Protocol):
    def poll(self) -> int | None: ...
    def read_stderr(self) -> str: ...
    def terminate(self) -> None: ...
    def wait(self, timeout: float) -> int: ...
    def kill(self) -> None: ...


class CertificationProcess(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CertificationProcessResult: ...

    def start(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
    ) -> RunningCertificationProcess: ...
