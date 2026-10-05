"""Path classifier and decision policy for the merged SDD PreToolUse gate.

Races between sessions are never prevented; there is no session mode. Protected CLI session records remain fail-closed against
file-tool writes.

**The gate blocks three things (0.4.7 FR1).** A PROTECTED write (CLI-owned session
records and projected law files); a MUTATING write out of the bind's scope or under
``repos/<r>/`` outside ``specs/audits/`` (ADRs 0103, 0105, 0124); and — in
``hooks/root_whitelist`` — a new workspace-root entry. There is no
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

from collections.abc import Callable
from enum import Enum
from functools import cache
from itertools import chain
from pathlib import PurePath

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.cli_line import fix_line, mkdir_line, script_line

__all__ = ["Decision", "PathClass", "classify_path", "evaluate"]

# Derived from the zone registry (OUTPUT + EPHEMERAL zones) — never a second literal.
_ADDITIVE_DADAIA_PREFIXES: tuple[str, ...] = workspace_layout.additive_prefixes()
_R = workspace_layout.FloorRefusal
_Fix = Callable[[PurePath, str | None], str]
_DRAFT: _Fix = lambda root, _: mkdir_line(root / ".dadaia" / "tmp")  # noqa: E731
#: One fix per refusal, total: a new ``FloorRefusal`` member fails here, as ``REFUSALS`` does.
_FIXES: dict[workspace_layout.FloorRefusal, _Fix] = {
    _R.LAW: lambda root, _: fix_line(root, "public", "install"),
    _R.OPERATOR: _DRAFT,
    _R.GLOB: _DRAFT,
    _R.SESSION: lambda root, ctx: fix_line(root, "context", *(("bind", ctx) if ctx else ("list",))),
}

_SCOPE_MESSAGE = (
    "[GATE] '{rel_path}' writes into repo '{repo}', owned by context '{owner}' — this "
    "session is bound to {bound}, whose scope is: {scope}.\n"
)
#: ADR 0105: ``repos/<r>`` receives only merges; every agent write happens in a worktree.
_MERGE_ONLY_MESSAGE = (
    "[GATE] '{rel_path}' is under repos/{repo}/, which receives only merges (ADR 0105): "
    "write it inside a worktree of {repo}.\n"
)
_WORKTREE_SCRIPT = ".agents/skills/dd-gitflow-default/scripts/worktree.py"


class PathClass(Enum):
    """Three classes, no fourth (0.4.7 FR1). A workspace-root path matching no
    ADDITIVE or PROTECTED prefix is MUTATING — there is no UNGATED fall-through."""

    ADDITIVE = "ADDITIVE"
    MUTATING = "MUTATING"
    PROTECTED = "PROTECTED"


class Decision(Enum):
    ALLOW = "allow"
    BLOCK = "block"


@cache
def _locate() -> Callable[[str], tuple[str, str | None, tuple[str, ...]] | None]:
    """The worktree grammar's one path reader (ADR 0191) through the one loader, imported on
    the first protected glob judged so a gate with none pays nothing."""
    from dadaia_workspace.infrastructure.ledger_scripts import load_owner

    locate: Callable[[str], tuple[str, str | None, tuple[str, ...]] | None] = load_owner(
        "dd-gitflow-default", "_worktree_names"
    ).locate
    return locate


def _protection(
    p: str, projected: frozenset[str], protected: tuple[str, ...]
) -> tuple[workspace_layout.FloorRefusal, str] | None:
    """The one PROTECTED predicate, in precedence order: ``(refusal, match)`` — a *projected*
    path (LAW), a ``CORE_FLOOR`` entry (its own refusal), a *protected* glob (GLOB) — else ``None``."""
    floor = workspace_layout.CORE_FLOOR
    return next(
        chain(
            [(_R.LAW, p)] if p in projected else [],
            ((floor[f], f) for f in floor if p == f or p.startswith(f + "/")),
            (
                (_R.GLOB, g)
                for g in protected
                if workspace_layout.protected_glob((_locate()(p) or ("", None, ()))[2], (g,))
            ),  # fmt: skip
        ),
        None,
    )


def classify_path(
    rel_path: str, projected: frozenset[str] = frozenset(), protected: tuple[str, ...] = ()
) -> tuple[PathClass, tuple[workspace_layout.FloorRefusal, str] | None]:
    """(class, ``_protection`` hit) of a workspace-relative path; first match wins: PROTECTED
    (*projected*, then the floor, then a *protected* glob — ``_protection``'s order), ADDITIVE (the zone-registry ``.dadaia/``
    prefixes), else MUTATING — no ``repos/`` path is ever ADDITIVE (ADR 0124)."""
    p = rel_path.lstrip("/")
    if hit := _protection(p, projected, protected):
        return PathClass.PROTECTED, hit
    if any(p.startswith(x) for x in _ADDITIVE_DADAIA_PREFIXES):
        return PathClass.ADDITIVE, None
    return PathClass.MUTATING, None


def evaluate(
    rel_path: str,
    *,
    root: PurePath,
    projected: frozenset[str] = frozenset(),
    protected: tuple[str, ...] = (),
    zone: str = "root",
    repo: str | None = None,
    owner: str | None = None,
    context: str | None = None,
    repos: frozenset[str] = frozenset(),
    has_id: bool = True,
) -> tuple[Decision, str]:
    """The gate decision and its message for one write target; *root* builds every
    ``fix:`` line. The target arrives as ``core.invocation.scope``'s *zone*/*repo* plus
    the context registering *repo* (*owner*); the session as its bind (*context*,
    *repos*) and whether it carries an id (*has_id*), never re-resolved here.

    PROTECTED blocks first (fail-closed). A MUTATING write into an owned repo outside the
    bind's *repos* is refused with ``context bind <owner>`` — an unbound session with an id
    owns nothing (ADR 0072); an id-less one bound by env is told to relaunch; an id-less
    unbound one is the declared gap (ADR 0116). Then every write in zone ``repo`` is
    refused with the ``worktree.py list`` fix (ADR 0105). Everything else ALLOWS.
    """
    cls, hit = classify_path(rel_path, projected, protected)
    if hit:
        refusal, match = hit
        fix = _FIXES[refusal](root, context)
        message = workspace_layout.REFUSALS[refusal].format(path=rel_path, match=match)
        return Decision.BLOCK, message + f"fix: {fix}"
    if cls == PathClass.ADDITIVE or repo is None:
        return Decision.ALLOW, ""
    if owner is not None and repo not in repos and (context is not None or has_id):
        message = _SCOPE_MESSAGE.format(
            rel_path=rel_path,
            repo=repo,
            owner=owner,
            bound=f"'{context}'" if context else "no context",
            scope=", ".join(sorted(repos)) or "no registered repo",
        )
        fix = (  # an id-less session's bind is its env: only the operator can change it
            fix_line(root, "context", "bind", owner)
            if has_id
            else f"Operator action: relaunch this session with DADAIA_CONTEXT={owner}"
        )
        return Decision.BLOCK, message + f"fix: {fix}"
    if zone == "repo":
        message = _MERGE_ONLY_MESSAGE.format(rel_path=rel_path, repo=repo)
        return Decision.BLOCK, message + f"fix: {script_line(_WORKTREE_SCRIPT, 'list')}"
    return Decision.ALLOW, ""
