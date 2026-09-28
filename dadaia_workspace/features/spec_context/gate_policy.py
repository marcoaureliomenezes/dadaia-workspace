"""Path classifier and decision policy for the merged SDD PreToolUse gate.

Races between sessions are never prevented; there is no session mode. Protected CLI session records remain fail-closed against
file-tool writes.

**The gate blocks three things (0.4.7 FR1).** A PROTECTED write (CLI-owned session
records and projected law files); a MUTATING write into a repo the session's bind does
not own; and — in ``hooks/root_whitelist`` — a new workspace-root entry. There is no
fourth block and no path class beyond ``ADDITIVE``/``MUTATING``/``PROTECTED``.

The MEMORY class and its phase rule are DELETED, with the gate's ``_RELEASE.json``
read behind them: the gate reads no SDD artifact (the root `AGENTS.md` map §3), and every gate
Stall in the bug ledger came from that read resolving an empty phase
(``sdd-gate-memory-phase-resolves-empty…``, ``minted-feature-branch-without-live-
release-blocks-every-memory-write``, ``context-bind-implementation-requires-release-id-
stall-when-none-live``). Memory authorship is constitution discipline, audited by the
drift pillar, never gated. The READ-mode self-block is deleted with it — its only
documented way out was a bind flag that no longer exists.
"""

from __future__ import annotations

from enum import Enum
from fnmatch import fnmatch
from pathlib import PurePath

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.cli_line import fix_line

__all__ = ["Decision", "PathClass", "classify_path", "evaluate"]

# Derived from the zone registry (OUTPUT + EPHEMERAL zones) — never a second literal.
_ADDITIVE_DADAIA_PREFIXES: tuple[str, ...] = workspace_layout.additive_prefixes()
#: .dadaia/sessions/ holds protected, caller-owned bind records. Agents must not write
#: these via file tools; only the CLI/bootstrap may write them.
_PROTECTED_PREFIX = ".dadaia/sessions/"
#: SEC-01 block reason emitted by the Python hook ``dadaia_workspace.hooks.sdd_gate``,
#: which delegates here so PROTECTED has a single message source.
_PROTECTED_MESSAGE = (
    "[GATE] .dadaia/sessions/ is protected CLI-owned bind state. Agents must not write "
    "here via file tools. Blocked to preserve caller session identity integrity "
    "(SEC-01 / CWE-284).\n"
)
#: PROTECTED also holds every path the install ledger records (the caller passes that
#: set as *projected*): the ledger, not a basename, decides what is projected law.
_LAW_MESSAGE = (
    "[GATE] '{path}' is a projected file (the install ledger records it). In an "
    "instantiated workspace only a human operator edits it by hand; "
    "an agent changes the law at its source and re-projects.\n"
    "The source is dadaia_workspace/public/; this re-projects it:\n"
)

#: BLOCK message for a MUTATING write into a repo outside the Bind's scope (FR1, Q1).
#: Only ``repos/<slug>/`` is scope-judged: a workspace-root path is in scope under any
#: bind, and a slug no Context registers is unattributable, so it ALLOWS (fail-open).
_SCOPE_BLOCK_MESSAGE = (
    "[GATE] '{rel_path}' writes into repo '{slug}', owned by context '{owner}' — this "
    "session is bound to '{bound}', whose scope is: {scope}.\n"
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


def _is_specs_additive(spec_rel: str) -> bool:
    """True when a root- or context-relative ``specs/`` path is ADDITIVE."""
    return any(fnmatch(spec_rel, glob) for glob in workspace_layout.SPECS_ADDITIVE_GLOBS)


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


def classify_path(rel_path: str, projected: frozenset[str] = frozenset()) -> PathClass:
    """Classify a workspace-relative path into one of THREE classes; first match wins.

    A path under ``repos/<slug>/`` is classified by its **context-relative** remainder
    using the same ``specs/`` ADDITIVE prefixes that govern workspace-root paths; every
    other remainder is MUTATING. A workspace-root path is PROTECTED (session records,
    paths in *projected*, the install ledger's), ADDITIVE (the zone-registry prefixes), or MUTATING —
    there is no UNGATED fall-through, so nothing at the root escapes classification.
    """
    p = rel_path.lstrip("/")
    if p in projected or p.startswith(_PROTECTED_PREFIX):
        return PathClass.PROTECTED

    ctx_rel = _context_relative(p)
    if ctx_rel is not None:
        return PathClass.ADDITIVE if _is_specs_additive(ctx_rel) else PathClass.MUTATING

    if any(p.startswith(x) for x in _ADDITIVE_DADAIA_PREFIXES):
        return PathClass.ADDITIVE
    return PathClass.MUTATING


def _scope_block(
    root: PurePath,
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
    return (
        _SCOPE_BLOCK_MESSAGE.format(
            rel_path=rel_path,
            slug=target_slug,
            owner=target_owner,
            bound=bound_context,
            scope=", ".join(sorted(bound_repos)) or "no registered repo",
        )
        + f"fix: {fix_line(root, 'context', 'bind', target_owner)}"
    )


def evaluate(
    rel_path: str,
    *,
    root: PurePath,
    projected: frozenset[str] = frozenset(),
    bound_context: str | None = None,
    bound_repos: frozenset[str] = frozenset(),
    target_slug: str | None = None,
    target_owner: str | None = None,
) -> tuple[Decision, str]:
    """Return the gate decision and its message for one write target. *root* is the
    workspace every ``fix:`` line's CLI path is built from.

    Three blocks, in order: PROTECTED (fail-CLOSED, the projected-law message or the
    session-record message), then — for a MUTATING write — the bind's SCOPE, received as
    plain data (*bound_context* / *bound_repos*), never re-resolved here. Everything
    else ALLOWS with an empty message.

    SCOPE (FR1, Q1): only ``repos/<slug>/`` is scope-judged. *target_slug* is the repo
    the write lands in and *target_owner* the context that registers it; the write is
    refused only when the session is BOUND, some context demonstrably owns that slug,
    and it is not the bound context's own (*bound_repos* = main + associated). An
    unbound session, a workspace-root path, and a slug no context registers all ALLOW —
    the gate cannot attribute them, and fail-open is the posture. A MUTATING write is
    never blocked on another session: races surface through git.
    """
    cls = classify_path(rel_path, projected)

    # PROTECTED is the sole fail-closed path and is evaluated before fail-open branches.
    if cls == PathClass.PROTECTED:
        if not rel_path.lstrip("/").startswith(_PROTECTED_PREFIX):
            restage = " && ".join(
                (fix_line(root, "public", "stage"), fix_line(root, "public", "install"))
            )
            return Decision.BLOCK, _LAW_MESSAGE.format(path=rel_path) + f"fix: {restage}"
        return (
            Decision.BLOCK,
            _PROTECTED_MESSAGE + f"fix: {fix_line(root, 'context', 'bind', '<ctx>')}",
        )

    if cls == PathClass.ADDITIVE:
        return Decision.ALLOW, ""

    scope_block = _scope_block(
        root, rel_path, bound_context, bound_repos, target_slug, target_owner
    )
    if scope_block is not None:
        return Decision.BLOCK, scope_block

    # MUTATING: always allowed; races surface through git, never through a block.
    return Decision.ALLOW, ""
