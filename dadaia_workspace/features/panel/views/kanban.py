"""Kanban view — GET /api/kanban.

API version: **kanban-v2** (lifecycle-truth board).

Prior to v2 (kanban-v1) the board dumped *every* parseable session record under
``.dadaia/sessions/*.json`` as a card, regardless of liveness, and rendered the
``runtime`` field (literally ``"unknown"`` in every bind record) twice while never
showing mode or release. The result was a wall of ``sess_xxxx / unknown / unknown ·
9h ago`` cards — dead sessions that never aged out. v2 makes the board mean something.

What a swimlane is (v2)
-----------------------
**One swimlane per ALIVE Spec Context Project**, read from the context registry
(``.dadaia/states/spec_contexts.json`` via the injected ``alive_contexts`` provider) —
NOT "whatever contexts happen to have session files". A context with no live session and
no active release still gets a lane (so the operator sees the project exists, idle).

What lands in each column (v2)
------------------------------
Two kinds of card live on the board:

1. **Release card** (primary, one per lane at most). Read from the context's
   ``repos/<slug>/specs/releases/ACTIVE.md`` (``release:`` + ``phase:``). The active
   release's *phase* decides the column:

       Phase (ACTIVE.md)                     Column         Label
       ------------------------------------  -------------  -----------------------
       DEFINITION / DISCOVERY / SPEC / PLAN  release_def    Release Definition
       TASKS / IMPLEMENTATION / REVIEW       impl_review    Implementation + Review
       CLOSURE                               closure        Closure
       ARCHIVED / none / (no ACTIVE.md)      (no card)      —

   ``card_kind: "release"``. Carries ``release`` + ``phase``; it is never "stale".

2. **Session card** — emitted ONLY for **live** sessions. A session is live when its
   recorded ``pid`` is still running (injected ``pid_probe``) **or**, when no probe /
   no usable pid is available, its heartbeat (``last_seen_at`` vs ``ttl_seconds``) is
   still fresh. Stale-and-dead records are dropped, never rendered. A live session card
   shows meaningful text: its mode and, if bound, its release + relative age — never the
   literal string "unknown" (absent fields are omitted by the renderer).

   Session-mode → column (the honest mapping):

       READ                              observers   (an Observers strip, NOT Backlog)
       SPEC                              release_def
       BOUND_IMPLEMENTATION / _REVIEW    impl_review
       unrecognised                      observers   (fail-safe: never drop a live one)

   The legacy ``backlog`` column was a dumping ground for READ binds. READ sessions are
   passive observers, not backlog work, so v2 routes them to a dedicated ``observers``
   strip and the ``backlog`` column is retired from the response.

Response schema (kanban-v2, normative)
---------------------------------------
    GET /api/kanban →
      {
        "schema": "kanban-v2",
        "generated_at": "<ISO-8601 UTC>",
        "swimlanes": [ SwimLane, ... ]
      }
    SwimLane = {
      "context": "<context name>",
      "columns": { "release_def": [Card], "impl_review": [Card], "closure": [Card] },
      "observers": [Card]
    }
    Card (release) = {
      "card_kind": "release", "release": "<id>", "phase": "<PHASE>"
    }
    Card (session) = {
      "card_kind": "session", "session_id": "<id>", "mode": "<MODE>",
      "release": "<id>"|null, "started_at": "<ISO>"|null,
      "last_seen_at": "<ISO>"|null, "age_seconds": <int>|null
    }

Security (OWASP A03, A06):
- JSON / Markdown files are parsed defensively; malformed/missing-field files are
  skipped, never reflected verbatim in an error.
- Context names and slugs from the registry are filename components only; path
  construction stays inside the workspace tree (no user-controlled traversal).
- No credentials, PII, or code appear in the session/release schema.
"""

from __future__ import annotations

import contextlib
import datetime
import json
import logging
import re
from collections.abc import Callable, Iterable
from pathlib import Path

from dadaia_workspace.core.lock_liveness import is_stale_session
from dadaia_workspace.features.spec_context import session_identity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Lifecycle columns rendered on every swimlane (left → right). ``backlog`` is retired;
#: READ sessions live in the separate ``observers`` strip (see module docstring).
_COLUMN_KEYS: tuple[str, ...] = ("release_def", "impl_review", "closure")

#: ACTIVE.md ``phase:`` token → lifecycle column. Phases not listed (ARCHIVED) produce
#: no release card.
_PHASE_TO_COLUMN: dict[str, str] = {
    "DISCOVERY": "release_def",
    "DEFINITION": "release_def",
    "SPEC": "release_def",
    "PLAN": "release_def",
    "TASKS": "impl_review",
    "IMPLEMENTATION": "impl_review",
    "REVIEW": "impl_review",
    "CLOSURE": "closure",
}

#: Session ``mode:`` → lifecycle column. READ + unrecognised modes go to ``observers``.
_MODE_TO_COLUMN: dict[str, str] = {
    "SPEC": "release_def",
    "BOUND_IMPLEMENTATION": "impl_review",
    "BOUND_REVIEW": "impl_review",
}

_OBSERVERS_KEY = "observers"

_REQUIRED_FIELDS: frozenset[str] = frozenset({"session_id", "mode", "context"})

_DEFAULT_TTL_SECONDS = 300

#: ``release:`` / ``phase:`` lines in a release ACTIVE.md (YAML-ish frontmatter).
_RELEASE_RE = re.compile(r"^release:\s*(.+?)\s*$", re.MULTILINE)
_PHASE_RE = re.compile(r"^phase:\s*(.+?)\s*$", re.MULTILINE)

#: Context slugs are filename components — fence path traversal (CWE-22/CWE-59).
_SLUG_RE = re.compile(r"\A[A-Za-z0-9_-]+\Z")

#: Provider signature: returns ``[(context_name, repo_slug), ...]`` for ALIVE contexts.
AliveContextsProvider = Callable[[], Iterable[tuple[str, str]]]

#: pid liveness probe ``(pid) -> alive?``; ``None`` ⇒ heartbeat-only liveness.
PidProbe = Callable[[int], bool]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_active_release(workspace_root: Path, repo_slug: str) -> tuple[str, str] | None:
    """Return ``(release_id, phase)`` from a context's release ACTIVE.md, or ``None``.

    ``None`` when the file is absent, unreadable, declares ``release: none``, or carries
    no parseable ``release:``/``phase:`` pair. Fail-soft: never raises.
    """
    if not _SLUG_RE.match(repo_slug):
        return None
    active = workspace_root / "repos" / repo_slug / "specs" / "releases" / "ACTIVE.md"
    try:
        text = active.read_text(encoding="utf-8")
    except OSError:
        return None
    rel_m = _RELEASE_RE.search(text)
    phase_m = _PHASE_RE.search(text)
    if rel_m is None or phase_m is None:
        return None
    release = rel_m.group(1).strip()
    phase = phase_m.group(1).strip()
    if not release or release.lower() == "none":
        return None
    return (release, phase.upper())


def _session_is_live(
    *,
    pid: object,
    last_seen_at: str,
    ttl_seconds: int,
    pid_probe: PidProbe | None,
) -> bool:
    """Return ``True`` when a session should render as a live card.

    Liveness = recorded pid demonstrably alive (when a probe + usable pid exist), else a
    fresh heartbeat. This mirrors the lease's TTL-floor + pid-veto contract: a probe can
    *keep* an otherwise heartbeat-stale session alive, but never makes a heartbeat-fresh
    one dead. A probe that raises is swallowed → fall back to the heartbeat verdict.
    """
    if pid_probe is not None and isinstance(pid, int) and pid > 0:
        with contextlib.suppress(Exception):
            if pid_probe(pid):
                return True
    return not is_stale_session(last_seen_at, ttl_seconds)


def _age_seconds(last_seen_at: str, *, now: datetime.datetime) -> int | None:
    if not last_seen_at:
        return None
    try:
        seen = datetime.datetime.fromisoformat(last_seen_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=datetime.UTC)
    return max(0, int((now - seen).total_seconds()))


def _empty_lane() -> dict[str, list[dict[str, object]]]:
    lane: dict[str, list[dict[str, object]]] = {key: [] for key in _COLUMN_KEYS}
    lane[_OBSERVERS_KEY] = []
    return lane


# ---------------------------------------------------------------------------
# View factory
# ---------------------------------------------------------------------------


def render_api_kanban(
    workspace_root: Path,
    *,
    alive_contexts: AliveContextsProvider | None = None,
    pid_probe: PidProbe | None = None,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a view callable for GET /api/kanban (kanban-v2).

    Parameters
    ----------
    workspace_root:
        Absolute path to the workspace root. Session records are read from
        ``<root>/.dadaia/sessions/*.json``; release state from
        ``<root>/repos/<slug>/specs/releases/ACTIVE.md``.
    alive_contexts:
        Injected provider returning ``(context_name, repo_slug)`` for each ALIVE Spec
        Context — the swimlane set. ``None`` (the default) makes the board
        session-derived for back-compat: a lane is created for every context that has a
        live session, but no release cards are emitted (no registry → no ACTIVE.md
        resolution). The composition root injects the real provider.
    pid_probe:
        Injected ``(pid) -> alive?`` liveness probe (the container's ``OsProcessProbe``;
        ``features`` never imports the adapter). ``None`` ⇒ heartbeat-only liveness.
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        now = datetime.datetime.now(tz=datetime.UTC)
        generated_at = now.isoformat()

        # Seed lanes from the ALIVE context registry so every live project has a
        # swimlane even with zero sessions. context name → columns dict.
        lanes: dict[str, dict[str, list[dict[str, object]]]] = {}
        slug_by_context: dict[str, str] = {}
        if alive_contexts is not None:
            with contextlib.suppress(Exception):
                for ctx_name, repo_slug in alive_contexts():
                    name = str(ctx_name)
                    lanes.setdefault(name, _empty_lane())
                    slug_by_context[name] = str(repo_slug)

        # 1. Release cards — the primary lifecycle truth per lane.
        for ctx_name, repo_slug in slug_by_context.items():
            resolved = _read_active_release(workspace_root, repo_slug)
            if resolved is None:
                continue
            release_id, phase = resolved
            column = _PHASE_TO_COLUMN.get(phase)
            if column is None:
                continue  # ARCHIVED or unknown phase → no card.
            lanes[ctx_name][column].append(
                {
                    "card_kind": "release",
                    "release": release_id,
                    "phase": phase,
                }
            )

        # 2. Live session cards.
        for json_file in session_identity.iter_session_records(workspace_root):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                logger.debug("api_kanban: skipping unparseable file %s", json_file.name)
                continue
            if not isinstance(data, dict):
                continue
            if _REQUIRED_FIELDS - set(data.keys()):
                logger.debug("api_kanban: skipping %s — missing required fields", json_file.name)
                continue

            mode = str(data["mode"])
            context = str(data["context"])
            pid = data.get("pid")
            last_seen_at = str(data.get("last_seen_at") or "")
            ttl_seconds = _DEFAULT_TTL_SECONDS
            with contextlib.suppress(TypeError, ValueError):
                ttl_seconds = int(data.get("ttl_seconds", _DEFAULT_TTL_SECONDS))

            if not _session_is_live(
                pid=pid,
                last_seen_at=last_seen_at,
                ttl_seconds=ttl_seconds,
                pid_probe=pid_probe,
            ):
                continue  # dead / stale record → not a card.

            # When no registry was injected, fall back to session-derived lanes.
            if context not in lanes:
                if alive_contexts is not None:
                    # Registry present but this context is not ALIVE — drop the orphan.
                    continue
                lanes[context] = _empty_lane()

            column = _MODE_TO_COLUMN.get(mode, _OBSERVERS_KEY)
            started_at = data.get("bound_at") or data.get("created_at")
            card: dict[str, object] = {
                "card_kind": "session",
                "session_id": str(data["session_id"]),
                "mode": mode,
                "release": data.get("release"),
                "started_at": str(started_at) if started_at else None,
                "last_seen_at": last_seen_at or None,
                "age_seconds": _age_seconds(last_seen_at, now=now),
            }
            lanes[context][column].append(card)

        # Build the sorted response. Sort lanes by context; release cards first then
        # session cards (by session_id) within each lifecycle column.
        swimlanes: list[dict[str, object]] = []
        for context_name in sorted(lanes.keys()):
            cols = lanes[context_name]
            sorted_columns: dict[str, list[dict[str, object]]] = {}
            for col_key in _COLUMN_KEYS:
                sorted_columns[col_key] = sorted(cols[col_key], key=_card_sort_key)
            observers = sorted(cols[_OBSERVERS_KEY], key=_card_sort_key)
            swimlanes.append(
                {
                    "context": context_name,
                    "columns": sorted_columns,
                    "observers": observers,
                }
            )

        payload: dict[str, object] = {
            "schema": "kanban-v2",
            "generated_at": generated_at,
            "swimlanes": swimlanes,
        }
        return (200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))

    return _view


def _card_sort_key(card: dict[str, object]) -> tuple[int, str]:
    """Release cards sort before session cards; sessions sort by session_id."""
    if card.get("card_kind") == "release":
        return (0, str(card.get("release", "")))
    return (1, str(card.get("session_id", "")))
