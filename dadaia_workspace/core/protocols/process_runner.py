"""ProcessRunner Protocol — subprocess execution abstraction.

The concrete implementation lives in
``dadaia_workspace.infrastructure.subprocess_runner``.

``core/`` is zero-I/O — only Protocol definitions live here.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple, Protocol


class ProcessResult(NamedTuple):
    """Outcome of running an external command."""

    returncode: int
    stdout: str
    stderr: str


class ProcessRunner(Protocol):
    """Execute an external command and return its outcome.

    Implementors must NOT raise on non-zero exit codes — the caller decides
    whether a non-zero code is an error.  ``TimeoutError`` is re-raised when
    the process exceeds ``timeout`` seconds.
    """

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> ProcessResult: ...
