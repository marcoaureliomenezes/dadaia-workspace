"""JsonRunStateStore — atomic manifest.json + append-only events.jsonl per run."""

import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from dadaia_workspace.core.exceptions import RunNotFoundError
from dadaia_workspace.core.models.run_state import (
    EventKind,
    RunEvent,
    RunManifest,
    RunStatus,
    StageState,
    StageStatus,
)
from dadaia_workspace.infrastructure.public_assets_common import _atomic_write_text

_MANIFEST = "manifest.json"
_EVENTS = "events.jsonl"


def _manifest_to_dict(m: RunManifest) -> dict[str, object]:
    return {
        "run_id": m.run_id,
        "workflow_name": m.workflow_name,
        "workflow_version": m.workflow_version,
        "context": m.context,
        "runtime": m.runtime,
        "status": m.status.value,
        "started_at": m.started_at,
        "finished_at": m.finished_at,
        "inputs": m.inputs,
        "stages": [
            {
                "id": s.id,
                "agent": s.agent,
                "status": s.status.value,
                "started_at": s.started_at,
                "finished_at": s.finished_at,
                "output_path": s.output_path,
                "error": s.error,
            }
            for s in m.stages
        ],
    }


def _manifest_from_dict(d: dict[str, object]) -> RunManifest:
    raw_stages = d.get("stages") or []
    if not isinstance(raw_stages, list):
        raw_stages = []
    stages = tuple(
        StageState(
            id=str(s["id"]),
            agent=str(s["agent"]),
            status=StageStatus(str(s["status"])),
            started_at=s.get("started_at"),
            finished_at=s.get("finished_at"),
            output_path=s.get("output_path"),
            error=s.get("error"),
        )
        for s in raw_stages
        if isinstance(s, dict)
    )
    inputs_raw = d.get("inputs") or {}
    inputs = inputs_raw if isinstance(inputs_raw, dict) else {}
    return RunManifest(
        run_id=str(d["run_id"]),
        workflow_name=str(d["workflow_name"]),
        workflow_version=str(d.get("workflow_version", "0.0.0")),
        context=str(d["context"]),
        runtime=str(d["runtime"]),
        status=RunStatus(str(d["status"])),
        started_at=str(d["started_at"]),
        finished_at=d.get("finished_at"),  # type: ignore[arg-type]
        stages=stages,
        inputs={str(k): str(v) for k, v in inputs.items()},
    )


def _event_to_line(e: RunEvent) -> str:
    payload = asdict(e)
    payload["kind"] = e.kind.value
    return json.dumps(payload, separators=(",", ":"))


def _line_to_event(line: str) -> RunEvent:
    raw = json.loads(line)
    return RunEvent(
        ts=str(raw["ts"]),
        run_id=str(raw["run_id"]),
        kind=EventKind(str(raw["kind"])),
        stage_id=raw.get("stage_id"),
        payload=raw.get("payload"),
    )


class JsonRunStateStore:
    def __init__(self, runs_dir: Path) -> None:
        self._dir = runs_dir

    def _run_dir(self, run_id: str) -> Path:
        return self._dir / run_id

    def _manifest_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / _MANIFEST

    def _events_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / _EVENTS

    def create_run(self, manifest: RunManifest) -> None:
        run_dir = self._run_dir(manifest.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        self._events_path(manifest.run_id).touch(exist_ok=True)
        self._write_manifest_atomic(manifest)

    def load_run(self, run_id: str) -> RunManifest:
        mpath = self._manifest_path(run_id)
        if not mpath.exists():
            raise RunNotFoundError(f"run '{run_id}' not found under {self._dir}")
        with mpath.open(encoding="utf-8") as f:
            return _manifest_from_dict(json.load(f))

    def update_manifest(self, manifest: RunManifest) -> None:
        self._write_manifest_atomic(manifest)

    def append_event(self, event: RunEvent) -> None:
        path = self._events_path(event.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(_event_to_line(event) + "\n")

    def list_runs(self) -> tuple[RunManifest, ...]:
        if not self._dir.exists():
            return ()
        runs: list[RunManifest] = []
        for child in sorted(self._dir.iterdir()):
            if child.is_dir() and (child / _MANIFEST).exists():
                runs.append(self.load_run(child.name))
        return tuple(runs)

    def iter_events(self, run_id: str) -> Iterable[RunEvent]:
        path = self._events_path(run_id)
        if not path.exists():
            return
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield _line_to_event(line)
                except (json.JSONDecodeError, KeyError):
                    continue

    def _write_manifest_atomic(self, manifest: RunManifest) -> None:
        mpath = self._manifest_path(manifest.run_id)
        mpath.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(mpath, json.dumps(_manifest_to_dict(manifest), indent=2))
