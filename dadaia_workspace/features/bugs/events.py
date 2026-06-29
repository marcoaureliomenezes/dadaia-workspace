"""Append-only JSONL bug-event telemetry."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

EVENT_TYPES = frozenset({"reported", "resolved", "superseded", "deferred", "rejected", "archived"})
TERMINAL_EVENTS = frozenset({"resolved", "superseded", "deferred", "rejected", "archived"})
_BUG_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_MAX_ROWS_PER_FILE = 1000


@dataclass(frozen=True)
class BugEventResult:
    path: Path
    event: dict[str, object]


def make_event(
    *,
    bug_id: str,
    event: str,
    reported_by: str,
    ts: str | None = None,
    title: str | None = None,
    severity: str | None = None,
    surface: str | None = None,
    component: str | None = None,
    context: str | None = None,
    tags: tuple[str, ...] = (),
    symptom: str | None = None,
    repro: str | None = None,
    expected: str | None = None,
    notes: str | None = None,
    release: str | None = None,
    superseded_by: str | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "bug_id": bug_id,
        "event": event,
        "ts": ts or _now_ts(),
        "reported_by": reported_by,
    }
    optional: dict[str, object | None] = {
        "title": title,
        "severity": severity,
        "surface": surface,
        "component": component,
        "context": context,
        "symptom": symptom,
        "repro": repro,
        "expected": expected,
        "notes": notes,
        "release": release,
        "superseded_by": superseded_by,
        "reason": reason,
    }
    record.update({key: value for key, value in optional.items() if value not in (None, "")})
    if tags:
        record["tags"] = list(tags)
    validate_event(record)
    return record


def validate_event(event: dict[str, object]) -> None:
    bug_id = event.get("bug_id")
    if not isinstance(bug_id, str) or not _BUG_ID_RE.match(bug_id):
        raise ValueError("bug_id must match ^[a-z][a-z0-9-]*$")
    event_type = event.get("event")
    if event_type not in EVENT_TYPES:
        raise ValueError(f"event must be one of: {', '.join(sorted(EVENT_TYPES))}")
    ts = event.get("ts")
    if not isinstance(ts, str) or not ts.endswith("Z"):
        raise ValueError("ts must be a UTC timestamp ending in Z")
    reported_by = event.get("reported_by")
    if not isinstance(reported_by, str) or not reported_by.strip():
        raise ValueError("reported_by is required")
    if event_type == "reported":
        for key in ("title", "severity", "surface", "context", "symptom"):
            value = event.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"reported event requires {key}")
    if event_type == "resolved" and not event.get("release"):
        raise ValueError("resolved event requires release")
    if event_type == "superseded" and not event.get("superseded_by"):
        raise ValueError("superseded event requires superseded_by")
    if event_type in {"deferred", "rejected"} and not event.get("reason"):
        raise ValueError(f"{event_type} event requires reason")
    tags = event.get("tags")
    if tags is not None and (
        not isinstance(tags, list) or not all(isinstance(item, str) for item in tags)
    ):
        raise ValueError("tags must be an array of strings")


def append_event(specs_dir: Path, event: dict[str, object], *, now: datetime | None = None) -> Path:
    validate_event(event)
    events = read_events(specs_dir)
    _validate_coherence(events, event)
    target = _current_event_file(specs_dir, now=now)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
    return target


def read_events(specs_dir: Path) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for path in sorted((specs_dir / "bugs").glob("*.jsonl")):
        for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc
            if not isinstance(event, dict):
                raise ValueError(f"{path}:{line_no}: event must be an object")
            validate_event(event)
            events.append(event)
    return events


def bug_status(specs_dir: Path, bug_id: str | None = None) -> dict[str, dict[str, object]]:
    status: dict[str, dict[str, object]] = {}
    for event in read_events(specs_dir):
        current_id = str(event["bug_id"])
        if bug_id is not None and current_id != bug_id:
            continue
        status[current_id] = {
            "bug_id": current_id,
            "state": event["event"],
            "last_event_ts": event["ts"],
            "last_event": event,
        }
    return status


def bug_stats(specs_dir: Path) -> dict[str, object]:
    events = read_events(specs_dir)
    by_event = Counter(str(event["event"]) for event in events)
    states = bug_status(specs_dir)
    open_count = sum(1 for item in states.values() if item["state"] not in TERMINAL_EVENTS)
    return {
        "events": len(events),
        "bugs": len(states),
        "open": open_count,
        "terminal": len(states) - open_count,
        "by_event": dict(sorted(by_event.items())),
    }


def migrate_markdown_bugs(specs_dir: Path, *, apply: bool = False) -> dict[str, object]:
    migrated: list[str] = []
    for path in sorted((specs_dir / "bugs").glob("*.md")):
        frontmatter, title = _read_bug_markdown(path)
        bug_id = str(frontmatter.get("name") or path.stem)
        status = str(frontmatter.get("status") or "Open")
        reported = make_event(
            bug_id=bug_id,
            event="reported",
            reported_by=str(frontmatter.get("session_id") or "migration"),
            title=title or bug_id,
            severity=str(frontmatter.get("severity") or "UNKNOWN"),
            surface=str(frontmatter.get("surface") or "legacy-markdown"),
            context=str(frontmatter.get("context") or "unknown"),
            symptom=title or bug_id,
            notes=f"migrated from {path.name}",
        )
        if apply:
            append_event(specs_dir, reported)
            if status.lower() == "closed":
                append_event(
                    specs_dir,
                    make_event(
                        bug_id=bug_id,
                        event="resolved",
                        reported_by="migration",
                        release=str(frontmatter.get("release") or "unknown"),
                    ),
                )
            archive = specs_dir / "bugs" / "_archive" / path.name
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), archive)
        migrated.append(path.name)
    return {"apply": apply, "migrated": migrated, "count": len(migrated)}


def _validate_coherence(events: list[dict[str, object]], event: dict[str, object]) -> None:
    if event["event"] == "reported":
        return
    bug_id = event["bug_id"]
    if not any(existing["bug_id"] == bug_id and existing["event"] == "reported" for existing in events):
        raise ValueError(f"{event['event']} event for {bug_id} requires a prior reported event")


def _current_event_file(specs_dir: Path, *, now: datetime | None = None) -> Path:
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%HZ")
    base = specs_dir / "bugs" / f"{stamp}.jsonl"
    if _row_count(base) < _MAX_ROWS_PER_FILE:
        return base
    index = 1
    while True:
        candidate = specs_dir / "bugs" / f"{stamp[:-1]}-{index}Z.jsonl"
        if _row_count(candidate) < _MAX_ROWS_PER_FILE:
            return candidate
        index += 1


def _row_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _read_bug_markdown(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    frontmatter: dict[str, str] = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                key, sep, value = line.partition(":")
                if sep:
                    frontmatter[key.strip()] = value.strip().strip('"')
    title = path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return frontmatter, title


def _now_ts() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
