"""JsonWorkflowStateStore — persists running workflow PIDs to a JSON state file.

Design (T-016-P06):
  Provides restart-survival for the workflow liveness tracker in PanelService.
  State is written to ``.dadaia/states/running_workflows.json`` as a flat
  ``{workflow_name: pid}`` mapping.

  File is written atomically (write to a temp file, then rename) so a crash
  during write leaves the old state intact.

  All public methods are safe to call concurrently from a single-threaded
  panel server (no threading; panel uses BaseHTTPServer which is single-thread
  by default).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_FILENAME = "running_workflows.json"


class JsonWorkflowStateStore:
    """Persist running-workflow PIDs across panel restarts.

    Parameters
    ----------
    states_dir:
        Path to ``.dadaia/states/`` (created by ``dadaia init``).
    """

    def __init__(self, states_dir: Path) -> None:
        self._path = states_dir / _STATE_FILENAME

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> dict[str, int]:
        """Return the persisted ``{workflow_name: pid}`` mapping.

        Returns an empty dict when the file is absent or corrupt.
        """
        if not self._path.exists():
            return {}
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                logger.warning(
                    "JsonWorkflowStateStore: state file %s has unexpected type %s; resetting",
                    self._path,
                    type(data).__name__,
                )
                return {}
            # Keep only entries with integer PID values.
            return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, int)}
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "JsonWorkflowStateStore: failed to read %s: %s; returning empty state",
                self._path,
                exc,
            )
            return {}

    def save(self, state: dict[str, int]) -> None:
        """Atomically write *state* to the state file.

        An atomic rename ensures the file is never in a partially-written
        state from the reader's perspective.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=self._path.parent,
                prefix=".running_workflows_",
                suffix=".json.tmp",
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
            except Exception:
                os.unlink(tmp_path)
                raise
            os.replace(tmp_path, self._path)
        except OSError as exc:
            logger.warning(
                "JsonWorkflowStateStore: failed to save state to %s: %s",
                self._path,
                exc,
            )

    def set_pid(self, workflow_name: str, pid: int) -> None:
        """Persist *pid* for *workflow_name* (overwrites any existing entry)."""
        state = self.load()
        state[workflow_name] = pid
        self.save(state)

    def remove(self, workflow_name: str) -> None:
        """Remove *workflow_name* from the persisted state (no-op if absent)."""
        state = self.load()
        if workflow_name in state:
            del state[workflow_name]
            self.save(state)
