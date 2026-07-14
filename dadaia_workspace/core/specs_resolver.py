"""Session-bound specs directory resolution helpers."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import typer

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.record_liveness import is_stale
from dadaia_workspace.core.session_env import harness_session_id
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

#: Path-traversal allowlist (CWE-22/CWE-59). ``DADAIA_SESSION_ID`` becomes a filename
#: component, so it must be validated before use — mirrors ``session_identity._NAME_RE``.
_SESSION_ID_RE = re.compile(r"[A-Za-z0-9_-]+")

#: Session-record liveness field names (mirrors ``session_identity.SESSION_HEARTBEAT_FIELD`` /
#: ``SESSION_GC_TTL_FIELD``; re-stated here because ``core`` cannot import that ``features``
#: owner — constitution §6). Used by the FR4 harness-channel staleness guard below.
_SESSION_HEARTBEAT_FIELD = "last_seen_at"
_SESSION_TTL_FIELD = "ttl_seconds"

#: Bind-epoch marker name allowlist (W1-8). A marker's filename IS the context slug and
#: becomes a ``repos/<slug>/specs`` path component, so it is validated before use
#: (CWE-22/CWE-59 defence in depth) — mirrors ``session_identity._NAME_RE``. Reused
#: directly (not duplicated) by ``cli._specs_resolution.resolve_context_for_cli`` for the
#: SAME reason at its own *explicit*/``DADAIA_CONTEXT`` rungs (v0.1.80 FR3) — both
#: modules sit in the same import direction (``cli`` -> ``core``), so importing this
#: module-level compiled pattern is a clean reuse, not a layering violation.
_CONTEXT_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")


def _read_session_record(workspace_root: Path, session_id: str) -> dict[str, object] | None:
    """Self-contained, read-only, fail-soft read of ``.dadaia/sessions/<session_id>.json``.

    The session-record path schema is canonically owned by
    ``features.spec_context.session_identity`` (WS-R3). This ``core`` resolver cannot import
    that ``features`` module without violating the layering law (constitution §6 — ``core``
    imports nothing upward), so it re-reads the same canonical path directly. It never writes,
    never opens the pointer namespace, and is the documented core-layer reader in the
    ``test_session_store_ownership`` residue contract.
    """
    if not _SESSION_ID_RE.fullmatch(session_id):
        return None
    session_file = workspace_root / ".dadaia" / "sessions" / f"{session_id}.json"
    if not session_file.is_file():
        return None
    try:
        data = json.loads(session_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _record_context(record: dict[str, object] | None) -> str | None:
    """Return the ``context`` field of a session record, or ``None``."""
    if record is None:
        return None
    context = record.get("context")
    return str(context) if context else None


def _session_record_live(record: dict[str, object]) -> bool:
    """FR4 staleness guard: a harness-keyed session record is live iff its heartbeat is fresh.

    Reuses ``core.record_liveness.is_stale`` (the canonical TTL predicate) by mapping the
    session record's ``last_seen_at`` / ``ttl_seconds`` onto its ``heartbeat`` / ``ttl``
    fields. ``pid_probe`` is intentionally ``None`` (TTL-only): the record's ``pid`` is the
    transient bind-CLI pid, dead by construction (ADR-8), so heartbeat-freshness — renewed by
    the PostToolUse heartbeat on ``sessions/<harness_id>.json`` — is the liveness signal. A
    record with no/old ``last_seen_at`` is stale ⇒ NOT live, so an inherited/stale harness id
    can never resolve to a foreign bound context.
    """
    probe = {
        "heartbeat": record.get(_SESSION_HEARTBEAT_FIELD),
        "ttl": record.get(_SESSION_TTL_FIELD),
    }
    return not is_stale(probe)


def _session_context(workspace_root: Path) -> str | None:
    """Resolve the bound context from a session record (fail-soft).

    Two channels, in order:

    1. **Eval flow** — an explicit ``DADAIA_SESSION_ID`` addresses the CLI-minted session
       record directly (unchanged; no liveness gate — the operator exported it deliberately).
    2. **Harness-native channel (v0.1.55 FR4)** — when ``DADAIA_SESSION_ID`` is absent, resolve
       via the harness-native session id (``CODEX_SESSION_ID`` / ``CLAUDE_CODE_SESSION_ID``,
       the single source ``core.session_env``). ``bind`` persists a session record keyed by
       that id, so a codex/claude CLI call — whose process is NOT a descendant of the bind, so
       the ancestry-marker path can never attribute it — resolves its bound context
       deterministically, **ahead of** the ancestry path. Gated by the staleness guard: a
       harness id resolves ONLY when its record is LIVE (never a blind fallback).
    """
    session_id = os.environ.get("DADAIA_SESSION_ID")
    if session_id:
        return _record_context(_read_session_record(workspace_root, session_id))

    harness_id = harness_session_id()
    if harness_id:
        record = _read_session_record(workspace_root, harness_id)
        if record is not None and _session_record_live(record):
            return _record_context(record)
    return None


def _marker_chain(entry: Path) -> list[int]:
    """Read a bind-epoch marker's nearest-first ancestry pid chain (fail-soft).

    Each non-empty line is parsed as a positive integer; blank/garbage lines are skipped.
    Returns ``[]`` for a legacy/empty marker, an all-garbage marker, or any OS error. This
    is the ``core``-layer, self-contained mirror of
    ``features.spec_context.session_identity.read_bind_epoch_pids`` — ``core`` cannot import
    that ``features`` module (constitution §6), so it re-reads the canonical marker shape
    directly, read-only.
    """
    try:
        text = entry.read_text(encoding="utf-8")
    except OSError:
        return []
    pids: list[int] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = int(stripped)
        except ValueError:
            continue
        if value > 0:
            pids.append(value)
    return pids


def _persisted_bind_context(
    workspace_root: Path, ancestry_pids: frozenset[int] | None = None
) -> str | None:
    """Resolve the context of the single bind-epoch marker attributed to this session.

    W1-8 (T-47-17), v0.1.47 ancestry-chain amendment. After the ``DADAIA_CONTEXT`` env var
    and the bound session record, a workspace shell that ran ``dadaia context bind <ctx>``
    still exports no env — but the bind wrote ``.dadaia/states/bind_epoch/<ctx>`` recording
    the bind process's nearest-first ancestry pid chain (W1-7). A marker is attributable to
    this session when its recorded chain **shares at least one pid** with ``ancestry_pids``
    — the current process's own ancestry chain, supplied by the CLI seam. Membership (not
    single-pid equality) is what survives the ephemeral harness shell: bind and this
    resolver run under DIFFERENT short-lived shells but share the long-lived harness pid
    deeper in both chains.

    ``ancestry_pids=None`` is the DEGRADED mode preserving the pre-v0.1.47 single-getppid
    equality: attribution then uses ``frozenset({os.getppid()})`` (this ``dadaia`` CLI
    child's parent), which for the in-process / same-shell case is exactly the marker's
    recorded pid. It stays pure-stdlib so this ``core`` module needs no upward import
    (constitution §6): exactly like ``_session_context`` above, it performs a
    self-contained, read-only, fail-soft read of the canonical bind-epoch path.

    Exactly ONE attributable marker ⇒ that context name. None, or MORE THAN ONE (ambiguous),
    ⇒ ``None`` (the caller's cwd fallback / error path is unchanged). Legacy/empty markers,
    markers with a disjoint chain, and any OS/parse error are ignored — the fallback is
    best-effort and never raises.
    """
    epoch_dir = workspace_root / ".dadaia" / "states" / "bind_epoch"
    try:
        entries = list(epoch_dir.iterdir())
    except OSError:
        return None
    effective = ancestry_pids if ancestry_pids is not None else frozenset({os.getppid()})
    matched: list[str] = []
    for entry in entries:
        if not _CONTEXT_NAME_RE.fullmatch(entry.name) or not entry.is_file():
            continue
        chain = _marker_chain(entry)
        if chain and not effective.isdisjoint(chain):
            matched.append(entry.name)
    if len(matched) == 1:
        return matched[0]
    return None


def resolve_bound_context_name(
    explicit: str | None = None, *, ancestry_pids: frozenset[int] | None = None
) -> str | None:
    """Resolve the session-bound context name.

    Resolution order is explicit argument, ``DADAIA_CONTEXT``, the bound session file
    addressed by ``DADAIA_SESSION_ID``, then the persisted bind-epoch marker attributed to
    this session's harness ancestry (W1-8 — so a bound workspace shell resolves its context
    with no env). ``ancestry_pids`` (supplied by the CLI seam) is the current process's own
    nearest-first ancestry pid chain, matched by MEMBERSHIP against each marker's recorded
    chain; ``None`` degrades to single-getppid equality. This helper deliberately does not
    inspect retired global context state.
    """
    if explicit:
        return explicit
    env_context = os.environ.get("DADAIA_CONTEXT")
    if env_context:
        return env_context
    try:
        workspace_root = resolve_workspace_root()
    except WorkspaceNotInitializedError:
        return None
    session_context = _session_context(workspace_root)
    if session_context:
        return session_context
    return _persisted_bind_context(workspace_root, ancestry_pids)


def resolve_specs_dir(
    specs_dir: str | None, *, ancestry_pids: frozenset[int] | None = None
) -> Path:
    """Resolve a specs/ directory from explicit input or bound session context.

    ``ancestry_pids`` (the current process's ancestry pid chain, supplied by the CLI seam)
    is threaded into the persisted-bind fallback so a marker written from an ephemeral
    harness shell is attributed by ancestry-chain MEMBERSHIP (W1-8, v0.1.47). ``None``
    preserves the degraded single-getppid equality behavior.
    """
    if specs_dir:
        return Path(specs_dir).resolve()

    cwd = Path.cwd()
    try:
        workspace_root = resolve_workspace_root(cwd)
    except WorkspaceNotInitializedError:
        workspace_root = None

    if workspace_root is not None:
        context = resolve_bound_context_name(ancestry_pids=ancestry_pids)
        if context:
            return (workspace_root / "repos" / context / "specs").resolve()

    candidate = cwd / "specs"
    if candidate.exists():
        # v0.1.50 FR4 (bug bugs-append-bound-session-falls-through-to-cwd-specs):
        # a top-level specs/ AT THE WORKSPACE ROOT violates the root whitelist —
        # never silently write governance artifacts there. Redaction-safe message
        # (no absolute operator-local path echoed).
        if workspace_root is not None and cwd.resolve() == workspace_root.resolve():
            raise typer.BadParameter(
                "Refusing the workspace-root 'specs/' fallback: the Workspace Root "
                "Law forbids a top-level specs/ directory. Bind a context "
                "(`dadaia context bind <name>`) or pass --specs-dir explicitly."
            )
        return candidate.resolve()

    raise typer.BadParameter(
        "Could not resolve specs_dir. Pass --specs-dir or bind a context with "
        "`eval $(dadaia context bind <name> --mode read)`."
    )
