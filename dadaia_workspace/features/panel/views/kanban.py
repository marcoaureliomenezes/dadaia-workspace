"""Kanban view — GET /api/kanban.

Reads `.dadaia/sessions/*.json` (R2 session files) and groups them into a
Kanban board response: one swimlane per Spec Context Project, four phase columns.

Session mode → column mapping (canonical §7 lifecycle):

    Column key      Label                    Session modes
    -----------     -----------------------  ---------------------------------
    backlog         Backlog                  READ
    release_def     Release Definition       SPEC
    impl_review     Implementation + Review  BOUND_IMPLEMENTATION, BOUND_REVIEW
    closure         Closure                  (present-but-empty — no session
                                             mode maps to closure phase yet)

    Unknown / unrecognised mode → backlog  (fail-safe — never drop)

The XOR-lock dimming between implementation and review columns is retired: both
modes now share the single ``impl_review`` column, so the mutual-exclusion visual
no longer applies.

Staleness is computed at read time from ``last_seen_at`` and ``ttl_seconds``
using ``dadaia_workspace.core.lock_liveness.is_stale_session`` (single source
of truth — v0.1.7 T-017-10).

Security (OWASP A03, A06):
- JSON files are parsed defensively; malformed/missing-field files are skipped.
- No user-controlled input is reflected verbatim in error messages.
- No credentials, PII, or code appear in the session schema.
"""

from __future__ import annotations

import contextlib
import datetime
import json
import logging
from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.core.lock_liveness import is_stale_session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COLUMN_KEYS = ("backlog", "release_def", "impl_review", "closure")

_MODE_TO_COLUMN: dict[str, str] = {
    "READ": "backlog",
    "SPEC": "release_def",
    "BOUND_IMPLEMENTATION": "impl_review",
    "BOUND_REVIEW": "impl_review",
}

# No session mode currently maps to the "closure" column.
# It is always present but empty until a closure-phase session mode is introduced.
_FALLBACK_COLUMN = "backlog"

_REQUIRED_FIELDS: frozenset[str] = frozenset({"session_id", "mode", "context"})

_DEFAULT_TTL_SECONDS = 300


# ---------------------------------------------------------------------------
# View factory
# ---------------------------------------------------------------------------


def render_api_kanban(
    workspace_root: Path,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a view callable for GET /api/kanban.

    Parameters
    ----------
    workspace_root:
        Absolute path to the workspace root directory.  Session files are
        expected at ``<workspace_root>/.dadaia/sessions/*.json``.
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        sessions_dir = workspace_root / ".dadaia" / "sessions"
        generated_at = datetime.datetime.now(tz=datetime.UTC).isoformat()

        if not sessions_dir.exists():
            payload: dict[str, object] = {
                "generated_at": generated_at,
                "swimlanes": [],
            }
            return (200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))

        # Collect valid sessions from all *.json files in the sessions dir.
        # Key: context name → column key → list of SessionCard dicts
        lanes: dict[str, dict[str, list[dict[str, object]]]] = {}

        for json_file in sorted(sessions_dir.glob("*.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                logger.debug("api_kanban: skipping unparseable file %s", json_file.name)
                continue

            # Validate required fields.
            missing = _REQUIRED_FIELDS - set(data.keys())
            if missing:
                logger.debug(
                    "api_kanban: skipping %s — missing fields: %s",
                    json_file.name,
                    missing,
                )
                continue

            session_id: str = str(data["session_id"])
            mode: str = str(data["mode"])
            context: str = str(data["context"])
            release: str | None = data.get("release")
            runtime: str | None = data.get("runtime")
            pid: int | None = data.get("pid")
            last_seen_at: str = str(data.get("last_seen_at", ""))
            ttl_seconds: int = _DEFAULT_TTL_SECONDS
            with contextlib.suppress(TypeError, ValueError):
                ttl_seconds = int(data.get("ttl_seconds", _DEFAULT_TTL_SECONDS))

            stale = is_stale_session(last_seen_at, ttl_seconds)
            column = _MODE_TO_COLUMN.get(mode, _FALLBACK_COLUMN)

            card: dict[str, object] = {
                "session_id": session_id,
                "mode": mode,
                "release": release,
                "runtime": runtime,
                "pid": pid,
                "last_seen_at": last_seen_at if last_seen_at else None,
                "is_stale": stale,
            }

            if context not in lanes:
                lanes[context] = {key: [] for key in _COLUMN_KEYS}
            lanes[context][column].append(card)

        # Sort swimlanes by context name; sort cards within each column by session_id.
        swimlanes: list[dict[str, object]] = []
        for context_name in sorted(lanes.keys()):
            columns = lanes[context_name]
            sorted_columns: dict[str, list[dict[str, object]]] = {}
            for col_key in _COLUMN_KEYS:
                sorted_columns[col_key] = sorted(
                    columns[col_key],
                    key=lambda c: str(c.get("session_id", "")),
                )
            swimlanes.append(
                {
                    "context": context_name,
                    "columns": sorted_columns,
                }
            )

        payload = {
            "generated_at": generated_at,
            "swimlanes": swimlanes,
        }
        return (200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))

    return _view
