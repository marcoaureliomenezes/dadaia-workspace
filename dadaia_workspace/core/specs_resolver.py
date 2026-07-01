"""Session-bound specs directory resolution helpers."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import typer

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

#: Path-traversal allowlist (CWE-22/CWE-59). ``DADAIA_SESSION_ID`` becomes a filename
#: component, so it must be validated before use — mirrors ``session_identity._NAME_RE``.
_SESSION_ID_RE = re.compile(r"[A-Za-z0-9_-]+")

#: Bind-epoch marker name allowlist (W1-8). A marker's filename IS the context slug and
#: becomes a ``repos/<slug>/specs`` path component, so it is validated before use
#: (CWE-22/CWE-59 defence in depth) — mirrors ``session_identity._NAME_RE``.
_CONTEXT_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")


def _session_context(workspace_root: Path) -> str | None:
    """Read the ``context`` field of the bound session record (fail-soft).

    The session-record path schema (``.dadaia/sessions/<id>.json``) is canonically owned
    by ``features.spec_context.session_identity`` (WS-R3). This ``core`` resolver cannot
    import that ``features`` module without violating the layering law (constitution §6 —
    ``core`` imports nothing upward), so it performs a self-contained, read-only,
    fail-soft read of the same canonical path. It never writes, never opens the pointer
    namespace, and is recorded as the documented core-layer reader in the
    ``test_session_store_ownership`` residue contract.
    """
    session_id = os.environ.get("DADAIA_SESSION_ID")
    if not session_id or not _SESSION_ID_RE.fullmatch(session_id):
        return None
    session_file = workspace_root / ".dadaia" / "sessions" / f"{session_id}.json"
    if not session_file.is_file():
        return None
    try:
        data = json.loads(session_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    context = data.get("context")
    return str(context) if context else None


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
        return candidate.resolve()

    raise typer.BadParameter(
        "Could not resolve specs_dir. Pass --specs-dir or bind a context with "
        "`eval $(dadaia context bind <name> --mode read)`."
    )
