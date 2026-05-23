"""backfill_telemetry_agent_name.py — PR4-08 idempotent backfill.

Operator-facing command documented for CLOSURE.md:
    python3 scripts/backfill_telemetry_agent_name.py [--db PATH] [--projects-dir DIR]

Re-scans all *.jsonl files under the Claude projects directory and updates
sessions rows whose agent_name IS NULL by extracting the first canonical
subagent_type dispatch event for that session.

Hard requirements (PR4-08):
- Uses UPDATE ... WHERE session_id = ? — never INSERT.
- Running the script twice is a no-op (idempotent).
- Prints "updated N of M rows" to stdout.

Security: no content fields are read — only event.type, event.sessionId, and
    event.message.content[i].type/name/input.subagent_type are accessed.
    These are equivalent to the fields already accessed by the production reader.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sqlite3
import sys

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = pathlib.Path("~/.dadaia/state/telemetry/telemetry.sqlite").expanduser()
DEFAULT_PROJECTS_DIR = pathlib.Path("~/.claude/projects").expanduser()

# Non-canonical subtypes — same set as in reader/claude.py
_NON_CANONICAL_SUBTYPES: frozenset[str] = frozenset({"Explore", "Plan"})


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _extract_subagent_type_from_raw(raw_event: object) -> str | None:
    """Return the first canonical subagent_type from a raw jsonl event.

    JSON path (PR4-05):
        event.message.content[i].input.subagent_type
        where event.type == "assistant"
          AND event.message.content[i].type == "tool_use"
          AND event.message.content[i].name == "Agent"

    Returns None for non-canonical types ("Explore", "Plan") and when the
    event does not carry a dispatch.
    """
    if not isinstance(raw_event, dict):
        return None
    if raw_event.get("type") != "assistant":
        return None
    message = raw_event.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, list):
        return None
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "tool_use" and item.get("name") == "Agent":
            inp = item.get("input")
            if isinstance(inp, dict):
                val = inp.get("subagent_type")
                if val is not None and str(val) not in _NON_CANONICAL_SUBTYPES:
                    return str(val)
    return None


def _scan_jsonl_for_session(
    file_path: pathlib.Path,
    target_session_id: str,
) -> str | None:
    """Scan *file_path* for the first canonical subagent_type for *target_session_id*.

    Returns the subagent_type string, or None if not found.
    """
    try:
        with file_path.open("rb") as fh:
            for raw_line in fh:
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                if event.get("sessionId") != target_session_id:
                    continue
                val = _extract_subagent_type_from_raw(event)
                if val is not None:
                    return val
    except OSError:
        pass
    return None


def _discover_agent_name_for_session(
    session_id: str,
    projects_dirs: list[pathlib.Path],
    reader_state_paths: list[str],
) -> str | None:
    """Find the canonical agent_name for *session_id* by scanning jsonl files.

    Strategy:
    1. Look for a jsonl file whose stem == session_id in any projects directory
       (direct filename match — O(1) lookup).
    2. Fall back to reader_state_paths hint: scan only the files the reader
       previously processed for this session_id.
    3. If no match: scan all *.jsonl files under projects directories (slow path).

    Returns None if no canonical dispatch event is found.
    """
    # Strategy 1: direct filename match
    for projects_dir in projects_dirs:
        direct_match = projects_dir / f"{session_id}.jsonl"
        if direct_match.is_file():
            result = _scan_jsonl_for_session(direct_match, session_id)
            if result is not None:
                return result

    # Strategy 2: reader_state hint
    for rs_path in reader_state_paths:
        p = pathlib.Path(rs_path)
        if p.is_file() and p.stem == session_id:
            result = _scan_jsonl_for_session(p, session_id)
            if result is not None:
                return result

    # Strategy 3: full scan (slow, only for unresolved sessions)
    for projects_dir in projects_dirs:
        if not projects_dir.is_dir():
            continue
        for project_subdir in projects_dir.iterdir():
            if not project_subdir.is_dir():
                continue
            for jsonl_path in project_subdir.glob("*.jsonl"):
                result = _scan_jsonl_for_session(jsonl_path, session_id)
                if result is not None:
                    return result

    return None


# ---------------------------------------------------------------------------
# Main backfill logic
# ---------------------------------------------------------------------------


def backfill(
    db_path: pathlib.Path,
    projects_dirs: list[pathlib.Path],
    dry_run: bool = False,
) -> tuple[int, int]:
    """Run the backfill.

    Returns (updated_count, total_null_count).

    The operation is idempotent:
    - Only rows with agent_name IS NULL are candidates.
    - Each row is updated with UPDATE ... WHERE session_id = ? (never INSERT).
    - Re-running when all rows are already filled → updated_count = 0.
    """
    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # Fetch all NULL agent_name sessions
        null_sessions = conn.execute(
            "SELECT session_id FROM sessions WHERE agent_name IS NULL"
        ).fetchall()
        total_null = len(null_sessions)

        if total_null == 0:
            print("updated 0 of 0 rows (all sessions already have agent_name set)")
            return 0, 0

        # Fetch reader_state paths as hints for file discovery
        reader_state_rows = conn.execute("SELECT file_path FROM reader_state").fetchall()
        reader_state_paths = [r["file_path"] for r in reader_state_rows]

        updated = 0
        with conn:  # transaction context
            for row in null_sessions:
                session_id: str = row["session_id"]
                agent_name = _discover_agent_name_for_session(
                    session_id, projects_dirs, reader_state_paths
                )
                if agent_name is None:
                    continue  # no dispatch event found — leave NULL
                if not dry_run:
                    conn.execute(
                        "UPDATE sessions SET agent_name = ? WHERE session_id = ?",
                        (agent_name, session_id),
                    )
                updated += 1

        print(f"updated {updated} of {total_null} rows")
        return updated, total_null

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill telemetry sessions.agent_name from jsonl dispatch events."
    )
    parser.add_argument(
        "--db",
        metavar="PATH",
        type=pathlib.Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to telemetry SQLite (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--projects-dir",
        metavar="DIR",
        type=pathlib.Path,
        action="append",
        dest="projects_dirs",
        default=None,
        help=(
            f"Claude projects directory to scan (may be repeated; default: {DEFAULT_PROJECTS_DIR})"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be updated without writing to the database.",
    )
    return parser.parse_args()


def main() -> None:
    # Security guard: refuse to run as root (mirrors TelemetryService T6 check).
    if os.getuid() == 0:
        print(
            "[ERROR] Backfill must not run as root (uid=0). "
            "This prevents unintended access to other users' data.",
            file=sys.stderr,
        )
        sys.exit(1)

    args = _parse_args()
    db_path: pathlib.Path = args.db.expanduser()
    projects_dirs: list[pathlib.Path] = [
        p.expanduser() for p in (args.projects_dirs or [DEFAULT_PROJECTS_DIR])
    ]
    dry_run: bool = args.dry_run

    if dry_run:
        print("[dry-run] No writes will be performed.")

    updated, total = backfill(db_path, projects_dirs, dry_run=dry_run)

    if dry_run and updated > 0:
        print(f"[dry-run] would update {updated} of {total} rows")


if __name__ == "__main__":
    main()
