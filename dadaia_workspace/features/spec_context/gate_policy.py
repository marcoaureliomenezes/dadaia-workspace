"""Path classifier and decision policy for the merged SDD PreToolUse gate.

Races between sessions are never prevented; there is no session mode. Protected CLI session records remain fail-closed against
file-tool writes.

**The gate blocks four things.** A PROTECTED write (CLI-owned session
records and projected law files); a MUTATING write out of the bind's scope or under
``repos/<r>/`` outside ``specs/audits/``; in ``hooks/root_whitelist`` a new workspace-root
entry; and a verdict write by anyone but the reviewer (:func:`verdict_act`, the one Bash act
judged). There is no path class beyond ``ADDITIVE``/``MUTATING``/``PROTECTED``.

The gate reads no SDD artifact; memory authorship is never gated.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from enum import Enum
from itertools import chain
from pathlib import Path, PurePath

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.cli_line import fix_line, mkdir_line, reinstall_fix, spell_fix
from dadaia_workspace.core.linked_tree import linked_tree_depths
from dadaia_workspace.core.platform import act
from dadaia_workspace.core.skill_owner import load_owner

__all__ = ["Decision", "PathClass", "classify_path", "evaluate", "verdict_act"]

# Derived from the zone registry (OUTPUT + EPHEMERAL zones) — never a second literal.
_ADDITIVE_DADAIA_PREFIXES: tuple[str, ...] = workspace_layout.additive_prefixes()
_R = workspace_layout.FloorRefusal
_Fix = Callable[[PurePath, str | None], str]
_DRAFT: _Fix = lambda root, _: mkdir_line(root / ".dadaia" / "tmp")  # noqa: E731
#: One fix per refusal, total: a new ``FloorRefusal`` member fails here, as ``REFUSALS`` does.
_FIXES: dict[workspace_layout.FloorRefusal, _Fix] = {
    _R.LAW: lambda root, _: reinstall_fix(Path(root), projected=True),
    _R.STATE: lambda root, _: act(
        "agent", "use the verb or skill script that owns that state file instead of editing it"
    ),
    _R.OPERATOR: _DRAFT,
    _R.GLOB: _DRAFT,
    _R.SESSION: lambda root, ctx: fix_line(root, "context", *(("bind", ctx) if ctx else ("list",))),
}

_SCOPE_MESSAGE = (
    "[GATE] '{rel_path}' writes into repo '{repo}', owned by context '{owner}' — this "
    "session is bound to {bound}, whose scope is: {scope}.\n"
)
#: ``repos/<r>`` receives only merges; every agent write happens in a worktree.
_MERGE_ONLY_MESSAGE = (
    "[GATE] '{rel_path}' is under repos/{repo}/, which receives only merges: "
    "write it inside a worktree of {repo}.\n"
)


class PathClass(Enum):
    """Three classes, no fourth. A workspace-root path matching no
    ADDITIVE or PROTECTED prefix is MUTATING — there is no UNGATED fall-through."""

    ADDITIVE = "ADDITIVE"
    MUTATING = "MUTATING"
    PROTECTED = "PROTECTED"


class Decision(Enum):
    ALLOW = "allow"
    BLOCK = "block"


def _protection(
    p: str, projected: frozenset[str], protected: tuple[str, ...], root: PurePath
) -> tuple[workspace_layout.FloorRefusal, str] | None:
    """The one PROTECTED predicate, in precedence order: ``(refusal, match)`` — a *projected*
    path (LAW), a ``CORE_FLOOR`` entry (its own refusal), a *protected* glob (GLOB) — else ``None``."""
    floor = workspace_layout.CORE_FLOOR
    return next(
        chain(
            [(_R.LAW, p)] if p in projected else [],
            ((floor[f], f) for f in floor if p == f or p.startswith(f + "/")),
            [(_R.GLOB, g)]
            if (g := workspace_layout.protected_glob(Path(root), p, protected))
            else [],
        ),
        None,
    )


def classify_path(
    rel_path: str,
    projected: frozenset[str] = frozenset(),
    protected: tuple[str, ...] = (),
    *,
    root: PurePath,
) -> tuple[PathClass, tuple[workspace_layout.FloorRefusal, str] | None]:
    """(class, ``_protection`` hit) of a workspace-relative path; first match wins: PROTECTED
    (*projected*, then the floor, then a *protected* glob — ``_protection``'s order), ADDITIVE (the zone-registry ``.dadaia/``
    prefixes), else MUTATING — no ``repos/`` path is ever ADDITIVE."""
    p = rel_path.lstrip("/")
    if hit := _protection(p, projected, protected, root):
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
    owns nothing; an id-less one bound by env is told to relaunch; an id-less
    unbound one is the declared gap, unless the write lands inside a git-linked worktree of
    this workspace (scope follows the tree, never a rebind). Then every write in zone ``repo`` is
    refused with the ``dadaia worktree list`` fix. Everything else ALLOWS.
    """
    cls, hit = classify_path(rel_path, projected, protected, root=root)
    if hit:
        refusal, match = hit
        fix = _FIXES[refusal](root, context)
        message = workspace_layout.REFUSALS[refusal].format(path=rel_path, match=match)
        return Decision.BLOCK, message + spell_fix(fix)
    if cls == PathClass.ADDITIVE or repo is None:
        return Decision.ALLOW, ""
    in_linked_tree = zone == "worktree" and linked_tree_depths(
        Path(root), rel_path.replace("\\", "/").strip("/").split("/")
    )
    if (
        owner is not None
        and repo not in repos
        and (context is not None or has_id)
        and not in_linked_tree
    ):
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
            else act("operator", f"relaunch this session with DADAIA_CONTEXT={owner}")
        )
        return Decision.BLOCK, message + spell_fix(fix)
    if zone == "repo":
        message = _MERGE_ONLY_MESSAGE.format(rel_path=rel_path, repo=repo)
        return Decision.BLOCK, message + spell_fix(fix_line(root, "worktree", "list"))
    return Decision.ALLOW, ""


_WRITER = re.compile(r"verdict\.py|-m\s*verdict")


def verdict_act(command: str, *, key: str | None, subagent: str | None) -> str | None:
    """The block message when the text of *command* holds the writer (``verdict.py`` or
    ``-m verdict``) and ``--verdict`` once quotes and backslashes are removed (a glob, brace
    or parameter expansion of the name, e.g. ``verdict.p?``, ``verdict.{py,}``, ``$v.py``, is
    not caught), and the harness, which names a running subagent under payload *key*
    (``None``: it gives no identity), reports
    *subagent* (``None``: the main thread) other than the reviewer; else ``None``."""
    reviewer = load_owner("dd-bug-resolution", "_handoffs").REVIEWER
    if (
        key is None
        or subagent == reviewer
        or not (
            _WRITER.search(text := re.sub(r"['\"\\]", "", command.lower())) and "--verdict" in text
        )
    ):
        return None
    dispatch = f"dispatch {reviewer} on the tree to judge; its verdict.py run writes the verdict"
    return f"[GATE] Only the dispatched {reviewer} writes a verdict.\n" + spell_fix(
        act("agent", dispatch)
    )
