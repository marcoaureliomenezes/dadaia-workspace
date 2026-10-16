"""SubprocessProcessRunner — the sole subprocess-execution adapter."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

from dadaia_workspace.core import platform


class ProcessResult(NamedTuple):
    """Outcome of running an external command."""

    returncode: int
    stdout: str
    stderr: str


class SubprocessProcessRunner:
    """Run an external command; a timeout raises ``TimeoutError``, never a ``subprocess`` type."""

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        try:
            result = platform.run(argv, cwd=cwd, env=env, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"command timed out after {exc.timeout}s: {exc.cmd!r}") from exc
        return ProcessResult(result.returncode, result.stdout or "", result.stderr or "")
