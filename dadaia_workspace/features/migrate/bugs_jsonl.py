"""One-time ``specs/bugs/*.md`` → event-sourced JSONL migration (v0.1.46 AC-2).

Converts each legacy Markdown bug record into a coherent event stream and MOVES the source
``.md`` into ``specs/bugs/_archive/`` **in the same run** (the archival is intrinsic to the
migration, not a deferred Bash follow-task — review BLOCKING-1). An **Open** bug emits a
single ``reported`` event; a **Closed** bug emits ``reported`` plus the terminal event it can
reconstruct (``superseded`` when a ``superseded_by`` is recorded, else ``resolved`` with the
closing release — or the ``unknown`` sentinel + a WARN when the frontmatter omits it, R-3).

The move is ``shutil.move`` (in-process). git detects the rename at commit time — a direct
``git mv`` would require a subprocess, which the features layer must not import
(``features-no-infrastructure`` / ``features-no-subprocess``), so the reconciliation is left
to the normal add/commit. ``--dry-run`` PLANS the source→dest pairs and writes/moves nothing.

Idempotent: a re-run finds no loose ``.md`` (they were moved) and, as a belt-and-suspenders
guard against a partial prior run, skips any ``bug_id`` already present in the JSONL stream —
so no duplicate events and no re-move.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import yaml

from dadaia_workspace.core.models.bugs import BugEvent
from dadaia_workspace.features.migrate.tree_v2 import MigrateResult

__all__ = ["migrate_bugs_jsonl"]

#: Rotation ceiling mirrored from the store contract (kept local — the pure features layer
#: must not import the infrastructure store; the naming/rotation convention is the contract).
_ROWS_PER_FILE = 1000

#: Sentinel ts for a bug whose frontmatter records no usable date.
_FALLBACK_TS = "2000-01-01T00:00:00Z"

#: Sentinel closing release when a Closed bug records none (R-3 — never drop the bug).
_UNKNOWN_RELEASE = "unknown"

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

#: Frontmatter keys that may carry the closing release, in priority order.
_RELEASE_KEYS: tuple[str, ...] = (
    "resolved_in",
    "shipped_in",
    "fixed_by",
    "closed_by_release",
    "closed_by",
    "resolved_by",
    "release",
    "resolved",
    "closed",
    "adopted",
)

_VALID_SEVERITIES: frozenset[str] = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})

# Body-section extraction: ``**Symptom:** ... `` up to the next ``**Label:**`` or EOF.
_BODY_LABELS = ("symptom", "repro", "expected", "notes")


def migrate_bugs_jsonl(specs_dir: Path, *, dry_run: bool = False) -> MigrateResult:
    """Migrate ``specs/bugs/*.md`` into JSONL event streams + archive the sources.

    Args:
        specs_dir: Absolute path to the ``specs/`` directory being migrated.
        dry_run:   When *True*, compute the plan (planned moves recorded in
                   :attr:`MigrateResult.moved`) without writing JSONL or moving any file.

    Returns:
        A :class:`MigrateResult`: ``moved`` = ``(src, dst)`` archive moves (planned in
        dry-run), ``skipped`` = per-bug WARN/skip messages.
    """
    result = MigrateResult(dry_run=dry_run)
    bugs_dir = specs_dir / "bugs"
    if not bugs_dir.is_dir():
        result.skipped.append("bugs/ not found — nothing to migrate.")
        return result

    archive_dir = bugs_dir / "_archive"
    already = _existing_bug_ids(bugs_dir)

    for md_path in sorted(bugs_dir.glob("*.md")):
        if md_path.name == "README.md":
            continue
        events = _events_for_bug(md_path, result)
        if not events:
            continue
        bug_id = events[0].bug_id
        dst = archive_dir / md_path.name
        if bug_id in already:
            result.skipped.append(
                f"{md_path.name}: bug_id '{bug_id}' already in JSONL — skipped (idempotent)."
            )
            continue
        if dry_run:
            result.moved.append((md_path, dst))
            continue
        for event in events:
            _append_event_line(bugs_dir, event)
        already.add(bug_id)
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(md_path), str(dst))
        result.moved.append((md_path, dst))

    return result


# ---------------------------------------------------------------------------
# Per-bug event reconstruction
# ---------------------------------------------------------------------------


def _events_for_bug(md_path: Path, result: MigrateResult) -> list[BugEvent]:
    """Reconstruct the coherent event stream for one bug ``.md`` (``[]`` if unparseable)."""
    text = md_path.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    bug_id = _str(fm.get("name")) or md_path.stem
    reported_ts = _to_ts(fm.get("reported") or fm.get("opened") or fm.get("created_at"))
    body = _body_sections(text)

    reported = BugEvent(
        bug_id=bug_id,
        event="reported",
        ts=reported_ts,
        reported_by=_str(fm.get("reported_by")) or "bugs-jsonl-migration",
        title=_str(fm.get("title")) or bug_id,
        severity=_severity(fm.get("severity")),
        surface=_str(fm.get("surface")) or "",
        component=_str(fm.get("component")) or "",
        context=_str(fm.get("context")) or "",
        tags=(),
        symptom=body.get("symptom", ""),
        repro=body.get("repro", ""),
        expected=body.get("expected", ""),
        notes=body.get("notes", ""),
    ).redact()

    if _is_open(fm.get("status")):
        return [reported]

    terminal = _terminal_event(bug_id, fm, reported_ts, md_path, result)
    return [reported, terminal]


def _terminal_event(
    bug_id: str,
    fm: dict[str, object],
    reported_ts: str,
    md_path: Path,
    result: MigrateResult,
) -> BugEvent:
    """Reconstruct the single terminal event for a Closed bug."""
    terminal_ts = _clamp_ts(
        _to_ts(fm.get("closed") or fm.get("adopted"), default=reported_ts),
        floor=reported_ts,
    )
    superseded_by = _str(fm.get("superseded_by"))
    if superseded_by:
        return BugEvent(
            bug_id=bug_id,
            event="superseded",
            ts=terminal_ts,
            reported_by="bugs-jsonl-migration",
            superseded_by=superseded_by,
        )

    release = _closing_release(fm)
    if release == _UNKNOWN_RELEASE:
        result.skipped.append(
            f"{md_path.name}: Closed bug with no recorded closing release — "
            f"emitting resolved with release '{_UNKNOWN_RELEASE}' (WARN, R-3)."
        )
    return BugEvent(
        bug_id=bug_id,
        event="resolved",
        ts=terminal_ts,
        reported_by="bugs-jsonl-migration",
        release=release,
    )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _frontmatter(text: str) -> dict[str, object]:
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return {}
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _body_sections(text: str) -> dict[str, str]:
    """Extract ``**Symptom/Repro/Expected/Notes:**`` sections from the Markdown body."""
    out: dict[str, str] = {}
    for label in _BODY_LABELS:
        pattern = re.compile(
            rf"\*\*{label}:\*\*\s*(.*?)(?=\n\*\*[A-Z][a-z]+:\*\*|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        m = pattern.search(text)
        if m:
            out[label] = m.group(1).strip()
    return out


def _existing_bug_ids(bugs_dir: Path) -> set[str]:
    """Collect ``bug_id``s already present across the JSONL logs (idempotency guard)."""
    out: set[str] = set()
    for jsonl in bugs_dir.glob("*.jsonl"):
        try:
            lines = jsonl.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("bug_id"), str):
                out.add(obj["bug_id"])
    return out


def _is_open(status: object) -> bool:
    return _str(status).strip().lower() == "open" if status is not None else True


def _closing_release(fm: dict[str, object]) -> str:
    for key in _RELEASE_KEYS:
        value = _str(fm.get(key))
        if value:
            return value
    return _UNKNOWN_RELEASE


def _severity(value: object) -> str:
    text = _str(value).strip().upper()
    return text if text in _VALID_SEVERITIES else "MEDIUM"


def _str(value: object) -> str:
    """Coerce a scalar frontmatter value to a stripped string (``''`` for None)."""
    if value is None:
        return ""
    return str(value).strip()


def _to_ts(value: object, *, default: str = _FALLBACK_TS) -> str:
    """Coerce a frontmatter date/datetime into an ISO-8601 UTC ts, or ``default``."""
    text = _str(value)
    if not text:
        return default
    # A bare date (2026-06-27) → midnight UTC; a full datetime is used as-is.
    date_only = re.match(r"^(\d{4}-\d{2}-\d{2})$", text)
    if date_only:
        return f"{date_only.group(1)}T00:00:00Z"
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return default
    return text if text.endswith("Z") or "+" in text else f"{text}Z"


def _clamp_ts(ts: str, *, floor: str) -> str:
    """Return ``ts``, or ``floor`` when ``ts`` chronologically precedes ``floor``.

    A legacy Closed bug whose ``closed`` date predates its ``reported`` date would otherwise
    emit a terminal event before its own ``reported`` event — splitting the stream across
    hour-buckets out of order and tripping a false doctor coherence ERROR. Clamping the
    terminal ts up to the ``reported`` ts keeps ``reported`` first in an ordered stream. A ts
    that cannot be parsed is returned unchanged (best-effort, never raises).
    """
    try:
        ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        floor_dt = datetime.fromisoformat(floor.replace("Z", "+00:00"))
    except ValueError:
        return ts
    return floor if ts_dt < floor_dt else ts


def _append_event_line(bugs_dir: Path, event: BugEvent) -> None:
    """Append one event as a JSONL line to ``<hour>Z-<n>.jsonl`` (store naming contract)."""
    hour = datetime.fromisoformat(event.ts.replace("Z", "+00:00")).strftime("%Y%m%dT%H")
    target = _target_file(bugs_dir, hour)
    line = json.dumps(event.to_dict(), sort_keys=True, ensure_ascii=False) + "\n"
    with target.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _target_file(bugs_dir: Path, hour: str) -> Path:
    """Resolve the append target for ``hour``, rolling to ``-<n+1>`` at the row ceiling."""
    existing = sorted(
        (
            p
            for p in bugs_dir.glob(f"{hour}Z-*.jsonl")
            if re.match(rf"^{hour}Z-\d+\.jsonl$", p.name)
        ),
        key=lambda p: int(p.name.rsplit("-", 1)[1].split(".", 1)[0]),
    )
    if not existing:
        return bugs_dir / f"{hour}Z-00.jsonl"
    last = existing[-1]
    rows = sum(1 for line in last.read_text(encoding="utf-8").splitlines() if line.strip())
    if rows >= _ROWS_PER_FILE:
        n = int(last.name.rsplit("-", 1)[1].split(".", 1)[0]) + 1
        return bugs_dir / f"{hour}Z-{n:02d}.jsonl"
    return last
