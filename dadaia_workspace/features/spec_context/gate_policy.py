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

import runpy
from collections.abc import Callable
from enum import Enum
from functools import cache
from pathlib import Path, PurePath
from typing import Any

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

#: ``.dadaiaignore`` is the operator's alone (ADR 0092): an agent proposes a pattern, never writes it.
_OPERATOR_MESSAGE = (
    "[GATE] .dadaiaignore is the operator's file (ADR 0092): only the operator edits it by "
    "hand. Hand the operator the pattern you need; the doctor names every unadmitted entry.\n"
)

_SCOPE_MESSAGE = (
    "[GATE] '{rel_path}' writes into repo '{repo}', owned by context '{owner}' — this "
    "session is bound to {bound}, whose scope is: {scope}.\n"
)
#: ADR 0105: ``repos/<r>`` receives only merges; every agent write happens in a worktree.
_MERGE_ONLY_MESSAGE = (
    "[GATE] '{rel_path}' is under repos/{repo}/, which receives only merges (ADR 0105): "
    "write it inside a worktree of {repo}.\n"
)
_KINDS = Path(__file__).parents[2] / "public/skills/dd-gitflow-default/scripts/_worktree_kinds.py"


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
def _worktree_kinds() -> dict[str, Any]:
    """The KINDS table's owner script (ADR 0135), run in place: no bytecode left beside it."""
    return runpy.run_path(str(_KINDS))


def _worktree_fix(repo: str, repo_rel: str) -> str:
    kinds = _worktree_kinds()
    allows: Callable[[str, str], bool] = kinds["allows"]
    kind = next((k for k in kinds["KINDS"] if allows(k, repo_rel)), "release")
    return f"python3 .agents/skills/dd-gitflow-default/scripts/worktree.py new {repo} --kind {kind}"


def classify_path(rel_path: str, projected: frozenset[str] = frozenset()) -> PathClass:
    """Classify a workspace-relative path; first match wins: PROTECTED (session records,
    *projected* paths, ``.dadaiaignore``), ADDITIVE (the zone-registry ``.dadaia/``
    prefixes), else MUTATING — no ``repos/`` path is ever ADDITIVE (ADR 0124)."""
    p = rel_path.lstrip("/")
    if p in projected or p.startswith(_PROTECTED_PREFIX) or p == workspace_layout.DADAIAIGNORE:
        return PathClass.PROTECTED
    if any(p.startswith(x) for x in _ADDITIVE_DADAIA_PREFIXES):
        return PathClass.ADDITIVE
    return PathClass.MUTATING


def evaluate(
    rel_path: str,
    *,
    root: PurePath,
    projected: frozenset[str] = frozenset(),
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
    refused with the ``worktree.py new`` fix (ADR 0105). Everything else ALLOWS.
    """
    cls = classify_path(rel_path, projected)
    if cls == PathClass.PROTECTED:
        p = rel_path.lstrip("/")
        if p.startswith(_PROTECTED_PREFIX):
            message, fix = _PROTECTED_MESSAGE, fix_line(root, "context", "bind", "<ctx>")
        elif p == workspace_layout.DADAIAIGNORE:
            message, fix = _OPERATOR_MESSAGE, fix_line(root, "doctor")  # names what to ask for
        else:  # re-projects the law from staging
            message, fix = _LAW_MESSAGE.format(path=rel_path), fix_line(root, "public", "install")
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
        repo_rel = rel_path.lstrip("/").split("/", 2)[2:]
        message = _MERGE_ONLY_MESSAGE.format(rel_path=rel_path, repo=repo)
        return Decision.BLOCK, message + f"fix: {_worktree_fix(repo, ''.join(repo_rel))}"
    return Decision.ALLOW, ""
