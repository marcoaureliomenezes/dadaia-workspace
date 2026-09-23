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

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.kernel_tunables import DADAIA_BIN

__all__ = ["Decision", "PathClass", "classify_path", "evaluate"]

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
    f"fix: {DADAIA_BIN} context bind <ctx>"
)
#: Projected LAW files. The root ``AGENTS.md`` map is the workspace system prompt and
#: the sole always-on rule file the library ships; the ``.dadaia/**`` family is its
#: scoped counterpart. In an INSTANTIATED workspace these are human-only: an agent
#: changes the law by editing ``dadaia_workspace/public/`` and re-projecting, never by
#: writing the projection.
_LAW_BASENAMES: frozenset[str] = workspace_layout.LAW_BASENAMES
_LAW_MESSAGE = (
    "[GATE] '{path}' is a projected law file (the workspace system prompt / scoped "
    "AGENTS.md). In an instantiated workspace only a human operator edits it by hand; "
    "an agent changes the law at its source and re-projects.\n"
    "The source is dadaia_workspace/public/; this re-projects it:\n"
    f"fix: {DADAIA_BIN} public stage && {DADAIA_BIN} public "
    "install"
)

#: BLOCK message for a MUTATING write into a repo outside the Bind's scope (FR1, Q1).
#: Only ``repos/<slug>/`` is scope-judged: a workspace-root path is in scope under any
#: bind, and a slug no Context registers is unattributable, so it ALLOWS (fail-open).
_SCOPE_BLOCK_MESSAGE = (
    "[GATE] '{rel_path}' writes into repo '{slug}', owned by context '{owner}' — this "
    "session is bound to '{bound}', whose scope is: {scope}.\n"
    "fix: " + DADAIA_BIN + " context bind {owner}"
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

    Static, ORIGIN-only floor (v0.4.5 FR1, since collapsed): the projected
    ``AGENTS.md`` set — the root map and the ``.dadaia/**`` family. ``repos/<slug>/``
    never matches either shape, so a repo's own AGENTS.md is never LAW (closes
    sdd-gate-blocks-fresh-repo-root-agents-md + repo-agents-md-law-gate-contradicts-
    template) — and the floor never reads the manifest (CWE-284).
    """
    parts = rel_path.split("/")
    if parts[-1] not in _LAW_BASENAMES:
        return False
    return len(parts) == 1 or parts[0] == ".dadaia"


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
    rel_path: str,
    *,
    bound_context: str | None = None,
    bound_repos: frozenset[str] = frozenset(),
    target_slug: str | None = None,
    target_owner: str | None = None,
) -> tuple[Decision, str]:
    """Return the gate decision and its message for one write target.

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

    # MUTATING: always allowed; races surface through git, never through a block.
    return Decision.ALLOW, ""
