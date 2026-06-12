"""SubprocessProcessRunner — production implementation of ``ProcessRunner``.

This is the ONLY module in ``dadaia_workspace`` that may import ``subprocess``
for feature-layer use.  All features/ modules must consume the ``ProcessRunner``
protocol and receive this adapter (or a test fake) via injection.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from dadaia_workspace.core.protocols.process_runner import ProcessResult


class SubprocessProcessRunner:
    """Execute external commands via stdlib ``subprocess.run``.

    ``TimeoutError`` is raised (re-raised from ``subprocess.TimeoutExpired``)
    when the process exceeds the given timeout so callers can handle it
    uniformly without coupling to ``subprocess``.
    """

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> ProcessResult:
        try:
            result = subprocess.run(  # noqa: S603
                list(argv),
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"command timed out after {exc.timeout}s: {exc.cmd!r}") from exc
        return ProcessResult(
            returncode=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )


def subprocess_runner_for_ci(
    cwd: Path,
) -> Callable[[Sequence[str]], tuple[int, str]]:
    """Build a ``ci_preflight.Runner`` backed by real subprocesses.

    This factory lives in ``infrastructure/`` so that ``ci_preflight/service.py``
    never needs to import ``subprocess`` directly.  The returned callable matches
    the ``Runner = Callable[[Sequence[str]], tuple[int, str]]`` type alias used
    by the preflight service.

    Parameters
    ----------
    cwd:
        Working directory for each check subprocess.
    """

    def _run(argv: Sequence[str]) -> tuple[int, str]:
        try:
            proc = subprocess.run(  # noqa: S603
                list(argv),
                cwd=cwd,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            missing = exc.filename or (argv[0] if argv else "command")
            return 127, f"command not found: {missing} — install it or run the checks directly."
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    return _run
