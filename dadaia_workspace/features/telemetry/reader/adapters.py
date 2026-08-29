"""Reader adapters — ``Reader.ingest(store, now)`` (K8).

Each adapter wraps one runtime's free-function reader together with the path
resolution / directory walk that used to live duplicated three times inside
``TelemetryService._do_refresh``. ``TelemetryService.refresh()`` now loops
over a ``Sequence[Reader]`` instead of hand-rolling one block per runtime;
each adapter keeps its own try/except so one runtime's failure never blocks
the others (matching the prior per-block isolation).
"""

from __future__ import annotations

import logging
import os
import pathlib
from typing import Protocol

from dadaia_workspace.features.telemetry.store import TelemetryStore

logger = logging.getLogger(__name__)

_CLAUDE_PROJECTS_DIR = pathlib.Path("~/.claude/projects").expanduser()
_DEFAULT_CODEX_PATH = pathlib.Path("~/.codex/state_5.sqlite").expanduser()
_DEFAULT_KIMI_INDEX = pathlib.Path("~/.kimi-code/session_index.jsonl").expanduser()


class Reader(Protocol):
    """One telemetry ingestion source.

    Implementations never raise — a failure is logged and swallowed inside
    ``ingest`` itself so one reader's error can never block its siblings.
    """

    def ingest(self, store: TelemetryStore, now: str) -> None: ...


class ClaudeReader:
    """Walks ``~/.claude/projects/*/*.jsonl``, ingesting each session file."""

    def ingest(self, store: TelemetryStore, now: str) -> None:
        from dadaia_workspace.features.telemetry.reader.claude import read_session_file

        if not _CLAUDE_PROJECTS_DIR.is_dir():
            return
        for project_dir in _CLAUDE_PROJECTS_DIR.iterdir():
            if not project_dir.is_dir():
                continue
            for jsonl_file in project_dir.glob("*.jsonl"):
                try:
                    read_session_file(jsonl_file, store, now)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("ClaudeReader: error reading %s: %s", jsonl_file, exc)


class CodexReader:
    """Reads ``~/.codex/state_5.sqlite`` (or ``DADAIA_CODEX_DB_PATH`` override)."""

    def ingest(self, store: TelemetryStore, now: str) -> None:
        from dadaia_workspace.features.telemetry.reader.codex import read_codex_db

        env = os.environ.get("DADAIA_CODEX_DB_PATH")
        codex_path = pathlib.Path(env) if env else _DEFAULT_CODEX_PATH
        try:
            read_codex_db(codex_path, store, now)
        except Exception as exc:  # noqa: BLE001
            logger.warning("CodexReader: error reading %s: %s", codex_path, exc)


class KimiReader:
    """Reads ``~/.kimi-code/session_index.jsonl`` (or ``DADAIA_KIMI_SESSION_INDEX``)."""

    def ingest(self, store: TelemetryStore, now: str) -> None:
        from dadaia_workspace.features.telemetry.reader.kimi import read_kimi_sessions

        env = os.environ.get("DADAIA_KIMI_SESSION_INDEX")
        kimi_index = pathlib.Path(env) if env else _DEFAULT_KIMI_INDEX
        try:
            read_kimi_sessions(kimi_index, store, now)
        except Exception as exc:  # noqa: BLE001
            logger.warning("KimiReader: error reading %s: %s", kimi_index, exc)


#: Production ingestion set, in dispatch order (order has no behavioural
#: significance — each reader is independent and errors are isolated).
DEFAULT_READERS: tuple[Reader, ...] = (ClaudeReader(), CodexReader(), KimiReader())

__all__ = ["DEFAULT_READERS", "ClaudeReader", "CodexReader", "KimiReader", "Reader"]
