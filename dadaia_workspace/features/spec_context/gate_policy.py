"""Path classifier and decision policy for the merged SDD PreToolUse gate.

Races between sessions are surfaced through advisory presence and never prevented;
there is no session mode. Protected CLI session records remain fail-closed against
file-tool writes.

**The gate blocks three things (0.4.7 FR1).** A PROTECTED write (CLI-owned session
records and projected law files); a MUTATING write into a repo the session's bind does
not own; and — in ``hooks/root_whitelist`` — a new workspace-root entry. There is no
fourth block and no path class beyond ``ADDITIVE``/``MUTATING``/``PROTECTED``.

The MEMORY class and its phase rule are DELETED, with the gate's ``_RELEASE.json``
read behind them: the gate reads no SDD artifact (``DADAIA.md`` §3.5), and every gate
Stall in the bug ledger came from that read resolving an empty phase
(``sdd-gate-memory-phase-resolves-empty…``, ``minted-feature-branch-without-live-
release-blocks-every-memory-write``, ``context-bind-implementation-requires-release-id-
stall-when-none-live``). Memory authorship is constitution discipline, audited by the
drift pillar, never gated. The READ-mode self-block is deleted with it — its only
documented way out was a bind flag that no longer exists.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.features.spec_context import presence

__all__ = ["Decision", "PathClass", "classify_path", "evaluate"]

#: Throttle window (seconds) for the advisory concurrency warning (v0.1.76 FR1). A
#: second write inside this window from the same session emits no repeat warning — the
#: throttle marker lives at ``.dadaia/tmp/presence-warn-<sid>-<ctx>`` (mtime-based).
_ADVISORY_THROTTLE_SECONDS = 300

#: Ordered ADDITIVE prefixes — always allowed.
#: Parallel audit sessions use collision-safe directories, named per the single home
#: ``core.workspace_layout.AUDIT_DIR_NAME_RE`` (v0.5.0 T-050-25A — this comment used to
#: repeat that shape in prose; one fact, one place now).
#:
#: WS-R1 split (FR-R1-01/05): the ``specs/`` ADDITIVE classes apply both at the
#: workspace root *and* relative to a context root (``repos/<slug>/``). The ``.dadaia/``
#: classes are workspace-root-only — ``.dadaia/`` is forbidden inside any repo working
#: tree (root AGENTS.md repo-cleanliness law), so there is no in-repo ``.dadaia/``
#: ADDITIVE class to honor.
_SPECS_ADDITIVE_PREFIXES: tuple[str, ...] = (
    "specs/backlog/",
    "specs/bugs/",
    "specs/audits/",
)
# Derived from the zone registry (OUTPUT + EPHEMERAL zones) — never a second literal.
_ADDITIVE_DADAIA_PREFIXES: tuple[str, ...] = workspace_layout.additive_prefixes()
#: A path under ``repos/<slug>/`` whose context-relative remainder matches one of these
#: ``specs/`` class prefixes is classified by that class. Every other in-repo remainder —
#: production source AND unlisted ``specs/<other>`` files (e.g. ``specs/constitution.md``)
#: — is MUTATING (FR-R1-04): a ``ctx_rel`` matching no class NEVER falls through to UNGATED.
#: .dadaia/sessions/ holds protected, caller-owned bind records. Agents must not write
#: these via file tools; only the CLI/bootstrap may write them.
_PROTECTED_PREFIX = ".dadaia/sessions/"
#: SEC-01 block reason emitted by the Python hook ``dadaia_workspace.hooks.sdd_gate``,
#: which delegates here so PROTECTED has a single message source.
_PROTECTED_MESSAGE = (
    "[GATE] .dadaia/sessions/ is protected CLI-owned bind state. Agents must not write "
    "here via file tools. Blocked to preserve caller session identity integrity "
    "(SEC-01 / CWE-284).\n"
    "fix: .dadaia/.venv/bin/dadaia context bind <ctx>"
)
#: Projected LAW files. ``DADAIA.md`` is the workspace system prompt and the sole
#: always-on rule file the library ships; the ``AGENTS.md``/``CLAUDE.md`` pair is its
#: scoped/bridge counterpart. In an INSTANTIATED workspace these are human-only: an agent
#: changes the law by editing ``dadaia_workspace/public/`` and re-projecting, never by
#: writing the projection. Matched as exact relative paths (workspace root, harness dirs,
#: and each ``repos/<slug>/`` root) so library sources and test fixtures — which live
#: deeper — are never caught.
_LAW_BASENAMES: frozenset[str] = workspace_layout.LAW_BASENAMES
_LAW_HARNESS_DIRS: frozenset[str] = workspace_layout.LAW_HARNESS_DIRS
_LAW_MESSAGE = (
    "[GATE] '{path}' is a projected law file (the workspace system prompt / scoped "
    "AGENTS.md). In an instantiated workspace only a human operator edits it by hand; "
    "an agent changes the law at its source and re-projects.\n"
    "The source is dadaia_workspace/public/; this re-projects it:\n"
    "fix: .dadaia/.venv/bin/dadaia public stage && .dadaia/.venv/bin/dadaia public "
    "install --target all"
)

#: BLOCK message for a MUTATING write into a repo outside the Bind's scope (FR1, Q1).
#: Only ``repos/<slug>/`` is scope-judged: a workspace-root path is in scope under any
#: bind, and a slug no Context registers is unattributable, so it ALLOWS (fail-open).
_SCOPE_BLOCK_MESSAGE = (
    "[GATE] '{rel_path}' writes into repo '{slug}', owned by context '{owner}' — this "
    "session is bound to '{bound}', whose scope is: {scope}.\n"
    "fix: .dadaia/.venv/bin/dadaia context bind {owner}"
)

#: The default session id when no harness-native id resolves (``hooks/sdd_gate.py``'s
#: ``resolve_session_id(payload, default="anon-session")``). FR5: an anonymous identity
#: never creates a presence record — it degrades presence accuracy only, never the write
#: (v0.1.76, kills the anon-session dual-writer facet of the CRITICAL bug at the root).
_ANON_SESSION_ID = "anon-session"


def _advisory_marker_name(session_id: str, ctx: str) -> str:
    """The advisory throttle marker's filename — validated by :func:`presence.throttled`/
    :func:`presence.stamp_throttle` themselves (release 0.5.1 K2: the ONE
    mtime-throttle-marker idiom, replacing this module's own copy)."""
    return f"presence-warn-{session_id}-{ctx}"


def _advisory_message(ctx: str, rel_path: str, others: list[presence.PresenceRecord]) -> str:
    """Build the one-line advisory naming every other live session (FR1).

    Names each other session's id, runtime, and last-seen timestamp; states plainly that
    the write was ALLOWED — this is a signal, never a block.
    """
    parts = [
        f"{rec.session_id!r} (runtime={rec.runtime}, last seen at {rec.last_seen_at or 'unknown'})"
        for rec in others
    ]
    names = "; ".join(parts)
    return (
        f"[PRESENCE] '{rel_path}' write ALLOWED in context {ctx!r}. Other live session(s) "
        f"present: {names}. Races between sessions are accepted and surfaced, never "
        "blocked — no action required."
    )


class PathClass(Enum):
    """Three classes, no fourth (0.4.7 FR1). A workspace-root path matching no
    ADDITIVE or PROTECTED prefix is MUTATING — there is no UNGATED fall-through."""

    ADDITIVE = "ADDITIVE"
    MUTATING = "MUTATING"
    PROTECTED = "PROTECTED"


class Decision(Enum):
    ALLOW = "allow"
    BLOCK = "block"


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _is_specs_additive(spec_rel: str) -> bool:
    """True when a root- or context-relative ``specs/`` path is ADDITIVE."""
    return any(spec_rel.startswith(prefix) for prefix in _SPECS_ADDITIVE_PREFIXES)


def _context_relative(p: str) -> str | None:
    """Return the remainder of ``p`` after a ``repos/<slug>/`` prefix, else ``None``.

    ``repos/`` alone or ``repos/<slug>`` with no trailing remainder yields ``""`` (still
    in-repo, so the caller classifies it MUTATING). A non-``repos/`` path yields ``None``.
    """
    if not p.startswith("repos/"):
        return None
    rest = p[len("repos/") :]
    slash = rest.find("/")
    if slash == -1:
        return ""  # 'repos/<slug>' with no remainder — in-repo, no class match
    return rest[slash + 1 :]


def _is_law_path(rel_path: str) -> bool:
    """True when *rel_path* sits at a structurally fixed projected-law origin — a
    PROTECTED path (0.4.7 FR1 folded the LAW class into PROTECTED; the two share one
    verdict and differ only in the message that names the way out).

    Static, ORIGIN-only floor (v0.4.5 FR1): the workspace root or a fixed harness dir
    (``_LAW_HARNESS_DIRS``). ``repos/<slug>/`` never matches either shape, so a repo's
    own AGENTS.md/CLAUDE.md is never LAW (closes sdd-gate-blocks-fresh-repo-root-agents-md
    + repo-agents-md-law-gate-contradicts-template) — never reads the manifest (CWE-284).
    """
    parts = rel_path.split("/")
    if len(parts) == 1:
        return parts[0] in _LAW_BASENAMES
    parent = "/".join(parts[:-1])
    return parent in _LAW_HARNESS_DIRS and parts[-1] in _LAW_BASENAMES


def classify_path(rel_path: str) -> PathClass:
    """Classify a workspace-relative path into one of THREE classes; first match wins.

    A path under ``repos/<slug>/`` is classified by its **context-relative** remainder
    using the same ``specs/`` ADDITIVE prefixes that govern workspace-root paths; every
    other remainder is MUTATING. A workspace-root path is PROTECTED (session records,
    projected law), ADDITIVE (the ``specs/`` and zone-registry prefixes), or MUTATING —
    there is no UNGATED fall-through, so nothing at the root escapes classification.
    """
    p = rel_path.lstrip("/")
    if _is_law_path(p) or p.startswith(_PROTECTED_PREFIX):
        return PathClass.PROTECTED

    ctx_rel = _context_relative(p)
    if ctx_rel is not None:
        return PathClass.ADDITIVE if _is_specs_additive(ctx_rel) else PathClass.MUTATING

    if _is_specs_additive(p) or any(p.startswith(x) for x in _ADDITIVE_DADAIA_PREFIXES):
        return PathClass.ADDITIVE
    return PathClass.MUTATING


def _scope_block(
    rel_path: str,
    bound_context: str | None,
    bound_repos: frozenset[str],
    target_slug: str | None,
    target_owner: str | None,
) -> str | None:
    """The scope refusal for a MUTATING write, or ``None`` when the write is in scope.

    The bind is PLAIN DATA here — the name the session bound and the repo slugs that
    scope covers. Resolving them is the hook's job (``hooks/sdd_gate._evaluate_target``
    already resolves the Invocation once); this module imports nothing from
    ``core.invocation`` (P-09: the resolution seam has a single home).
    """
    if bound_context is None or target_slug is None or target_owner is None:
        return None
    if target_slug in bound_repos or target_owner == bound_context:
        return None
    return _SCOPE_BLOCK_MESSAGE.format(
        rel_path=rel_path,
        slug=target_slug,
        owner=target_owner,
        bound=bound_context,
        scope=", ".join(sorted(bound_repos)) or "no registered repo",
    )


def evaluate(
    workspace: Path,
    rel_path: str,
    *,
    ctx: str,
    session_id: str,
    bound_context: str | None = None,
    bound_repos: frozenset[str] = frozenset(),
    target_slug: str | None = None,
    target_owner: str | None = None,
    clock: Callable[[], datetime] = _utcnow,
    runtime: str = "unknown",
    pid: int | None = None,
) -> tuple[Decision, str]:
    """Return the gate decision for one write target — the fail-safe contract.

    Three blocks, in order: PROTECTED (fail-CLOSED, the projected-law message or the
    session-record message), then — for a MUTATING write — the bind's SCOPE, received as
    plain data (*bound_context* / *bound_repos*), never re-resolved here. Everything
    else ALLOWS, upserting advisory presence.

    SCOPE (FR1, Q1): only ``repos/<slug>/`` is scope-judged. *target_slug* is the repo
    the write lands in and *target_owner* the context that registers it; the write is
    refused only when the session is BOUND, some context demonstrably owns that slug,
    and it is not the bound context's own (*bound_repos* = main + associated). An
    unbound session, a workspace-root path, and a slug no context registers all ALLOW —
    the gate cannot attribute them, and fail-open is the posture.

    NO-LOCKS DOCTRINE (v0.1.76): a MUTATING write is NEVER blocked on another session.
    It upserts an advisory :mod:`presence` record for this ``(ctx, session_id)`` and,
    when another live session is visible on the same context, ALLOWS with a throttled
    one-line advisory. Presence I/O never raises (FR2).

    ``runtime``/``pid`` are recorded into the presence record. An anonymous session id
    (``anon-session``) never creates one (FR5): the write is still allowed, there is
    simply nothing to be advisory about.
    """
    cls = classify_path(rel_path)

    # PROTECTED is the sole fail-closed path and is evaluated before fail-open branches.
    if cls == PathClass.PROTECTED:
        if _is_law_path(rel_path.lstrip("/")):
            return Decision.BLOCK, _LAW_MESSAGE.format(path=rel_path)
        return Decision.BLOCK, _PROTECTED_MESSAGE

    if cls == PathClass.ADDITIVE:
        return Decision.ALLOW, ""

    scope_block = _scope_block(rel_path, bound_context, bound_repos, target_slug, target_owner)
    if scope_block is not None:
        return Decision.BLOCK, scope_block

    # MUTATING mode: advisory presence, never a peer-session block.
    # anon-session (no harness-native id resolved, FR5) creates no presence record — the
    # write is still allowed, there is simply nothing to be advisory about. The whole
    # block is wrapped fail-safe (AC-04 defense-in-depth): ``presence`` already swallows
    # its own errors internally, but a MUTATING write must NEVER be able to raise out of
    # this function regardless of what future presence code does.
    try:
        if session_id and session_id != _ANON_SESSION_ID and ctx:
            presence.upsert(workspace, ctx, session_id, runtime=runtime, pid=pid or 0)
            others = presence.others_alive(workspace, ctx, session_id)
            marker = _advisory_marker_name(session_id, ctx)
            now = time.time()
            if others and not presence.throttled(
                workspace, marker, window_seconds=_ADVISORY_THROTTLE_SECONDS, now=now
            ):
                presence.stamp_throttle(workspace, marker)
                message = _advisory_message(ctx, rel_path, others)
                return Decision.ALLOW, message
    except Exception:  # noqa: BLE001 — fail-safe contract (AC-04): never fail-dead.
        return Decision.ALLOW, ""
    return Decision.ALLOW, ""
