"""SubprocessProcessRunner — the sole subprocess-execution adapter (ADR-0001: one adapter, no port)."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple


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
            result = subprocess.run(  # noqa: S603
                list(argv),
                cwd=cwd,
                env=None if env is None else dict(env),
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
    cwd: Path, env: Mapping[str, str]
) -> Callable[[Sequence[str]], tuple[int, str]]:
    """A ``ci_preflight.Runner`` running each argv as a subprocess in *cwd* with *env* —
    here so ``ci_preflight/service.py`` never imports ``subprocess``."""

    def _run(argv: Sequence[str]) -> tuple[int, str]:
        try:
            result = SubprocessProcessRunner().run(argv, cwd=cwd, env=env)
        except FileNotFoundError as exc:
            missing = exc.filename or (argv[0] if argv else "command")
            return 127, f"command not found: {missing} — install it or run the checks directly."
        return result.returncode, result.stdout + result.stderr

    return _run
