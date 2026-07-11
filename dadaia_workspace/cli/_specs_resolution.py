"""The single CLI bind-resolution seam (v0.1.50 FR4; generalized v0.1.77 FR1).

Every resolver-driven ``dadaia`` command resolves through this module — its specs
directory via :func:`resolve_specs_dir_for_cli`, or (v0.1.77) the bound CONTEXT NAME
itself via :func:`resolve_context_for_cli`. Both ALWAYS thread the current process's
ancestry pid chain into the core resolver, so bind-marker attribution works from any
ephemeral harness shell. Five per-command wrappers used to hand-copy the specs-dir call
and four of them omitted ``ancestry_pids`` (bug
``bugs-append-bound-session-falls-through-to-cwd-specs``): centralizing here makes the
omission structurally impossible.

v0.1.77 (backlog ``central-bind-resolution-seam``, recurrence family F2 — 8 reports, 5
partial per-command fixes v0.1.47->v0.1.71): a partial seam existed here
(``resolve_specs_dir_for_cli``, consumed by specs/bugs/memory/migrate/newartifacts) but
NOT the ~15 lifecycle verbs, whose ``--context`` Typer default was the hardcoded literal
``"dadaia-workspace"`` passed as if explicit — the bind was never consulted.
:func:`resolve_context_for_cli` is the single canonical order (SPEC FR1) every verb now
resolves through: explicit -> ``DADAIA_CONTEXT`` env -> this session's OWN record
(harness-native id / ancestry-marker membership, via
:func:`~dadaia_workspace.core.specs_resolver.resolve_bound_context_name` — never a
foreign session's bind, consistent with the v0.1.76 NO-LOCKS DOCTRINE's self-scoped
identity) -> first-ALIVE context (fail-soft; mirrors ``context show``'s pre-v0.1.77
no-arg fallback, folded into the seam here per SPEC FR1's explicit disposition).
"""

from __future__ import annotations

import os
from pathlib import Path

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.core.specs_resolver import resolve_bound_context_name as _resolve_bound_name
from dadaia_workspace.core.specs_resolver import resolve_specs_dir as _core_resolve_specs_dir
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

#: The self-hosting-workspace slug (mirrors the pre-existing ``_DEFAULT_SLUG`` convention
#: in ``features.panel.views._md_render``). Terminal fallback of :func:`resolve_context_for_cli`
#: when NO context is ALIVE at all (a workspace with zero registered contexts — e.g. this
#: source-library self-hosting workspace pre-first-``context create``, or a hermetic test
#: fixture). This is NOT the FR2 hardcoded-Typer-default bug: FR2 forbids a specific
#: context name baked into a *CLI option default that shadows an explicit bind*; this is
#: the seam's OWN terminal fallback constant, reached only after explicit/env/session/
#: first-ALIVE are all exhausted — structurally identical in kind to
#: ``resolve_specs_dir_for_cli``'s own cwd/specs terminal fallback rung.
_SELF_HOSTING_SLUG = "dadaia-workspace"


def current_ancestry_pids() -> frozenset[int] | None:
    """This ``dadaia`` process's nearest-first ancestry pid chain (bind attribution).

    W1-8 (v0.1.47): the persisted-bind fallback attributes a bind-epoch marker by
    ancestry-chain MEMBERSHIP. A marker written from an ephemeral harness shell
    records the bind process's chain (incl. the long-lived harness pid); this CLI
    runs under a DIFFERENT short-lived shell but shares that harness pid deeper in
    ITS chain. Any failure ⇒ ``None`` ⇒ the resolver degrades to single-getppid
    equality.
    """
    try:
        from dadaia_workspace import container

        return frozenset(container.build_ancestry_pid_chain(os.getppid()))
    except Exception:  # noqa: BLE001 — attribution is best-effort; never break resolution.
        return None


def _first_alive_context_name() -> str | None:
    """Fail-soft first-ALIVE context name (the seam's last resolution rung, FR1).

    Mirrors the fallback ``context show`` used pre-v0.1.77 for its no-arg default
    (``cli.commands.context._resolve_default_context``'s tail case): when no explicit
    input, env, or live session record resolves a context, fall back to the first ALIVE
    Spec Context Project (workspace-registration order). Any failure (workspace not
    initialized, no ALIVE context, store error) fails soft to ``None`` — resolution
    never raises here; the caller's own not-bound error path is unchanged.
    """
    try:
        from dadaia_workspace import container

        workspace_root = resolve_workspace_root()
        svc = container.build_spec_context_service(workspace_root)
        for ctx in svc.list_all():
            if ctx.state == ContextState.ALIVE:
                return ctx.name
        return None
    except (WorkspaceNotInitializedError, Exception):  # noqa: BLE001 — fail-soft, never raise.
        return None


def resolve_context_for_cli(explicit: str | None) -> str:
    """Resolve the target Spec Context NAME (SPEC FR1 canonical order, v0.1.77).

    Order: *explicit* -> ``DADAIA_CONTEXT`` env -> this session's OWN bound record
    (harness-native id, then ancestry-marker membership — never a foreign session's
    bind) -> first-ALIVE context (fail-soft) -> the self-hosting-workspace slug
    (``"dadaia-workspace"``, terminal fallback when NO context is ALIVE at all).
    Always returns a non-empty string — never ``None`` — so a real bind or a real ALIVE
    context always takes priority (the FR1 bug this release fixes), while a workspace
    with no context registered at all degrades to the same self-hosting name every
    resolver-driven verb has always assumed by construction (unchanged prior behavior
    for that degenerate case).
    """
    if explicit:
        return explicit
    resolved = _resolve_bound_name(ancestry_pids=current_ancestry_pids())
    if resolved:
        return resolved
    return _first_alive_context_name() or _SELF_HOSTING_SLUG


def resolve_specs_dir_for_cli(specs_dir: str | None) -> Path:
    """Resolve the target specs/ dir (explicit flag → bound context → cwd/specs)."""
    return _core_resolve_specs_dir(specs_dir, ancestry_pids=current_ancestry_pids())
