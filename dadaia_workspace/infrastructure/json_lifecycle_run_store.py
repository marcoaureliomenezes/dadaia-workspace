"""JSON-backed lifecycle run store."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import LifecycleRun
from dadaia_workspace.features.lifecycle.run_store import LifecycleRunStoreError

_SCHEMA_VERSION = "lifecycle-run-v1"


class JsonLifecycleRunStore:
    """Persist lifecycle runs under canonical workspace runtime state."""

    def __init__(self, workspace_root: Path, *, location: str = "states") -> None:
        self._workspace_root = workspace_root.resolve()
        self._dadaia_root = self._workspace_root / ".dadaia"
        self._reject_repo_tree_root()
        if location not in {"states", "runs"}:
            raise LifecycleRunStoreError("unsupported lifecycle run-store location")
        self._root = self._dadaia_root / location / "lifecycle"

    @property
    def root(self) -> Path:
        return self._root

    def save(self, run: LifecycleRun) -> None:
        """Atomically persist or replace a lifecycle run."""
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(run.run_id)
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "run": run.to_dict(),
        }
        self._atomic_write(path, json.dumps(payload, indent=2, sort_keys=True))

    def load(self, run_id: str) -> LifecycleRun | None:
        """Load a lifecycle run by id."""
        path = self._path_for(run_id)
        if not path.exists():
            return None
        return self._load_path(path)

    def resume(self, run_id: str) -> LifecycleRun:
        """Return a persisted run for idempotent resume."""
        run = self.load(run_id)
        if run is None:
            raise LifecycleRunStoreError("lifecycle run state not found", self._path_for(run_id))
        return run

    def _load_path(self, path: Path) -> LifecycleRun:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LifecycleRunStoreError(
                f"corrupt lifecycle run state; inspect or remove malformed JSON ({exc.msg})",
                path,
            ) from exc
        except OSError as exc:
            raise LifecycleRunStoreError("cannot read lifecycle run state", path) from exc
        if not isinstance(raw, dict):
            raise LifecycleRunStoreError("corrupt lifecycle run state; root is not an object", path)
        if raw.get("schema_version") != _SCHEMA_VERSION:
            raise LifecycleRunStoreError("unsupported lifecycle run state schema", path)
        run_raw = raw.get("run")
        if not isinstance(run_raw, dict):
            raise LifecycleRunStoreError("corrupt lifecycle run state; missing run object", path)
        try:
            return LifecycleRun.from_dict(run_raw)
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            raise LifecycleRunStoreError(
                "corrupt lifecycle run state; invalid run payload", path
            ) from exc

    def _path_for(self, run_id: str) -> Path:
        if not run_id or "/" in run_id or "\\" in run_id or ".." in run_id:
            raise LifecycleRunStoreError("invalid lifecycle run id")
        return self._root / f"{run_id}.json"

    def _reject_repo_tree_root(self) -> None:
        has_workspace_marker = False
        for path in (self._workspace_root, *self._workspace_root.parents):
            if path.joinpath(".git").exists():
                raise LifecycleRunStoreError(
                    "refusing to create lifecycle state inside a repository tree",
                    self._workspace_root,
                )
            if path.joinpath(".dadaia").exists():
                has_workspace_marker = True
        if not has_workspace_marker:
            return

    def _atomic_write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            text=True,
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.write("\n")
            os.replace(tmp_path, path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
